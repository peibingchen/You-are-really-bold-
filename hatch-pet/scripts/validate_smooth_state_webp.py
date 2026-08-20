#!/usr/bin/env python3
"""Validate every image-time phase of a synchronized native-state WebP atlas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from package_smooth_idle_webp import load_static_v2_atlas, sha256_file
from package_smooth_state_webp import load_state_phase_manifest, validate_runtime


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_atlas")
    parser.add_argument("--source-atlas", required=True)
    parser.add_argument("--phase-manifest", required=True)
    parser.add_argument("--json-out")
    parser.add_argument("--require-all-states", action="store_true")
    parser.add_argument("--min-motion-clips", type=int, default=0)
    parser.add_argument("--max-motion-clips", type=int)
    args = parser.parse_args()

    runtime_path = Path(args.runtime_atlas).expanduser().resolve()
    source_path = Path(args.source_atlas).expanduser().resolve()
    manifest_path = Path(args.phase_manifest).expanduser().resolve()
    source = load_static_v2_atlas(source_path)
    durations, labels, state_cells, state_metadata, motion_clips = load_state_phase_manifest(
        manifest_path,
        source,
        require_all_states=args.require_all_states,
        min_motion_clips=args.min_motion_clips,
        max_motion_clips=args.max_motion_clips,
    )
    result = validate_runtime(
        runtime_path,
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
            "phase_manifest": str(manifest_path),
        }
    )
    if runtime_path.exists():
        result["output_sha256"] = sha256_file(runtime_path)
    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
