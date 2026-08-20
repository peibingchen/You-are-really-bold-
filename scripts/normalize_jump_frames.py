#!/usr/bin/env python3
"""Normalize Feidudu's generated jump poses without erasing the jump arc."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


CELL = (192, 208)
TARGET_HEIGHT = 174
TARGET_BOTTOMS = (201, 190, 177, 190, 201)


def clear_hidden_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for offset in range(0, len(data), 4):
        if data[offset + 3] == 0:
            data[offset : offset + 3] = b"\x00\x00\x00"
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def normalize(source: Image.Image, target_bottom: int) -> Image.Image:
    bbox = source.getbbox()
    if bbox is None:
        raise ValueError("jump phase is empty")
    sprite = source.crop(bbox).convert("RGBA")
    scale = min(TARGET_HEIGHT / sprite.height, 182 / sprite.width)
    sprite = sprite.resize(
        (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))),
        Image.Resampling.LANCZOS,
    )
    output = Image.new("RGBA", CELL, (0, 0, 0, 0))
    left = (CELL[0] - sprite.width) // 2
    top = target_bottom - sprite.height
    output.alpha_composite(sprite, (left, top))
    return clear_hidden_rgb(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-dir", required=True)
    args = parser.parse_args()
    frames_dir = Path(args.frames_dir).expanduser().resolve()
    paths = sorted(frames_dir.glob("*.png"))
    if len(paths) != len(TARGET_BOTTOMS):
        raise SystemExit(f"expected {len(TARGET_BOTTOMS)} jump phases, found {len(paths)}")
    for path, bottom in zip(paths, TARGET_BOTTOMS):
        with Image.open(path) as opened:
            result = normalize(opened.convert("RGBA"), bottom)
        result.save(path, optimize=True)
    print(f"normalized {len(paths)} jump frames in {frames_dir}")


if __name__ == "__main__":
    main()
