#!/usr/bin/env python3
"""Replace one native animation row in an approved static v2 atlas."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from package_smooth_idle_webp import ATLAS_SIZE, CELL_HEIGHT, CELL_WIDTH
from package_smooth_state_webp import STATE_SPECS


def image_files(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in {".png", ".webp"}
    )


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index : index + 3] = b"\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-atlas", required=True)
    parser.add_argument("--state", choices=STATE_SPECS, required=True)
    parser.add_argument("--frames-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_path = Path(args.source_atlas).expanduser().resolve()
    frames_dir = Path(args.frames_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    row, frame_count = STATE_SPECS[args.state]
    files = image_files(frames_dir)
    if len(files) != frame_count:
        parser.error(
            f"{args.state} requires exactly {frame_count} frame files; found {len(files)}"
        )

    with Image.open(source_path) as opened:
        if getattr(opened, "is_animated", False) and getattr(opened, "n_frames", 1) > 1:
            parser.error("--source-atlas must be static")
        if opened.size != ATLAS_SIZE:
            parser.error(
                f"--source-atlas must be {ATLAS_SIZE[0]}x{ATLAS_SIZE[1]}"
            )
        atlas = opened.convert("RGBA")

    top = row * CELL_HEIGHT
    atlas.paste(
        Image.new("RGBA", (ATLAS_SIZE[0], CELL_HEIGHT), (0, 0, 0, 0)),
        (0, top),
    )
    for column, frame_path in enumerate(files):
        with Image.open(frame_path) as opened:
            if opened.size != (CELL_WIDTH, CELL_HEIGHT):
                parser.error(
                    f"{frame_path} must be {CELL_WIDTH}x{CELL_HEIGHT}; got {opened.width}x{opened.height}"
                )
            frame = opened.convert("RGBA")
        if frame.getbbox() is None:
            parser.error(f"{frame_path} is empty")
        atlas.paste(frame, (column * CELL_WIDTH, top))

    atlas = clear_transparent_rgb(atlas)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(
        output_path,
        format="WEBP",
        lossless=True,
        quality=100,
        method=6,
        exact=True,
    )
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
