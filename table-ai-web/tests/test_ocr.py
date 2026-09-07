"""Real OCR regression checks using synthetic cells (requires cached weights).

Run from table-ai-web: python -m unittest discover -s tests
"""
import unittest

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app import ocr_text


class CellRecognitionTests(unittest.TestCase):
    def cell(self, text):
        image = Image.new("RGB", (340, 140), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 330, 130), outline="black", width=3)
        draw.text((170, 70), text, font=ImageFont.load_default(size=64),
                  anchor="mm", fill="black")
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def test_isolated_digits_are_not_dropped(self):
        for digit in ("0", "1", "2"):
            with self.subTest(digit=digit):
                self.assertEqual(ocr_text(self.cell(digit), (10, 10, 330, 130)), digit)

    def test_empty_cell_stays_empty(self):
        self.assertEqual(ocr_text(self.cell(""), (10, 10, 330, 130)), "")


if __name__ == "__main__":
    unittest.main()
