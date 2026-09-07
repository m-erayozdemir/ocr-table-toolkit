"""Generate a synthetic table image; no internship documents are used."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    rows = [("0", "STATE_IDLE"), ("1", "STATE_READY"), ("2", "STATE_RUNNING")]
    image = Image.new("RGB", (900, 330), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=34)
    for x in (20, 220, 880):
        draw.line((x, 20, x, 310), fill="black", width=3)
    for y in (20, 116, 213, 310):
        draw.line((20, y, 880, y), fill="black", width=3)
    for i, (value, name) in enumerate(rows):
        y = 50 + i * 97
        draw.text((65, y), value, font=font, fill="black")
        draw.text((260, y), name, font=font, fill="black")
    target = Path(__file__).with_name("sample-table.png")
    image.save(target)
    print(target)


if __name__ == "__main__":
    main()
