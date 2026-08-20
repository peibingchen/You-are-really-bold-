#!/usr/bin/env python3
"""Package a v2 atlas with synchronized image-time phases for native pet states."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path

from PIL import Image

from package_smooth_idle_webp import (
    ATLAS_SIZE,
    CELL_HEIGHT,
    CELL_WIDTH,
    alpha_nonzero,
    decoded_frames,
    load_static_v2_atlas,
    render_equal,
    save_runtime,
    sha256_file,
    transparent_rgb_residue,
)

STATE_SPECS = OrderedDict(
    [
        ("idle", (0, 6)),
        ("running-right", (1, 8)),
        ("running-left", (2, 8)),
        ("waving", (3, 4)),
        ("jumping", (4, 5)),
        ("failed", (5, 8)),
        ("waiting", (6, 6)),
        ("running", (7, 6)),
        ("review", (8, 6)),
    ]
)
MIN_PHASE_COUNT = 2
MAX_PHASE_COUNT = 60


def atlas_cell(source: Image.Image, row: int, column: int) -> Image.Image:
    if not 0 <= row < 11 or not 0 <= column < 8:
        raise ValueError(f"atlas source row/column out of range: {row}/{column}")
    cell = source.crop(
        (
            column * CELL_WIDTH,
            row * CELL_HEIGHT,
            (column + 1) * CELL_WIDTH,
            (row + 1) * CELL_HEIGHT,
        )
    )
    if alpha_nonzero(cell) == 0:
        raise ValueError(f"atlas source row {row} column {column} is empty")
    return cell


def load_source_cell(
    value: object,
    *,
    manifest_path: Path,
    source: Image.Image,
    default_row: int,
    state: str,
    phase_index: int,
) -> tuple[Image.Image, dict[str, object]]:
    if not isinstance(value, dict):
        raise ValueError(f"{state} phase {phase_index} must be an object")

    image_value = value.get("image")
    atlas_column = value.get("atlas_column")
    atlas_row = value.get("atlas_row", default_row)
    has_image = isinstance(image_value, str) and bool(image_value.strip())
    has_atlas = (
        isinstance(atlas_column, int)
        and not isinstance(atlas_column, bool)
        and isinstance(atlas_row, int)
        and not isinstance(atlas_row, bool)
    )
    if has_image == has_atlas:
        raise ValueError(
            f"{state} phase {phase_index} must specify exactly one source: image or atlas_column"
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
            raise ValueError(f"could not read {state} phase {phase_index}: {exc}") from exc
        if alpha_nonzero(cell) == 0:
            raise ValueError(f"{state} phase {phase_index} image is empty")
        metadata: dict[str, object] = {"image": str(image_path)}
    else:
        cell = atlas_cell(source, atlas_row, atlas_column)
        metadata = {"atlas_row": atlas_row, "atlas_column": atlas_column}
    return cell, metadata


def load_state_phase_manifest(
    manifest_path: Path,
    source: Image.Image,
    *,
    require_all_states: bool = False,
    min_motion_clips: int = 0,
    max_motion_clips: int | None = None,
) -> tuple[
    tuple[int, ...],
    list[str],
    OrderedDict[str, list[Image.Image]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read state-phase manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("state-phase manifest must be a JSON object")
    if payload.get("schema_version", 1) != 1:
        raise ValueError("state-phase manifest schema_version must be 1")

    phases = payload.get("phases")
    if not isinstance(phases, list) or not MIN_PHASE_COUNT <= len(phases) <= MAX_PHASE_COUNT:
        raise ValueError(
            f"state-phase manifest must contain {MIN_PHASE_COUNT}-{MAX_PHASE_COUNT} phases"
        )
    durations: list[int] = []
    labels: list[str] = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise ValueError(f"timeline phase {index} must be an object")
        label = phase.get("label", f"phase-{index:02d}")
        duration = phase.get("duration_ms")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"timeline phase {index} label must be non-empty")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
            raise ValueError(f"timeline phase {index} duration_ms must be a positive integer")
        labels.append(label.strip())
        durations.append(duration)

    motion_clips_value = payload.get("motion_clips", [])
    if not isinstance(motion_clips_value, list):
        raise ValueError("motion_clips must be an array")
    if len(motion_clips_value) < min_motion_clips:
        raise ValueError(
            f"manifest must declare at least {min_motion_clips} motion clips; found {len(motion_clips_value)}"
        )
    if max_motion_clips is not None and len(motion_clips_value) > max_motion_clips:
        raise ValueError(
            f"manifest must declare at most {max_motion_clips} motion clips; found {len(motion_clips_value)}"
        )
    motion_clips: list[dict[str, object]] = []
    clip_ids: set[str] = set()
    for index, clip in enumerate(motion_clips_value):
        if not isinstance(clip, dict):
            raise ValueError(f"motion clip {index} must be an object")
        clip_id = clip.get("id")
        state = clip.get("state")
        phase_range = clip.get("phase_range")
        if not isinstance(clip_id, str) or not clip_id.strip():
            raise ValueError(f"motion clip {index} id must be non-empty")
        clip_id = clip_id.strip()
        if clip_id in clip_ids:
            raise ValueError(f"duplicate motion clip id: {clip_id}")
        if state not in STATE_SPECS:
            raise ValueError(f"motion clip {clip_id} uses unknown native state: {state}")
        if (
            not isinstance(phase_range, list)
            or len(phase_range) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in phase_range)
            or not 0 <= phase_range[0] <= phase_range[1] < len(phases)
        ):
            raise ValueError(
                f"motion clip {clip_id} phase_range must be two ordered phase indices"
            )
        clip_ids.add(clip_id)
        motion_clips.append(
            {"id": clip_id, "state": state, "phase_range": phase_range}
        )

    states = payload.get("states")
    if not isinstance(states, dict) or not states:
        raise ValueError("state-phase manifest must contain a non-empty states object")
    unknown = sorted(set(states) - set(STATE_SPECS))
    if unknown:
        raise ValueError(f"unknown native state(s): {', '.join(unknown)}")
    if require_all_states:
        missing = [state for state in STATE_SPECS if state not in states]
        if missing:
            raise ValueError(f"manifest is missing native state(s): {', '.join(missing)}")

    state_cells: OrderedDict[str, list[Image.Image]] = OrderedDict()
    state_metadata: list[dict[str, object]] = []
    for state, (row, renderer_columns) in STATE_SPECS.items():
        if state not in states:
            continue
        state_value = states[state]
        if not isinstance(state_value, dict):
            raise ValueError(f"{state} must be an object")
        explicit_phases = state_value.get("phases")
        atlas_sequence = state_value.get("atlas_sequence")
        image_sequence = state_value.get("image_sequence")
        declared_sequences = sum(
            isinstance(value, list)
            for value in (explicit_phases, atlas_sequence, image_sequence)
        )
        if declared_sequences != 1:
            raise ValueError(
                f"{state} must declare exactly one of phases, atlas_sequence, or image_sequence"
            )
        if isinstance(atlas_sequence, list):
            state_phases = [{"atlas_column": value} for value in atlas_sequence]
        elif isinstance(image_sequence, list):
            state_phases = [{"image": value} for value in image_sequence]
        else:
            state_phases = explicit_phases
        if len(state_phases) != len(phases):
            raise ValueError(
                f"{state} must declare exactly {len(phases)} phase sources"
            )
        cells: list[Image.Image] = []
        sources: list[dict[str, object]] = []
        for phase_index, phase_source in enumerate(state_phases):
            cell, source_metadata = load_source_cell(
                phase_source,
                manifest_path=manifest_path,
                source=source,
                default_row=row,
                state=state,
                phase_index=phase_index,
            )
            cells.append(cell)
            sources.append(source_metadata)
        state_cells[state] = cells
        state_metadata.append(
            {
                "state": state,
                "atlas_row": row,
                "renderer_columns": renderer_columns,
                "sources": sources,
            }
        )
    return tuple(durations), labels, state_cells, state_metadata, motion_clips


def build_runtime_frames(
    source: Image.Image,
    state_cells: OrderedDict[str, list[Image.Image]],
) -> list[Image.Image]:
    phase_count = len(next(iter(state_cells.values())))
    if any(len(cells) != phase_count for cells in state_cells.values()):
        raise ValueError("all configured states must use the same image-time phase count")

    frames: list[Image.Image] = []
    for phase_index in range(phase_count):
        runtime = source.copy()
        for state, cells in state_cells.items():
            row, renderer_columns = STATE_SPECS[state]
            cell = cells[phase_index].convert("RGBA")
            for column in range(renderer_columns):
                runtime.paste(
                    cell,
                    (column * CELL_WIDTH, row * CELL_HEIGHT),
                )
        frames.append(runtime)
    return frames


def validate_runtime(
    runtime_path: Path,
    source: Image.Image,
    durations: tuple[int, ...],
    labels: list[str],
    state_cells: OrderedDict[str, list[Image.Image]],
    state_metadata: list[dict[str, object]],
    motion_clips: list[dict[str, object]],
) -> dict[str, object]:
    errors: list[str] = []
    expected_frames = build_runtime_frames(source, state_cells)
    try:
        actual_frames, actual_durations, loop = decoded_frames(runtime_path)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errors": [f"could not decode runtime atlas: {exc}"], "warnings": []}

    if len(actual_frames) != len(expected_frames):
        errors.append(f"expected {len(expected_frames)} animation frames, got {len(actual_frames)}")
    if tuple(actual_durations) != durations:
        errors.append(f"expected durations {list(durations)}, got {actual_durations}")
    if loop != 0:
        errors.append(f"expected infinite loop value 0, got {loop}")

    synchronized: dict[str, bool] = {state: True for state in state_cells}
    residue: list[int] = []
    for phase_index, (actual, expected) in enumerate(zip(actual_frames, expected_frames)):
        residue.append(transparent_rgb_residue(actual))
        if actual.size != ATLAS_SIZE:
            errors.append(
                f"animation frame {phase_index} has size {actual.width}x{actual.height}"
            )
            continue
        if not render_equal(actual, expected):
            errors.append(
                f"animation frame {phase_index} visibly differs from the deterministic state-phase map"
            )

        for state in state_cells:
            row, renderer_columns = STATE_SPECS[state]
            top = row * CELL_HEIGHT
            reference = actual.crop((0, top, CELL_WIDTH, top + CELL_HEIGHT))
            for column in range(1, renderer_columns):
                cell = actual.crop(
                    (
                        column * CELL_WIDTH,
                        top,
                        (column + 1) * CELL_WIDTH,
                        top + CELL_HEIGHT,
                    )
                )
                if not render_equal(cell, reference):
                    synchronized[state] = False
                    errors.append(
                        f"animation frame {phase_index} {state} column {column} is out of phase"
                    )

        if not render_equal(
            actual.crop((0, 9 * CELL_HEIGHT, ATLAS_SIZE[0], ATLAS_SIZE[1])),
            source.crop((0, 9 * CELL_HEIGHT, ATLAS_SIZE[0], ATLAS_SIZE[1])),
        ):
            errors.append(f"animation frame {phase_index} changes a look-direction row")

    return {
        "ok": not errors,
        "file": str(runtime_path),
        "format": "WEBP",
        "animated": True,
        "frame_count": len(actual_frames),
        "durations_ms": actual_durations,
        "loop_duration_ms": sum(actual_durations),
        "loop": loop,
        "phase_labels": labels,
        "states": state_metadata,
        "motion_clip_count": len(motion_clips),
        "motion_clips": motion_clips,
        "synchronized_state_rows": synchronized,
        "look_rows_unchanged": not any("look-direction row" in item for item in errors),
        "phase_map_exact": not any("state-phase map" in item for item in errors),
        "transparent_rgb_residue_pixels_per_frame": residue,
        "errors": errors,
        "warnings": [
            "All configured native states share one animated-WebP image clock and one duration timeline.",
            "State entry does not reset the image clock; every configured phase sequence must be a valid periodic loop.",
            "This wrapper adds visual submotions to the nine native triggers; it does not create new desktop event types.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-atlas", required=True)
    parser.add_argument("--phase-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json-out")
    parser.add_argument("--require-all-states", action="store_true")
    parser.add_argument("--min-motion-clips", type=int, default=0)
    parser.add_argument("--max-motion-clips", type=int)
    args = parser.parse_args()

    source_path = Path(args.source_atlas).expanduser().resolve()
    manifest_path = Path(args.phase_manifest).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    source = load_static_v2_atlas(source_path)
    durations, labels, state_cells, state_metadata, motion_clips = load_state_phase_manifest(
        manifest_path,
        source,
        require_all_states=args.require_all_states,
        min_motion_clips=args.min_motion_clips,
        max_motion_clips=args.max_motion_clips,
    )
    frames = build_runtime_frames(source, state_cells)
    save_runtime(frames, durations, output_path)
    result = validate_runtime(
        output_path,
        source,
        durations,
        labels,
        state_cells,
        state_metadata,
        motion_clips,
    )
    result.update(
        {
            "source_atlas": str(source_path),
            "source_sha256": sha256_file(source_path),
            "output_sha256": sha256_file(output_path),
            "phase_manifest": str(manifest_path),
        }
    )
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
