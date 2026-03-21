"""Default presets for fonts, databases, and layout configurations.

This module provides:
- FONT_* constants: Predefined FontResource instances for shipped fonts
- DATABASE_* constants: Predefined DatabaseConfig instances for shipped databases
- LANDSCAPE_PRESET, STORY_PRESET, SQUARE_PRESET: Layout configurations by resolution
"""

from quranmedialib.types import (
    DatabaseConfig,
    FontResource,
    LayoutConfig,
    TextConfig,
    WbwDatabaseConfig,
    WordConfig,
)

# === Font Presets ===
#: Hafs font for Arabic Quranic text rendering
FONT_HAFS = FontResource.from_packaged("hafs.otf", "Hafs")

#: Inter regular font for English text rendering
FONT_INTER = FontResource.from_packaged("inter.ttf", "Inter")

#: Inter italic font for English italic text rendering
FONT_INTER_ITALIC = FontResource.from_packaged("inter_italic.ttf", "Inter Italic")

#: Inter bold font for English bold text rendering
FONT_INTER_BOLD = FontResource.from_packaged("inter_bold.ttf", "Inter Bold")

#: Inter bold italic font for English bold italic text rendering
FONT_INTER_BOLD_ITALIC = FontResource.from_packaged("inter_bold_italic.ttf", "Inter Bold Italic")


# === Database Presets ===
#: Default Quran text database configuration
DATABASE_QURAN = DatabaseConfig.from_packaged(
    db_name="quran.db",
    tablename="verses",
    surah_col="sura",
    ayah_col="ayah",
    text_col="text",
)

#: Default English translation database configuration (Sahih International)
DATABASE_EN_SAHIH = DatabaseConfig.from_packaged(
    db_name="en_sahih.db",
    tablename="verses",
    surah_col="sura",
    ayah_col="ayah",
    text_col="text",
)

#: Default word-by-word translation database configuration
DATABASE_WBW_EN = WbwDatabaseConfig.from_packaged(
    db_name="wbw_en.db",
    tablename="wbw",
    surah_col="surah",
    ayah_col="ayah",
    text_col="translation",
    word_id_col="word",
)


# === Layout Presets ===

# Landscape (16:9) Presets
LANDSCAPE_PRESET = {
    "default": {
        "720p": (
            LayoutConfig(
                max_width=1280,
                image_height=720,
                padding=(33, 33, 33, 33),
                wimage_y_offset=-100,
                timage_y_offset=-80,
                wimage_vertical_align="center",
                timage_vertical_align="bottom",
            ),
            TextConfig(font_size=24, line_spacing=7, max_width=1280),
            WordConfig(
                font_size=53,
                word_spacing=13,
                row_spacing=20,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
                annotation_font_size=19,
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1920,
                image_height=1080,
                padding=(50, 50, 50, 50),
                wimage_y_offset=-150,
                timage_y_offset=-120,
                wimage_vertical_align="center",
                timage_vertical_align="bottom",
            ),
            TextConfig(font_size=36, line_spacing=10, max_width=1920),
            WordConfig(
                font_size=80,
                word_spacing=20,
                row_spacing=30,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
                annotation_font_size=28,
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=2560,
                image_height=1440,
                padding=(67, 67, 67, 67),
                wimage_y_offset=-200,
                timage_y_offset=-160,
                wimage_vertical_align="center",
                timage_vertical_align="bottom",
            ),
            TextConfig(font_size=48, line_spacing=13, max_width=2560),
            WordConfig(
                font_size=107,
                word_spacing=27,
                row_spacing=40,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
                annotation_font_size=37,
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=3840,
                image_height=2160,
                padding=(100, 100, 100, 100),
                wimage_y_offset=-300,
                timage_y_offset=-240,
                wimage_vertical_align="center",
                timage_vertical_align="bottom",
            ),
            TextConfig(font_size=72, line_spacing=20, max_width=3840),
            WordConfig(
                font_size=160,
                word_spacing=40,
                row_spacing=60,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
                annotation_font_size=56,
            ),
        ),
    },
    "arabic": {
        "720p": (
            LayoutConfig(
                max_width=1280,
                image_height=720,
                padding=(33, 33, 33, 33),
                wimage_vertical_align="center",
                wimage_horizontal_align="center",
            ),
            TextConfig(font_size=24, line_spacing=7, max_width=1280, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=53,
                word_spacing=13,
                row_spacing=7,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 9, 1, 1),
                annotation_font_size=19,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1920,
                image_height=1080,
                padding=(50, 50, 50, 50),
                wimage_vertical_align="center",
                wimage_horizontal_align="center",
            ),
            TextConfig(font_size=36, line_spacing=10, max_width=1920, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=80,
                word_spacing=20,
                row_spacing=10,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 14, 1, 1),
                annotation_font_size=28,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=2560,
                image_height=1440,
                padding=(67, 67, 67, 67),
                wimage_vertical_align="center",
                wimage_horizontal_align="center",
            ),
            TextConfig(font_size=48, line_spacing=13, max_width=2560, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=107,
                word_spacing=27,
                row_spacing=13,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 19, 2, 2),
                annotation_font_size=37,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=3840,
                image_height=2160,
                padding=(100, 100, 100, 100),
                wimage_vertical_align="center",
                wimage_horizontal_align="center",
            ),
            TextConfig(font_size=72, line_spacing=20, max_width=3840, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=160,
                word_spacing=40,
                row_spacing=20,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 28, 2, 2),
                annotation_font_size=56,
                word_padding=(8, 8, 0, 0),
            ),
        ),
    },
    "translation": {
        "720p": (
            LayoutConfig(
                max_width=1280,
                image_height=720,
                padding=(33, 33, 33, 33),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=24, line_spacing=7, max_width=1280),
            WordConfig(
                font_size=53,
                word_spacing=13,
                row_spacing=20,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(1, 27, 1, 1),
                annotation_font_size=19,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1920,
                image_height=1080,
                padding=(50, 50, 50, 50),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=36, line_spacing=10, max_width=1920),
            WordConfig(
                font_size=80,
                word_spacing=20,
                row_spacing=30,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(1, 41, 1, 1),
                annotation_font_size=28,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=2560,
                image_height=1440,
                padding=(67, 67, 67, 67),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=48, line_spacing=13, max_width=2560),
            WordConfig(
                font_size=107,
                word_spacing=27,
                row_spacing=40,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(2, 55, 2, 2),
                annotation_font_size=37,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=3840,
                image_height=2160,
                padding=(100, 100, 100, 100),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=72, line_spacing=20, max_width=3840),
            WordConfig(
                font_size=160,
                word_spacing=40,
                row_spacing=60,
                max_rows_per_page=5,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(2, 82, 2, 2),
                annotation_font_size=56,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
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
                padding=(40, 40, 40, 40),
                timage_y_offset=640 + 160,
                wimage_vertical_align="center",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=24, line_spacing=10, max_width=720),
            WordConfig(
                font_size=53,
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 27, 1, 1),
                annotation_font_size=19,
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1920,
                padding=(60, 60, 60, 60),
                timage_y_offset=960 + 240,
                wimage_vertical_align="center",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=36, line_spacing=15, max_width=1080),
            WordConfig(
                font_size=80,
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=2,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 41, 1, 1),
                annotation_font_size=28,
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=2560,
                padding=(80, 80, 80, 80),
                timage_y_offset=1280 + 320,
                wimage_vertical_align="center",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=48, line_spacing=20, max_width=1440),
            WordConfig(
                font_size=107,
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 55, 2, 2),
                annotation_font_size=37,
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=3840,
                padding=(120, 120, 120, 120),
                timage_y_offset=1920 + 480,
                wimage_vertical_align="center",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=72, line_spacing=30, max_width=2160),
            WordConfig(
                font_size=160,
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 82, 2, 2),
                annotation_font_size=56,
            ),
        ),
    },
    "arabic": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=1280,
                padding=(40, 40, 40, 40),
            ),
            TextConfig(font_size=24, line_spacing=10, max_width=720, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=53,
                word_spacing=15,
                row_spacing=6,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_padding=(1, 9, 1, 1),
                annotation_font_size=19,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1920,
                padding=(60, 60, 60, 60),
            ),
            TextConfig(font_size=36, line_spacing=15, max_width=1080, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=80,
                word_spacing=20,
                row_spacing=10,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(1, 14, 1, 1),
                annotation_font_size=28,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=2560,
                padding=(80, 80, 80, 80),
            ),
            TextConfig(font_size=48, line_spacing=20, max_width=1440, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=107,
                word_spacing=25,
                row_spacing=13,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_padding=(2, 19, 2, 2),
                annotation_font_size=37,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=3840,
                padding=(120, 120, 120, 120),
            ),
            TextConfig(font_size=72, line_spacing=30, max_width=2160, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=160,
                word_spacing=40,
                row_spacing=20,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_padding=(2, 28, 2, 2),
                annotation_font_size=56,
                word_padding=(8, 8, 0, 0),
            ),
        ),
    },
    "translation": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=1280,
                padding=(40, 40, 40, 40),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=24, line_spacing=10, max_width=720),
            WordConfig(
                font_size=53,
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=73,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(1, 27, 1, 1),
                annotation_font_size=19,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1920,
                padding=(60, 60, 60, 60),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=36, line_spacing=15, max_width=1080),
            WordConfig(
                font_size=80,
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(1, 41, 1, 1),
                annotation_font_size=28,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=2560,
                padding=(80, 80, 80, 80),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=48, line_spacing=20, max_width=1440),
            WordConfig(
                font_size=107,
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=147,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(2, 55, 2, 2),
                annotation_font_size=37,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=3840,
                padding=(120, 120, 120, 120),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=72, line_spacing=30, max_width=2160),
            WordConfig(
                font_size=160,
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=8,
                balanced_wrapping=True,
                verse_number_size=220,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(2, 82, 2, 2),
                annotation_font_size=56,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
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
                padding=(40, 40, 40, 40),
                timage_y_offset=360 + 80,
                wimage_y_offset=-360 + 40,
                wimage_vertical_align="bottom",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=19, line_spacing=10, max_width=720 - 80),
            WordConfig(
                font_size=40,
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=55,
                verse_number_padding=(1, 20, 1, 1),
                annotation_font_size=14,
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1080,
                padding=(60, 60, 60, 60),
                timage_y_offset=540 + 120,
                wimage_y_offset=-540 + 60,
                wimage_vertical_align="bottom",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=28, line_spacing=15, max_width=1080 - 120),
            WordConfig(
                font_size=60,
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=83,
                verse_number_padding=(1, 31, 1, 1),
                annotation_font_size=21,
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=1440,
                padding=(80, 80, 80, 80),
                timage_y_offset=720 + 160,
                wimage_y_offset=-720 + 80,
                wimage_vertical_align="bottom",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=37, line_spacing=20, max_width=1440 - 160),
            WordConfig(
                font_size=80,
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(2, 41, 2, 2),
                annotation_font_size=28,
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=2160,
                padding=(120, 120, 120, 120),
                timage_y_offset=1080 + 240,
                wimage_y_offset=-1080 + 120,
                wimage_vertical_align="bottom",
                timage_vertical_align="top",
            ),
            TextConfig(font_size=56, line_spacing=30, max_width=2160 - 240),
            WordConfig(
                font_size=120,
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=165,
                verse_number_padding=(2, 61, 2, 2),
                annotation_font_size=42,
            ),
        ),
    },
    "arabic": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=720,
                padding=(40, 40, 40, 40),
            ),
            TextConfig(font_size=24, line_spacing=10, max_width=720, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=40,
                word_spacing=15,
                row_spacing=6,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=55,
                verse_number_padding=(1, 8, 1, 1),
                annotation_font_size=14,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1080,
                padding=(60, 60, 60, 60),
            ),
            TextConfig(font_size=36, line_spacing=15, max_width=1080, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=60,
                word_spacing=20,
                row_spacing=10,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=83,
                verse_number_padding=(1, 11, 1, 1),
                annotation_font_size=21,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=1440,
                padding=(80, 80, 80, 80),
            ),
            TextConfig(font_size=48, line_spacing=20, max_width=1440, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=80,
                word_spacing=25,
                row_spacing=13,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_padding=(2, 15, 2, 2),
                annotation_font_size=28,
                word_padding=(8, 8, 0, 0),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=2160,
                padding=(120, 120, 120, 120),
            ),
            TextConfig(font_size=72, line_spacing=30, max_width=2160, color=(0, 0, 0, 0)),
            WordConfig(
                font_size=120,
                word_spacing=40,
                row_spacing=20,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=165,
                verse_number_padding=(2, 22, 2, 2),
                annotation_font_size=42,
                word_padding=(8, 8, 0, 0),
            ),
        ),
    },
    "translation": {
        "720p": (
            LayoutConfig(
                max_width=720,
                image_height=720,
                padding=(40, 40, 40, 40),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=24, line_spacing=10, max_width=720 - 80),
            WordConfig(
                font_size=40,
                word_spacing=15,
                row_spacing=25,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=55,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(1, 20, 1, 1),
                annotation_font_size=14,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "1080p": (
            LayoutConfig(
                max_width=1080,
                image_height=1080,
                padding=(60, 60, 60, 60),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=28, line_spacing=15, max_width=1080 - 120),
            WordConfig(
                font_size=60,
                word_spacing=20,
                row_spacing=40,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=83,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(1, 31, 1, 1),
                annotation_font_size=21,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "1440p": (
            LayoutConfig(
                max_width=1440,
                image_height=1440,
                padding=(80, 80, 80, 80),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=37, line_spacing=20, max_width=1440 - 160),
            WordConfig(
                font_size=80,
                word_spacing=25,
                row_spacing=55,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=110,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(2, 41, 2, 2),
                annotation_font_size=28,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
        "2160p": (
            LayoutConfig(
                max_width=2160,
                image_height=2160,
                padding=(120, 120, 120, 120),
                timage_vertical_align="center",
            ),
            TextConfig(font_size=56, line_spacing=30, max_width=2160 - 240),
            WordConfig(
                font_size=120,
                word_spacing=40,
                row_spacing=80,
                max_rows_per_page=3,
                balanced_wrapping=True,
                verse_number_size=165,
                verse_number_color=(0, 0, 0, 0),
                verse_number_padding=(2, 61, 2, 2),
                annotation_font_size=42,
                word_color=(0, 0, 0, 0),
                annotation_color=(0, 0, 0, 0),
            ),
        ),
    },
}
