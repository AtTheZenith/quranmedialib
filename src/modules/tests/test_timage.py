"""
Tests for the timage module.
"""

import os
from PIL import ImageOps
from src.modules.timage import get_timage, TextConfig


def test_timage_formatting():
    print("\nRunning test_timage_formatting...")
    output_dir = "./output/test/timage"
    os.makedirs(output_dir, exist_ok=True)

    max_width = 1000
    config = TextConfig(font_size=48)

    # 1. Plain text
    img1 = get_timage("Hello World!", max_width, config)
    img1.save(f"{output_dir}/plain.png")

    # 2. Bold Red
    img2 = get_timage("#b#ff0000#Bold Red Text#", max_width, config)
    img2.save(f"{output_dir}/bold_red.png")

    # 3. Italic Green
    img3 = get_timage("#i#00ff00#Italic Green Text#", max_width, config)
    img3.save(f"{output_dir}/italic_green.png")

    # 4. Bold Italic Blue
    img4 = get_timage("#bi#0000ffff#Bold Italic Blue Text#", max_width, config)
    img4.save(f"{output_dir}/bold_italic_blue.png")

    # 5. Right Aligned
    config_right = TextConfig(font_size=48, horizontal_align="right")
    img5 = get_timage("Right Aligned Text", max_width, config_right)
    img5.save(f"{output_dir}/right_aligned.png")

    # 6. Center Aligned in larger canvas
    img6 = get_timage("#b#ffffff#Centered in 400px height#", max_width, config, max_height=400)
    # Re-calculate vertical center manually for verification if needed, but the tool does it.
    # Drawing a border to see the canvas height
    img6_with_border = ImageOps.expand(img6, border=2, fill="white")
    img6_with_border.save(f"{output_dir}/center_vertical.png")

    print(f"test_timage_formatting completed. Results saved to {output_dir}")


if __name__ == "__main__":
    test_timage_formatting()
