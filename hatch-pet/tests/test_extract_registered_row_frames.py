import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from extract_registered_row_frames import (  # noqa: E402
    CELL_HEIGHT,
    CELL_WIDTH,
    FRAME_COUNT,
    extract_registered_frames,
)


class ExtractRegisteredRowFramesTest(unittest.TestCase):
    def test_exact_cell_crops_preserve_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            row_path = Path(temporary) / "row.png"
            row = Image.new("RGBA", (CELL_WIDTH * FRAME_COUNT, CELL_HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(row)
            for index in range(FRAME_COUNT):
                left = index * CELL_WIDTH
                draw.rectangle(
                    (left + 20 + index, 30, left + 80 + index, 180),
                    fill=(20 * index, 90, 180, 255),
                )
            row.save(row_path)

            frames = extract_registered_frames(row_path)

            self.assertEqual(len(frames), FRAME_COUNT)
            for index, frame in enumerate(frames):
                self.assertEqual(frame.size, (CELL_WIDTH, CELL_HEIGHT))
                self.assertEqual(frame.getchannel("A").getbbox(), (20 + index, 30, 81 + index, 181))


if __name__ == "__main__":
    unittest.main()
