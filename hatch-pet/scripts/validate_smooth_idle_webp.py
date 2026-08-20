#!/usr/bin/env python3
"""Validate every frame of a hatch-pet smooth-idle animated WebP atlas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from package_smooth_idle_webp import (
    DEFAULT_DURATIONS,
    default_phase_plan,
    load_phase_manifest,
    load_static_v2_atlas,
    parse_durations,
    sha256_file,
    validate_runtime,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runtime_atlas")
    parser.add_argument("--source-atlas", required=True)
    parser.add_argument(
        "--durations",
        type=parse_durations,
        default=None,
        help="six comma-separated idle durations in milliseconds",
    )
    parser.add_argument("--phase-manifest")
    parser.add_argument("--json-out")
    args = parser.parse_args()

    runtime_path = Path(args.runtime_atlas).expanduser().resolve()
    source_path = Path(args.source_atlas).expanduser().resolve()
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
    result = validate_runtime(
        runtime_path,
        source,
        durations,
        phase_cells=phase_cells,
        phase_metadata=phase_metadata,
    )
    if runtime_path.exists():
        result["output_sha256"] = sha256_file(runtime_path)
    result["source_atlas"] = str(source_path)
    result["source_sha256"] = sha256_file(source_path)
    result["phase_manifest"] = str(manifest_path) if manifest_path else None

    if args.json_out:
        Path(args.json_out).expanduser().resolve().write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
