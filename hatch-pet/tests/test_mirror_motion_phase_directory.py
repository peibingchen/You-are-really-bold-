import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mirror_motion_phase_directory import mirror_phase_directory  # noqa: E402


class MirrorMotionPhaseDirectoryTest(unittest.TestCase):
    def test_mirrors_each_phase_without_reversing_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "right"
            output = root / "left"
            source.mkdir()
            expected: list[Image.Image] = []
            for index in range(4):
                phase = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
                draw = ImageDraw.Draw(phase)
                draw.rectangle(
                    (12 + index * 7, 30, 54 + index * 7, 185),
                    fill=(40 + index * 30, 120, 210, 255),
                )
                phase.save(source / f"{index:02d}.png")
                expected.append(ImageOps.mirror(phase))

            outputs = mirror_phase_directory(
                source,
                output,
                expected_count=4,
            )

            self.assertEqual([path.name for path in outputs], ["00.png", "01.png", "02.png", "03.png"])
            for index, output_path in enumerate(outputs):
                with Image.open(output_path) as opened:
                    actual = opened.convert("RGBA")
                self.assertEqual(actual.tobytes(), expected[index].tobytes())

    def test_rejects_wrong_phase_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "right"
            source.mkdir()
            Image.new("RGBA", (192, 208), (255, 120, 0, 255)).save(source / "00.png")

            with self.assertRaisesRegex(ValueError, "expected 2 source phases"):
                mirror_phase_directory(source, root / "left", expected_count=2)


if __name__ == "__main__":
    unittest.main()
