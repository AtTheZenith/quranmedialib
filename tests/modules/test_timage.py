"""
Tests for the timage module.
"""

import os

from PIL import ImageOps

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.timage import get_timage


def test_timage_formatting():
    print("\nRunning test_timage_formatting...")
    output_dir = "./output/test/timage"
    os.makedirs(output_dir, exist_ok=True)

    layout_config, text_config, word_config = LANDSCAPE_PRESET["default"]["1080p"]

    # 1. Plain text
    img1 = get_timage("Hello World!", text_config)
    img1.save(f"{output_dir}/plain.png")

    # 2. Bold Red
    img2 = get_timage("#b#ff0000#Bold Red Text#", text_config)
    img2.save(f"{output_dir}/bold_red.png")

    # 3. Italic Green
    img3 = get_timage("#i#00ff00#Italic Green Text#", text_config)
    img3.save(f"{output_dir}/italic_green.png")

    # 4. Bold Italic Blue
    img4 = get_timage("#bi#0000ffff#Bold Italic Blue Text#", text_config)
    img4.save(f"{output_dir}/bold_italic_blue.png")

    # 5. Custom max_height (centered vertically in larger canvas)
    img5 = get_timage("#b#ffffff#Centered in 400px height#", text_config, max_height=400)
    # Drawing a border to see the canvas height
    img5_with_border = ImageOps.expand(img5, border=2, fill="white")
    img5_with_border.save(f"{output_dir}/center_vertical.png")

    print(f"test_timage_formatting completed. Results saved to {output_dir}")


if __name__ == "__main__":
    test_timage_formatting()
