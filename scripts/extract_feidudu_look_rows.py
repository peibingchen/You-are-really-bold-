#!/usr/bin/env python3
"""Extract and equalize Feidudu's two coherent gaze rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "hatch-pet" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from assemble_extended_atlas import (  # noqa: E402
    cell_geometry,
    clear_transparent_rgb,
    component_frame_groups,
    component_group_image,
    remove_chroma_background,
)


CELL = (192, 208)
DIRECTIONS = (
    "000",
    "022.5",
    "045",
    "067.5",
    "090",
    "112.5",
    "135",
    "157.5",
    "180",
    "202.5",
    "225",
    "247.5",
    "270",
    "292.5",
    "315",
    "337.5",
)


def extract_row(path: Path) -> list[Image.Image]:
    with Image.open(path) as opened:
        transparent = remove_chroma_background(opened, (255, 0, 255), 96.0)
    groups = component_frame_groups(transparent, 8)
    if groups is None:
        raise ValueError(f"could not recover eight pose groups from {path}")
    return [component_group_image(transparent, group, padding=4) for group in groups]


def normalize_pose(pose: Image.Image, target_height: int, target_bottom: int, target_x: float) -> Image.Image:
    bbox = pose.getbbox()
    if bbox is None:
        raise ValueError("look pose is empty")
    crop = pose.crop(bbox).convert("RGBA")
    geometry = cell_geometry(crop)
    if geometry is None:
        raise ValueError("look pose has no visible geometry")
    scale = min(target_height / geometry.height, 182 / crop.width)
    crop = crop.resize(
        (max(1, round(crop.width * scale)), max(1, round(crop.height * scale))),
        Image.Resampling.LANCZOS,
    )
    scaled_geometry = cell_geometry(crop)
    if scaled_geometry is None:
        raise ValueError("normalized look pose is empty")
    left = round(target_x - scaled_geometry.lower_center_x)
    top = target_bottom - scaled_geometry.bottom
    output = Image.new("RGBA", CELL, (0, 0, 0, 0))
    output.alpha_composite(crop, (left, top))
    return clear_transparent_rgb(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row-9", required=True)
    parser.add_argument("--row-10", required=True)
    parser.add_argument("--neutral", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with Image.open(Path(args.neutral).expanduser().resolve()) as opened:
        neutral = opened.convert("RGBA")
    target = cell_geometry(neutral)
    if target is None:
        raise SystemExit("neutral reference is empty")
    target_height = min(target.height, 192)
    poses = extract_row(Path(args.row_9).expanduser().resolve())
    poses.extend(extract_row(Path(args.row_10).expanduser().resolve()))
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for label, pose in zip(DIRECTIONS, poses):
        normalized = normalize_pose(pose, target_height, target.bottom, target.lower_center_x)
        normalized.save(output_dir / f"{label}.png", optimize=True)
    print(f"wrote {len(poses)} normalized gaze cells to {output_dir}")


if __name__ == "__main__":
    main()
