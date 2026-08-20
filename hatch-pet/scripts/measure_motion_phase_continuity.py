#!/usr/bin/env python3
"""Measure registration and silhouette continuity across a periodic motion loop."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image

from validate_atlas import chroma_fringe_count, opaque_chroma_key_count, parse_hex_color

CELL_SIZE = (192, 208)


def image_files(path: Path) -> list[Path]:
    return sorted(
        item
        for item in path.iterdir()
        if item.is_file() and item.suffix.lower() in {".png", ".webp"}
    )


def geometry(
    path: Path,
    chroma_key: tuple[int, int, int],
    chroma_leak_threshold: float,
    chroma_fringe_threshold: float,
) -> dict[str, object]:
    with Image.open(path) as opened:
        if opened.size != CELL_SIZE:
            raise ValueError(f"{path} must be {CELL_SIZE[0]}x{CELL_SIZE[1]}")
        rgba = opened.convert("RGBA")
        alpha = rgba.getchannel("A")
    points = [
        (x, y)
        for y in range(CELL_SIZE[1])
        for x in range(CELL_SIZE[0])
        if alpha.getpixel((x, y)) > 16
    ]
    if not points:
        raise ValueError(f"{path} is empty")
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    left, top, right, bottom = min(xs), min(ys), max(xs) + 1, max(ys) + 1
    lower_threshold = top + (bottom - top) * 0.72
    lower = [point for point in points if point[1] >= lower_threshold] or points
    edge_pixels = sum(
        x < 2 or x >= CELL_SIZE[0] - 2 or y < 2 or y >= CELL_SIZE[1] - 2
        for x, y in points
    )
    return {
        "file": str(path),
        "area": len(points),
        "bbox": [left, top, right, bottom],
        "centroid": [sum(xs) / len(xs), sum(ys) / len(ys)],
        "lower_center_x": sum(x for x, _y in lower) / len(lower),
        "baseline": bottom,
        "edge_pixels": edge_pixels,
        "chroma_leak_pixels": opaque_chroma_key_count(
            rgba, chroma_key, chroma_leak_threshold
        ),
        "chroma_fringe_pixels": chroma_fringe_count(
            rgba,
            chroma_key=chroma_key,
            distance_threshold=chroma_fringe_threshold,
            edge_radius=2,
            alpha_minimum=16,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames_dir")
    parser.add_argument("--expected-count", type=int)
    parser.add_argument("--max-area-ratio", type=float, default=1.20)
    parser.add_argument("--max-centroid-shift", type=float, default=10.0)
    parser.add_argument("--max-lower-center-shift", type=float, default=8.0)
    parser.add_argument("--max-baseline-shift", type=int, default=5)
    parser.add_argument("--max-edge-pixels", type=int, default=0)
    parser.add_argument("--chroma-key", default="#00FF00")
    parser.add_argument("--chroma-leak-threshold", type=float, default=36.0)
    parser.add_argument("--chroma-fringe-threshold", type=float, default=96.0)
    parser.add_argument("--json-out")
    args = parser.parse_args()

    frames_dir = Path(args.frames_dir).expanduser().resolve()
    files = image_files(frames_dir)
    errors: list[str] = []
    if args.expected_count is not None and len(files) != args.expected_count:
        errors.append(f"expected {args.expected_count} frames, found {len(files)}")

    chroma_key = parse_hex_color(args.chroma_key)
    frames = [
        geometry(
            path,
            chroma_key,
            args.chroma_leak_threshold,
            args.chroma_fringe_threshold,
        )
        for path in files
    ]
    pairs: list[dict[str, object]] = []
    for index, current in enumerate(frames):
        next_index = (index + 1) % len(frames)
        following = frames[next_index]
        area_ratio = max(current["area"], following["area"]) / min(
            current["area"], following["area"]
        )
        centroid_shift = math.dist(current["centroid"], following["centroid"])
        lower_center_shift = abs(current["lower_center_x"] - following["lower_center_x"])
        baseline_shift = abs(current["baseline"] - following["baseline"])
        pair = {
            "from": index,
            "to": next_index,
            "area_ratio": area_ratio,
            "centroid_shift": centroid_shift,
            "lower_center_shift": lower_center_shift,
            "baseline_shift": baseline_shift,
        }
        pairs.append(pair)
        if area_ratio > args.max_area_ratio:
            errors.append(f"phase {index:02d}->{next_index:02d} area ratio {area_ratio:.3f}")
        if centroid_shift > args.max_centroid_shift:
            errors.append(
                f"phase {index:02d}->{next_index:02d} centroid shift {centroid_shift:.2f}px"
            )
        if lower_center_shift > args.max_lower_center_shift:
            errors.append(
                f"phase {index:02d}->{next_index:02d} lower anchor shift {lower_center_shift:.2f}px"
            )
        if baseline_shift > args.max_baseline_shift:
            errors.append(
                f"phase {index:02d}->{next_index:02d} baseline shift {baseline_shift}px"
            )

    for index, frame in enumerate(frames):
        if frame["edge_pixels"] > args.max_edge_pixels:
            errors.append(f"phase {index:02d} has {frame['edge_pixels']} near-edge pixels")
        if frame["chroma_leak_pixels"]:
            errors.append(
                f"phase {index:02d} has {frame['chroma_leak_pixels']} visible chroma-key pixels"
            )
        if frame["chroma_fringe_pixels"]:
            errors.append(
                f"phase {index:02d} has {frame['chroma_fringe_pixels']} chroma-contaminated edge pixels"
            )

    result = {
        "ok": not errors,
        "frames_dir": str(frames_dir),
        "frame_count": len(frames),
        "frames": frames,
        "pairs": pairs,
        "errors": errors,
        "warnings": [
            "Continuity metrics cannot prove anatomy; visually inspect every numbered phase for detached or extra limbs."
        ],
    }
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
