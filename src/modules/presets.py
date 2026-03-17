from src.modules.configs import LayoutConfig, TextConfig, WordConfig

# Common Presets

# Landscape (16:9) Presets
LANDSCAPE_PRESET = {
    "default": {
        "720p": (
            LayoutConfig(
                max_width=1280,
                image_height=720,
                padding=33,
                bottom_offset=200,
            ),
            TextConfig(font_size=24, line_spacing=7),
            WordConfig(
                word_spacing=13,
                row_spacing=20,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1920,
                image_height=1080,
                padding=50,
                bottom_offset=300,
            ),
            TextConfig(font_size=36, line_spacing=10),
            WordConfig(
                word_spacing=20,
                row_spacing=30,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=2560,
                image_height=1440,
                padding=67,
                bottom_offset=400,
            ),
            TextConfig(font_size=48, line_spacing=13),
            WordConfig(
                word_spacing=27,
                row_spacing=40,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=3840,
                image_height=2160,
                padding=100,
                bottom_offset=600,
            ),
            TextConfig(font_size=72, line_spacing=20),
            WordConfig(
                word_spacing=40,
                row_spacing=60,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
            ),
        ),
    },
    "arabic": {
        "720p": (
            LayoutConfig(
                max_width=1280,
                image_height=720,
                padding=33,
                bottom_offset=0,
            ),
            TextConfig(font_size=24, line_spacing=7),
            WordConfig(
                word_spacing=13,
                row_spacing=20,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 9, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1920,
                image_height=1080,
                padding=50,
                bottom_offset=0,
            ),
            TextConfig(font_size=36, line_spacing=10),
            WordConfig(
                word_spacing=20,
                row_spacing=30,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 14, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=2560,
                image_height=1440,
                padding=67,
                bottom_offset=0,
            ),
            TextConfig(font_size=48, line_spacing=13),
            WordConfig(
                word_spacing=27,
                row_spacing=40,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 19, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=3840,
                image_height=2160,
                padding=100,
                bottom_offset=0,
            ),
            TextConfig(font_size=72, line_spacing=20),
            WordConfig(
                word_spacing=40,
                row_spacing=60,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 28, 2, 2),
            ),
        ),
    },
    "translation": {
        "720p": (
            LayoutConfig(
                max_width=1280,
                image_height=720,
                padding=33,
                bottom_offset=360,
            ),
            TextConfig(font_size=24, line_spacing=7),
            WordConfig(
                word_spacing=13,
                row_spacing=20,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1920,
                image_height=1080,
                padding=50,
                bottom_offset=540,
            ),
            TextConfig(font_size=36, line_spacing=10),
            WordConfig(
                word_spacing=20,
                row_spacing=30,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=2560,
                image_height=1440,
                padding=67,
                bottom_offset=720,
            ),
            TextConfig(font_size=48, line_spacing=13),
            WordConfig(
                word_spacing=27,
                row_spacing=40,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=3840,
                image_height=2160,
                padding=100,
                bottom_offset=1080,
            ),
            TextConfig(font_size=72, line_spacing=20),
            WordConfig(
                word_spacing=40,
                row_spacing=60,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
            ),
        ),
    },
}

# Portrait/Story (9:16) Presets
STORY_PRESET = {
    "default": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=1280,
                padding=40,
                bottom_offset=300,
            ),
            TextConfig(font_size=24, line_spacing=10),
            WordConfig(
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1920,
                padding=60,
                bottom_offset=450,
            ),
            TextConfig(font_size=36, line_spacing=15),
            WordConfig(
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=2560,
                padding=80,
                bottom_offset=600,
            ),
            TextConfig(font_size=48, line_spacing=20),
            WordConfig(
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=3840,
                padding=120,
                bottom_offset=900,
            ),
            TextConfig(font_size=72, line_spacing=30),
            WordConfig(
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
            ),
        ),
    },
    "arabic": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=1280,
                padding=40,
                bottom_offset=0,
            ),
            TextConfig(font_size=24, line_spacing=10),
            WordConfig(
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 9, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1920,
                padding=60,
                bottom_offset=0,
            ),
            TextConfig(font_size=36, line_spacing=15),
            WordConfig(
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 14, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=2560,
                padding=80,
                bottom_offset=0,
            ),
            TextConfig(font_size=48, line_spacing=20),
            WordConfig(
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 19, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=3840,
                padding=120,
                bottom_offset=0,
            ),
            TextConfig(font_size=72, line_spacing=30),
            WordConfig(
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 28, 2, 2),
            ),
        ),
    },
    "translation": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=1280,
                padding=40,
                bottom_offset=640,
            ),
            TextConfig(font_size=24, line_spacing=10),
            WordConfig(
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1920,
                padding=60,
                bottom_offset=960,
            ),
            TextConfig(font_size=36, line_spacing=15),
            WordConfig(
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=2560,
                padding=80,
                bottom_offset=1280,
            ),
            TextConfig(font_size=48, line_spacing=20),
            WordConfig(
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=3840,
                padding=120,
                bottom_offset=1920,
            ),
            TextConfig(font_size=72, line_spacing=30),
            WordConfig(
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
            ),
        ),
    },
}

SQUARE_PRESET = {
    "default": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=720,
                padding=40,
                bottom_offset=0,
            ),
            TextConfig(font_size=24, line_spacing=10),
            WordConfig(
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1080,
                padding=60,
                bottom_offset=0,
            ),
            TextConfig(font_size=36, line_spacing=15),
            WordConfig(
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=1440,
                padding=80,
                bottom_offset=0,
            ),
            TextConfig(font_size=48, line_spacing=20),
            WordConfig(
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=2160,
                padding=120,
                bottom_offset=0,
            ),
            TextConfig(font_size=72, line_spacing=30),
            WordConfig(
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
            ),
        ),
    },
    "arabic": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=720,
                padding=40,
                bottom_offset=0,
            ),
            TextConfig(font_size=24, line_spacing=10),
            WordConfig(
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 9, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1080,
                padding=60,
                bottom_offset=0,
            ),
            TextConfig(font_size=36, line_spacing=15),
            WordConfig(
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 14, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=1440,
                padding=80,
                bottom_offset=0,
            ),
            TextConfig(font_size=48, line_spacing=20),
            WordConfig(
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 19, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=2160,
                padding=120,
                bottom_offset=0,
            ),
            TextConfig(font_size=72, line_spacing=30),
            WordConfig(
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 28, 2, 2),
            ),
        ),
    },
    "translation": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=720,
                padding=40,
                bottom_offset=0,
            ),
            TextConfig(font_size=24, line_spacing=10),
            WordConfig(
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1080,
                padding=60,
                bottom_offset=0,
            ),
            TextConfig(font_size=36, line_spacing=15),
            WordConfig(
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=1440,
                padding=80,
                bottom_offset=0,
            ),
            TextConfig(font_size=48, line_spacing=20),
            WordConfig(
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=2160,
                padding=120,
                bottom_offset=0,
            ),
            TextConfig(font_size=72, line_spacing=30),
            WordConfig(
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
            ),
        ),
    },
}
