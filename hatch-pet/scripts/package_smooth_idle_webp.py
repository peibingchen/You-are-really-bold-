#!/usr/bin/env python3
"""Package an approved static v2 atlas as a self-timed smooth-idle WebP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ATLAS_SIZE = (1536, 2288)
CELL_WIDTH = 192
CELL_HEIGHT = 208
IDLE_FRAME_COUNT = 6
NEUTRAL_LOOK_COLUMN = 6
UNUSED_IDLE_COLUMNS = (7,)
DEFAULT_DURATIONS = (280, 110, 110, 140, 140, 320)
MIN_PHASE_COUNT = 2
MAX_PHASE_COUNT = 60


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_durations(value: str) -> tuple[int, ...]:
    try:
        durations = tuple(int(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("durations must be comma-separated integers") from exc
    if len(durations) != IDLE_FRAME_COUNT:
        raise argparse.ArgumentTypeError(
            f"durations must contain {IDLE_FRAME_COUNT} values"
        )
    if any(duration <= 0 for duration in durations):
        raise argparse.ArgumentTypeError("durations must all be positive")
    return durations


def atlas_cell(source: Image.Image, row: int, column: int) -> Image.Image:
    if not 0 <= row < ATLAS_SIZE[1] // CELL_HEIGHT:
        raise ValueError(f"atlas row must be between 0 and 10, got {row}")
    if not 0 <= column < ATLAS_SIZE[0] // CELL_WIDTH:
        raise ValueError(f"atlas column must be between 0 and 7, got {column}")
    cell = source.crop(
        (
            column * CELL_WIDTH,
            row * CELL_HEIGHT,
            (column + 1) * CELL_WIDTH,
            (row + 1) * CELL_HEIGHT,
        )
    )
    if alpha_nonzero(cell) == 0:
        raise ValueError(f"atlas cell row {row} column {column} is empty")
    return cell


def default_phase_plan(
    source: Image.Image,
    durations: tuple[int, ...] = DEFAULT_DURATIONS,
) -> tuple[list[Image.Image], tuple[int, ...], list[dict[str, object]]]:
    if len(durations) != IDLE_FRAME_COUNT:
        raise ValueError(f"default idle plan requires {IDLE_FRAME_COUNT} durations")
    cells = [atlas_cell(source, 0, column) for column in range(IDLE_FRAME_COUNT)]
    metadata = [
        {
            "label": f"idle-{column}",
            "duration_ms": duration,
            "source": {"atlas_row": 0, "atlas_column": column},
        }
        for column, duration in enumerate(durations)
    ]
    return cells, durations, metadata


def load_phase_manifest(
    manifest_path: Path,
    source: Image.Image,
) -> tuple[list[Image.Image], tuple[int, ...], list[dict[str, object]]]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read phase manifest: {exc}") from exc
    phases = payload.get("phases") if isinstance(payload, dict) else None
    if not isinstance(phases, list):
        raise ValueError("phase manifest must contain a phases array")
    if not MIN_PHASE_COUNT <= len(phases) <= MAX_PHASE_COUNT:
        raise ValueError(
            f"phase manifest must contain {MIN_PHASE_COUNT}-{MAX_PHASE_COUNT} phases"
        )

    cells: list[Image.Image] = []
    durations: list[int] = []
    metadata: list[dict[str, object]] = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise ValueError(f"phase {index} must be an object")
        label = phase.get("label", f"phase-{index}")
        duration = phase.get("duration_ms")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"phase {index} label must be a non-empty string")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
            raise ValueError(f"phase {index} duration_ms must be a positive integer")

        image_value = phase.get("image")
        atlas_row = phase.get("atlas_row")
        atlas_column = phase.get("atlas_column")
        has_image = isinstance(image_value, str) and bool(image_value.strip())
        has_atlas_cell = isinstance(atlas_row, int) and isinstance(atlas_column, int)
        if has_image == has_atlas_cell:
            raise ValueError(
                f"phase {index} must specify exactly one source: image or atlas_row/atlas_column"
            )

        if has_image:
            image_path = Path(image_value).expanduser()
            if not image_path.is_absolute():
                image_path = manifest_path.parent / image_path
            image_path = image_path.resolve()
            try:
                with Image.open(image_path) as opened:
                    if getattr(opened, "is_animated", False) and getattr(opened, "n_frames", 1) > 1:
                        raise ValueError("phase image must be static")
                    if opened.size != (CELL_WIDTH, CELL_HEIGHT):
                        raise ValueError(
                            f"phase image must be {CELL_WIDTH}x{CELL_HEIGHT}, got {opened.width}x{opened.height}"
                        )
                    cell = opened.convert("RGBA")
            except OSError as exc:
                raise ValueError(f"could not read phase {index} image: {exc}") from exc
            if alpha_nonzero(cell) == 0:
                raise ValueError(f"phase {index} image is empty")
            source_metadata: dict[str, object] = {"image": str(image_path)}
        else:
            if isinstance(atlas_row, bool) or isinstance(atlas_column, bool):
                raise ValueError(f"phase {index} atlas coordinates must be integers")
            cell = atlas_cell(source, atlas_row, atlas_column)
            source_metadata = {
                "atlas_row": atlas_row,
                "atlas_column": atlas_column,
            }

        cells.append(cell)
        durations.append(duration)
        metadata.append(
            {
                "label": label.strip(),
                "duration_ms": duration,
                "source": source_metadata,
            }
        )
    return cells, tuple(durations), metadata


def alpha_nonzero(image: Image.Image) -> int:
    return sum(image.getchannel("A").histogram()[1:])


def render_equal(left: Image.Image, right: Image.Image) -> bool:
    """Compare alpha and every visible RGBA pixel, ignoring hidden RGB under alpha 0."""
    if left.size != right.size:
        return False
    left_bytes = left.convert("RGBA").tobytes()
    right_bytes = right.convert("RGBA").tobytes()
    for index in range(0, len(left_bytes), 4):
        left_alpha = left_bytes[index + 3]
        right_alpha = right_bytes[index + 3]
        if left_alpha != right_alpha:
            return False
        if left_alpha and left_bytes[index : index + 3] != right_bytes[index : index + 3]:
            return False
    return True


def transparent_rgb_residue(image: Image.Image) -> int:
    data = image.convert("RGBA").tobytes()
    return sum(
        data[index + 3] == 0 and any(data[index : index + 3])
        for index in range(0, len(data), 4)
    )


def load_static_v2_atlas(source: Path) -> Image.Image:
    with Image.open(source) as opened:
        if getattr(opened, "is_animated", False) and getattr(opened, "n_frames", 1) > 1:
            raise ValueError("source atlas must be the approved static v2 atlas")
        if opened.size != ATLAS_SIZE:
            raise ValueError(
                f"source atlas must be {ATLAS_SIZE[0]}x{ATLAS_SIZE[1]}, got {opened.width}x{opened.height}"
            )
        atlas = opened.convert("RGBA")

    for column in range(IDLE_FRAME_COUNT):
        cell = atlas.crop(
            (
                column * CELL_WIDTH,
                0,
                (column + 1) * CELL_WIDTH,
                CELL_HEIGHT,
            )
        )
        if alpha_nonzero(cell) == 0:
            raise ValueError(f"source idle column {column} is empty")

    neutral_cell = atlas.crop(
        (
            NEUTRAL_LOOK_COLUMN * CELL_WIDTH,
            0,
            (NEUTRAL_LOOK_COLUMN + 1) * CELL_WIDTH,
            CELL_HEIGHT,
        )
    )
    if alpha_nonzero(neutral_cell) == 0:
        raise ValueError("source neutral-look column 6 is empty")

    for column in UNUSED_IDLE_COLUMNS:
        cell = atlas.crop(
            (
                column * CELL_WIDTH,
                0,
                (column + 1) * CELL_WIDTH,
                CELL_HEIGHT,
            )
        )
        if alpha_nonzero(cell) != 0:
            raise ValueError(f"source idle unused column {column} is not transparent")
    return atlas


def build_runtime_frames(
    source: Image.Image,
    phase_cells: list[Image.Image] | None = None,
) -> list[Image.Image]:
    if phase_cells is None:
        phase_cells, _, _ = default_phase_plan(source)
    frames: list[Image.Image] = []
    for phase_cell in phase_cells:
        if phase_cell.size != (CELL_WIDTH, CELL_HEIGHT):
            raise ValueError(
                f"phase cell must be {CELL_WIDTH}x{CELL_HEIGHT}, got {phase_cell.width}x{phase_cell.height}"
            )
        phase_cell = phase_cell.convert("RGBA")
        if alpha_nonzero(phase_cell) == 0:
            raise ValueError("phase cell is empty")
        runtime = source.copy()
        for column in range(IDLE_FRAME_COUNT):
            runtime.paste(phase_cell, (column * CELL_WIDTH, 0))
        frames.append(runtime)
    return frames


def decoded_frames(path: Path) -> tuple[list[Image.Image], list[int], int | None]:
    frames: list[Image.Image] = []
    durations: list[int] = []
    with Image.open(path) as opened:
        if opened.format != "WEBP":
            raise ValueError(f"runtime atlas must be WebP, got {opened.format}")
        if not getattr(opened, "is_animated", False):
            raise ValueError("runtime atlas is not animated")
        loop = opened.info.get("loop")
        for index in range(opened.n_frames):
            opened.seek(index)
            opened.load()
            durations.append(int(opened.info.get("duration", 0)))
            frames.append(opened.convert("RGBA"))
    return frames, durations, loop


def validate_runtime(
    runtime_path: Path,
    source: Image.Image,
    expected_durations: tuple[int, ...],
    phase_cells: list[Image.Image] | None = None,
    phase_metadata: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    errors: list[str] = []
    expected_frames = build_runtime_frames(source, phase_cells)
    try:
        actual_frames, actual_durations, loop = decoded_frames(runtime_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "errors": [f"could not decode animated runtime atlas: {exc}"],
            "warnings": [],
        }

    expected_frame_count = len(expected_frames)
    if len(actual_frames) != expected_frame_count:
        errors.append(
            f"expected {expected_frame_count} animation frames, got {len(actual_frames)}"
        )
    if tuple(actual_durations) != expected_durations:
        errors.append(
            f"expected durations {list(expected_durations)}, got {actual_durations}"
        )
    if loop != 0:
        errors.append(f"expected infinite loop value 0, got {loop}")

    frames_to_check = min(len(actual_frames), len(expected_frames))
    transparent_rgb_residue_per_frame: list[int] = []
    for index in range(frames_to_check):
        actual = actual_frames[index]
        expected = expected_frames[index]
        transparent_rgb_residue_per_frame.append(transparent_rgb_residue(actual))
        if actual.size != ATLAS_SIZE:
            errors.append(
                f"animation frame {index} has size {actual.width}x{actual.height}"
            )
            continue
        if not render_equal(actual, expected):
            errors.append(
                f"animation frame {index} visibly differs from the deterministic phase map"
            )

        reference_cell = actual.crop((0, 0, CELL_WIDTH, CELL_HEIGHT))
        for column in range(1, IDLE_FRAME_COUNT):
            cell = actual.crop(
                (
                    column * CELL_WIDTH,
                    0,
                    (column + 1) * CELL_WIDTH,
                    CELL_HEIGHT,
                )
            )
            if not render_equal(cell, reference_cell):
                errors.append(
                    f"animation frame {index} idle column {column} is out of phase"
                )

        if not render_equal(
            actual.crop((0, CELL_HEIGHT, ATLAS_SIZE[0], ATLAS_SIZE[1])),
            source.crop((0, CELL_HEIGHT, ATLAS_SIZE[0], ATLAS_SIZE[1])),
        ):
            errors.append(f"animation frame {index} changes a non-idle row")

    return {
        "ok": not errors,
        "file": str(runtime_path),
        "format": "WEBP",
        "animated": True,
        "frame_count": len(actual_frames),
        "durations_ms": actual_durations,
        "loop_duration_ms": sum(actual_durations),
        "loop": loop,
        "phases": phase_metadata or [],
        "idle_columns_synchronized": not any("out of phase" in item for item in errors),
        "non_idle_rows_unchanged": not any("non-idle row" in item for item in errors),
        "phase_map_exact": not any("phase map" in item for item in errors),
        "transparent_rgb_residue_pixels_per_frame": transparent_rgb_residue_per_frame,
        "errors": errors,
        "warnings": [
            "Animated WebP playback is image-timed and is not disabled by the desktop reduced-motion setting.",
            "Animated WebP decoding may normalize hidden RGB under fully transparent pixels; validation requires exact alpha and exact visible RGB instead.",
        ],
    }


def save_runtime(
    frames: list[Image.Image],
    durations: tuple[int, ...],
    output: Path,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=list(durations),
        loop=0,
        lossless=True,
        quality=100,
        method=6,
        exact=True,
        minimize_size=True,
        background=(0, 0, 0, 0),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-atlas", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--durations",
        type=parse_durations,
        default=None,
        help="six comma-separated idle durations in milliseconds",
    )
    parser.add_argument(
        "--phase-manifest",
        help="optional JSON phase plan using approved atlas cells or 192x208 RGBA images",
    )
    parser.add_argument("--json-out")
    args = parser.parse_args()

    source_path = Path(args.source_atlas).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    source = load_static_v2_atlas(source_path)
    if args.phase_manifest:
        if args.durations is not None:
            parser.error("--durations cannot be combined with --phase-manifest")
        manifest_path = Path(args.phase_manifest).expanduser().resolve()
        phase_cells, durations, phase_metadata = load_phase_manifest(manifest_path, source)
    else:
        manifest_path = None
        phase_cells, durations, phase_metadata = default_phase_plan(
            source, args.durations or DEFAULT_DURATIONS
        )
    frames = build_runtime_frames(source, phase_cells)
    save_runtime(frames, durations, output_path)
    result = validate_runtime(
        output_path,
        source,
        durations,
        phase_cells=phase_cells,
        phase_metadata=phase_metadata,
    )
    result.update(
        {
            "source_atlas": str(source_path),
            "source_sha256": sha256_file(source_path),
            "output_sha256": sha256_file(output_path),
            "phase_manifest": str(manifest_path) if manifest_path else None,
        }
    )

    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
