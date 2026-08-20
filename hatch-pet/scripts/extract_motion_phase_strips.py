#!/usr/bin/env python3
"""Extract and register arbitrary motion-phase strips into 192x208 cells."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from assemble_extended_atlas import (
    clear_transparent_rgb,
    normalize_cells_to_reference,
)
from extract_strip_frames import (
    component_frame_groups,
    component_group_image,
    fit_to_cell,
    parse_hex_color,
    remove_chroma_background,
)


def load_strip(
    path: Path,
    frame_count: int,
    chroma_key: tuple[int, int, int] | None,
    chroma_threshold: float,
) -> list[Image.Image]:
    with Image.open(path) as opened:
        strip = opened.convert("RGBA")
    if chroma_key is not None:
        strip = remove_chroma_background(strip, chroma_key, chroma_threshold)

    groups = component_frame_groups(strip, frame_count)
    if groups is None:
        raise ValueError(
            f"could not recover {frame_count} separated pose groups from {path}"
        )
    return [fit_to_cell(component_group_image(strip, group)) for group in groups]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("strips", nargs="+")
    parser.add_argument("--frames-per-strip", type=int, required=True)
    parser.add_argument("--reference-cell", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json-out")
    parser.add_argument(
        "--chroma-key",
        help="optional #RRGGBB key; omit for strips that already contain alpha",
    )
    parser.add_argument("--chroma-threshold", type=float, default=60.0)
    args = parser.parse_args()

    if args.frames_per_strip < 2:
        parser.error("--frames-per-strip must be at least 2")

    strip_paths = [Path(value).expanduser().resolve() for value in args.strips]
    reference_path = Path(args.reference_cell).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    chroma_key = parse_hex_color(args.chroma_key) if args.chroma_key else None

    with Image.open(reference_path) as opened:
        reference = opened.convert("RGBA")
    if reference.size != (192, 208) or reference.getbbox() is None:
        parser.error("--reference-cell must be a populated 192x208 RGBA image")

    raw_cells: list[Image.Image] = []
    for strip_path in strip_paths:
        raw_cells.extend(
            load_strip(
                strip_path,
                args.frames_per_strip,
                chroma_key,
                args.chroma_threshold,
            )
        )

    registered = normalize_cells_to_reference(raw_cells, reference)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    frames: list[dict[str, object]] = []
    for index, cell in enumerate(registered):
        output = output_dir / f"{index:02d}.png"
        cleaned = clear_transparent_rgb(cell)
        cleaned.save(output, optimize=True)
        outputs.append(str(output))
        frames.append(
            {
                "index": index,
                "file": str(output),
                "bbox": list(cleaned.getbbox() or (0, 0, 0, 0)),
                "nontransparent_pixels": sum(cleaned.getchannel("A").histogram()[1:]),
            }
        )

    result = {
        "ok": True,
        "strips": [str(path) for path in strip_paths],
        "frames_per_strip": args.frames_per_strip,
        "frame_count": len(registered),
        "reference_cell": str(reference_path),
        "output_dir": str(output_dir),
        "outputs": outputs,
        "frames": frames,
    }
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
