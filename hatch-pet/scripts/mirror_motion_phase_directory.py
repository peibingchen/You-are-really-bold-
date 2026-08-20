#!/usr/bin/env python3
"""Mirror an approved motion-phase directory while preserving phase order."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

CELL_SIZE = (192, 208)
IMAGE_SUFFIXES = {".png", ".webp"}


def image_files(path: Path) -> list[Path]:
    if not path.is_dir():
        raise ValueError(f"source phase directory does not exist: {path}")
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES
    )


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index : index + 3] = b"\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def mirror_phase_directory(
    source_dir: Path,
    output_dir: Path,
    *,
    expected_count: int,
    force: bool = False,
) -> list[Path]:
    source_dir = source_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if source_dir == output_dir:
        raise ValueError("source and output phase directories must differ")
    files = image_files(source_dir)
    if len(files) != expected_count:
        raise ValueError(
            f"expected {expected_count} source phases, found {len(files)}"
        )
    if output_dir.exists() and any(output_dir.iterdir()) and not force:
        raise ValueError(f"output directory is not empty: {output_dir}; pass --force")

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for index, source_path in enumerate(files):
        with Image.open(source_path) as opened:
            if getattr(opened, "is_animated", False) and getattr(opened, "n_frames", 1) > 1:
                raise ValueError(f"phase must be static: {source_path}")
            if opened.size != CELL_SIZE:
                raise ValueError(
                    f"phase must be {CELL_SIZE[0]}x{CELL_SIZE[1]}: {source_path}"
                )
            source = opened.convert("RGBA")
        if source.getbbox() is None:
            raise ValueError(f"phase is empty: {source_path}")
        mirrored = clear_transparent_rgb(ImageOps.mirror(source))
        output = output_dir / f"{index:02d}.png"
        mirrored.save(output, optimize=True)
        outputs.append(output)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--decision-note", required=True)
    parser.add_argument("--confirm-appropriate-mirror", action="store_true")
    parser.add_argument("--json-out")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.confirm_appropriate_mirror:
        parser.error("refusing to mirror without --confirm-appropriate-mirror")
    if args.expected_count < 2:
        parser.error("--expected-count must be at least 2")
    if not args.decision_note.strip():
        parser.error("--decision-note must explain why mirroring is appropriate")

    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    try:
        outputs = mirror_phase_directory(
            source_dir,
            output_dir,
            expected_count=args.expected_count,
            force=args.force,
        )
    except ValueError as exc:
        parser.error(str(exc))

    result = {
        "ok": True,
        "source_dir": str(source_dir.expanduser().resolve()),
        "output_dir": str(output_dir.expanduser().resolve()),
        "phase_count": len(outputs),
        "phase_order_preserved": True,
        "transform": "framewise-horizontal-mirror-preserving-order",
        "decision_note": args.decision_note.strip(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "outputs": [str(path) for path in outputs],
    }
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
