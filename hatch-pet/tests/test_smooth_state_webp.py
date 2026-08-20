import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from package_smooth_idle_webp import ATLAS_SIZE, CELL_HEIGHT, CELL_WIDTH, load_static_v2_atlas, save_runtime  # noqa: E402
from package_smooth_state_webp import (  # noqa: E402
    STATE_SPECS,
    build_runtime_frames,
    load_state_phase_manifest,
    validate_runtime,
)


class SmoothStateWebpTest(unittest.TestCase):
    def make_source(self, path: Path) -> None:
        atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
        draw = ImageDraw.Draw(atlas)
        for state_index, (_state, (row, columns)) in enumerate(STATE_SPECS.items()):
            for column in range(columns):
                left = column * CELL_WIDTH + 28
                top = row * CELL_HEIGHT + 32
                draw.rectangle(
                    (left, top, left + 100, top + 140),
                    fill=(30 + state_index * 20, 50 + column * 15, 180, 255),
                )
        neutral_left = 6 * CELL_WIDTH + 28
        draw.rectangle((neutral_left, 32, neutral_left + 100, 172), fill=(220, 140, 30, 255))
        for row in (9, 10):
            for column in range(8):
                left = column * CELL_WIDTH + 40
                top = row * CELL_HEIGHT + 40
                draw.ellipse((left, top, left + 90, top + 120), fill=(80, 120, 160, 255))
        atlas.save(path)

    def test_runtime_synchronizes_multiple_native_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.png"
            runtime_path = root / "runtime.webp"
            manifest_path = root / "phases.json"
            self.make_source(source_path)

            external = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
            ImageDraw.Draw(external).ellipse((35, 25, 157, 190), fill=(245, 165, 25, 255))
            external.save(root / "working.png")
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "phases": [
                            {"label": "a", "duration_ms": 80},
                            {"label": "b", "duration_ms": 90},
                            {"label": "c", "duration_ms": 100},
                        ],
                        "motion_clips": [
                            {"id": "work", "state": "running", "phase_range": [0, 2]}
                        ],
                        "states": {
                            "idle": {
                                "phases": [
                                    {"atlas_column": 0},
                                    {"atlas_column": 1},
                                    {"atlas_column": 2},
                                ]
                            },
                            "running": {
                                "phases": [
                                    {"atlas_column": 0},
                                    {"image": "working.png"},
                                    {"atlas_column": 1},
                                ]
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )

            source = load_static_v2_atlas(source_path)
            durations, labels, state_cells, metadata, motion_clips = load_state_phase_manifest(
                manifest_path, source, min_motion_clips=1, max_motion_clips=1
            )
            frames = build_runtime_frames(source, state_cells)
            save_runtime(frames, durations, runtime_path)
            result = validate_runtime(
                runtime_path,
                source,
                durations,
                labels,
                state_cells,
                metadata,
                motion_clips,
            )

            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["frame_count"], 3)
            self.assertEqual(result["durations_ms"], [80, 90, 100])
            self.assertEqual(result["phase_labels"], ["a", "b", "c"])
            self.assertEqual(result["motion_clip_count"], 1)
            self.assertEqual(result["synchronized_state_rows"], {"idle": True, "running": True})
            self.assertTrue(result["look_rows_unchanged"])
            self.assertTrue(result["phase_map_exact"])

    def test_require_all_states_rejects_partial_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.png"
            manifest_path = root / "phases.json"
            self.make_source(source_path)
            manifest_path.write_text(
                json.dumps(
                    {
                        "phases": [
                            {"duration_ms": 80},
                            {"duration_ms": 80},
                        ],
                        "states": {
                            "idle": {
                                "phases": [
                                    {"atlas_column": 0},
                                    {"atlas_column": 1},
                                ]
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            source = load_static_v2_atlas(source_path)
            with self.assertRaisesRegex(ValueError, "missing native state"):
                load_state_phase_manifest(manifest_path, source, require_all_states=True)


if __name__ == "__main__":
    unittest.main()
