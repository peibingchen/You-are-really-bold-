import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from package_smooth_idle_webp import (  # noqa: E402
    ATLAS_SIZE,
    CELL_HEIGHT,
    CELL_WIDTH,
    DEFAULT_DURATIONS,
    IDLE_FRAME_COUNT,
    build_runtime_frames,
    decoded_frames,
    load_phase_manifest,
    load_static_v2_atlas,
    save_runtime,
    validate_runtime,
)


class SmoothIdleWebpTest(unittest.TestCase):
    def test_runtime_retimes_idle_and_preserves_other_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.png"
            runtime_path = root / "runtime.webp"
            atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
            draw = ImageDraw.Draw(atlas)
            for column in range(IDLE_FRAME_COUNT):
                left = column * CELL_WIDTH + 24
                color = (30 + column * 30, 80 + column * 20, 180 - column * 20, 255)
                draw.rectangle((left, 40, left + 96, 168), fill=color)
            neutral_left = IDLE_FRAME_COUNT * CELL_WIDTH + 24
            draw.rectangle(
                (neutral_left, 40, neutral_left + 96, 168),
                fill=(200, 150, 40, 255),
            )
            draw.rectangle((24, CELL_HEIGHT + 24, 120, CELL_HEIGHT + 160), fill=(12, 34, 56, 255))
            atlas.save(source_path)

            source = load_static_v2_atlas(source_path)
            frames = build_runtime_frames(source)
            save_runtime(frames, DEFAULT_DURATIONS, runtime_path)
            result = validate_runtime(runtime_path, source, DEFAULT_DURATIONS)

            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["frame_count"], 6)
            self.assertEqual(result["durations_ms"], list(DEFAULT_DURATIONS))
            self.assertEqual(result["loop_duration_ms"], 1100)
            self.assertTrue(result["idle_columns_synchronized"])
            self.assertTrue(result["non_idle_rows_unchanged"])
            self.assertTrue(result["phase_map_exact"])

            decoded, durations, loop = decoded_frames(runtime_path)
            self.assertEqual(durations, list(DEFAULT_DURATIONS))
            self.assertEqual(loop, 0)
            for phase, frame in enumerate(decoded):
                expected = source.crop(
                    (
                        phase * CELL_WIDTH,
                        0,
                        (phase + 1) * CELL_WIDTH,
                        CELL_HEIGHT,
                    )
                ).tobytes()
                for column in range(IDLE_FRAME_COUNT):
                    actual = frame.crop(
                        (
                            column * CELL_WIDTH,
                            0,
                            (column + 1) * CELL_WIDTH,
                            CELL_HEIGHT,
                        )
                    ).tobytes()
                    self.assertEqual(actual, expected)

    def test_custom_phase_manifest_accepts_external_expressive_idle_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.png"
            runtime_path = root / "runtime.webp"
            manifest_path = root / "phases.json"
            atlas = Image.new("RGBA", ATLAS_SIZE, (0, 0, 0, 0))
            draw = ImageDraw.Draw(atlas)
            for column in range(IDLE_FRAME_COUNT):
                left = column * CELL_WIDTH + 24
                draw.rectangle((left, 40, left + 96, 168), fill=(40 + column * 20, 80, 180, 255))
            neutral_left = IDLE_FRAME_COUNT * CELL_WIDTH + 24
            draw.rectangle((neutral_left, 40, neutral_left + 96, 168), fill=(200, 150, 40, 255))
            draw.rectangle((24, CELL_HEIGHT + 24, 120, CELL_HEIGHT + 160), fill=(12, 34, 56, 255))
            atlas.save(source_path)

            custom = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
            ImageDraw.Draw(custom).ellipse((36, 24, 156, 184), fill=(244, 170, 22, 255))
            custom.save(root / "wave.png")
            manifest_path.write_text(
                '{"phases":['
                '{"label":"rest","atlas_row":0,"atlas_column":0,"duration_ms":220},'
                '{"label":"wave","image":"wave.png","duration_ms":160},'
                '{"label":"return","atlas_row":0,"atlas_column":1,"duration_ms":220}'
                ']}',
                encoding="utf-8",
            )

            source = load_static_v2_atlas(source_path)
            cells, durations, metadata = load_phase_manifest(manifest_path, source)
            frames = build_runtime_frames(source, cells)
            save_runtime(frames, durations, runtime_path)
            result = validate_runtime(
                runtime_path,
                source,
                durations,
                phase_cells=cells,
                phase_metadata=metadata,
            )

            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["frame_count"], 3)
            self.assertEqual(result["durations_ms"], [220, 160, 220])
            self.assertEqual([phase["label"] for phase in result["phases"]], ["rest", "wave", "return"])
            self.assertTrue(result["non_idle_rows_unchanged"])


if __name__ == "__main__":
    unittest.main()
