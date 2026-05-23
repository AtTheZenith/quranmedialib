"""Default presets for fonts, databases, and layout configurations.

This module provides:
- FONT_* constants: Predefined FontResource instances for shipped fonts
- DATABASE_* constants: Predefined DatabaseConfig instances for shipped databases
- build_preset(): Public builder function for custom configs at any resolution
- LANDSCAPE_PRESET, STORY_PRESET, SQUARE_PRESET: Pre-built layout configurations

The builder uses 1080p as the reference resolution. All sizing parameters
(font sizes, spacing, padding, offsets) scale linearly with the canvas height.
Users can call build_preset() directly to generate configs for custom resolutions.
"""

from typing import Final

from quranmedialib.exceptions import ValidationError
from quranmedialib.types import (
    DatabaseConfig,
    FontResource,
    LayoutConfig,
    Padding,
    TextConfig,
    WbwDatabaseConfig,
    WordConfig,
)

# === Common Constants ===
TRANSPARENT: Final[tuple[int, int, int, int]] = (0, 0, 0, 0)
WHITE: Final[tuple[int, int, int, int]] = (255, 255, 255, 255)
ARABIC_WORD_PADDING: Final[tuple[int, int, int, int]] = (8, 8, 0, 0)

# === Font Presets ===
FONT_HAFS: Final = FontResource.from_packaged("hafs.otf", "Hafs")
FONT_INTER: Final = FontResource.from_packaged("inter.ttf", "Inter")
FONT_INTER_ITALIC: Final = FontResource.from_packaged("inter_italic.ttf", "Inter Italic")

# === Database Presets ===
DATABASE_QURAN: Final = DatabaseConfig.from_packaged(
    db_name="quran.db",
    tablename="ayat",
    surah_col="sura",
    ayah_col="ayah",
    text_col="text",
)
DATABASE_EN_SAHIH: Final = DatabaseConfig.from_packaged(
    db_name="english_sahih.db",
    tablename="english_sahih",
    surah_col="sura",
    ayah_col="aya",
    text_col="text",
)
DATABASE_WBW_EN: Final = WbwDatabaseConfig.from_packaged(
    db_name="english_wbw.db",
    tablename="wbw",
    surah_col="surah",
    ayah_col="ayah",
    text_col="translation",
    word_id_col="word",
)

# === Builder Constants (1080p reference values) ===
# These are the base values at 1080p. The builder scales them linearly
# with the canvas height ratio (height / 1080) for any resolution.
# To microadjust: change the _BASE values here — all presets update automatically.

# --- Landscape (16:9) base at 1080p ---
_LANDSCAPE_BASE = {
    "default": {
        "layout": {
            "padding": 50,
            "wimage_y_offset": -150,
            "timage_y_offset": -120,
            "wimage_vertical_align": "center",
            "timage_vertical_align": "bottom",
        },
        "text": {"font_size": 36, "line_spacing": 10, "max_width_subtract": 100},
        "word": {
            "font_size": 80,
            "word_spacing": 20,
            "row_spacing": 30,
            "max_rows_per_page": 2,
            "verse_number_size": 110,
            "verse_number_padding_bottom": 41,
            "annotation_font_size": 28,
        },
    },
    "arabic": {
        "layout": {
            "padding": 50,
            "wimage_vertical_align": "center",
            "wimage_horizontal_align": "center",
        },
        "text": {"font_size": 36, "line_spacing": 10, "color": TRANSPARENT},
        "word": {
            "font_size": 80,
            "word_spacing": 20,
            "row_spacing": 10,
            "max_rows_per_page": 3,
            "verse_number_size": 110,
            "verse_number_padding_bottom": 14,
            "annotation_font_size": 28,
            "word_padding": ARABIC_WORD_PADDING,
        },
    },
    "translation": {
        "layout": {
            "padding": 50,
            "timage_vertical_align": "center",
        },
        "text": {"font_size": 36, "line_spacing": 10, "max_width_subtract": 100},
        "word": {
            "font_size": 80,
            "word_spacing": 20,
            "row_spacing": 30,
            "max_rows_per_page": 5,
            "verse_number_size": 110,
            "verse_number_color": TRANSPARENT,
            "verse_number_padding_bottom": 41,
            "annotation_font_size": 28,
            "word_color": TRANSPARENT,
            "annotation_color": TRANSPARENT,
        },
    },
}

# --- Story/Portrait (9:16) base at 1080p ---
_STORY_BASE = {
    "default": {
        "layout": {
            "padding": 60,
            "timage_y_offset_formula": "height/2 + height/8",  # 960 + 240 = 1200
            "wimage_vertical_align": "center",
            "timage_vertical_align": "top",
        },
        "text": {"font_size": 36, "line_spacing": 15, "max_width_subtract": 120},
        "word": {
            "font_size": 80,
            "word_spacing": 20,
            "row_spacing": 40,
            "max_rows_per_page": 8,
            "verse_number_size": 110,
            "verse_number_padding_bottom": 41,
            "annotation_font_size": 28,
        },
    },
    "arabic": {
        "layout": {
            "padding": 60,
        },
        "text": {"font_size": 36, "line_spacing": 15, "color": TRANSPARENT},
        "word": {
            "font_size": 80,
            "word_spacing": 20,
            "row_spacing": 10,
            "max_rows_per_page": 8,
            "verse_number_size": 110,
            "verse_number_padding_bottom": 14,
            "annotation_font_size": 28,
            "word_padding": ARABIC_WORD_PADDING,
        },
    },
    "translation": {
        "layout": {
            "padding": 60,
            "timage_vertical_align": "center",
        },
        "text": {"font_size": 36, "line_spacing": 15, "max_width_subtract": 120},
        "word": {
            "font_size": 80,
            "word_spacing": 20,
            "row_spacing": 40,
            "max_rows_per_page": 8,
            "verse_number_size": 110,
            "verse_number_color": TRANSPARENT,
            "verse_number_padding_bottom": 41,
            "annotation_font_size": 28,
            "word_color": TRANSPARENT,
            "annotation_color": TRANSPARENT,
        },
    },
}

# --- Square (1:1) base at 1080p ---
_SQUARE_BASE = {
    "default": {
        "layout": {
            "padding": 60,
            "timage_y_offset_formula": "height/2 + height/9",  # 540 + 120 = 660
            "wimage_y_offset_formula": "-height/2 + padding",  # -540 + 60 = -480
            "wimage_vertical_align": "bottom",
            "timage_vertical_align": "top",
        },
        "text": {"font_size": 28, "line_spacing": 15, "max_width_subtract": 120},
        "word": {
            "font_size": 60,
            "word_spacing": 20,
            "row_spacing": 40,
            "max_rows_per_page": 3,
            "verse_number_size": 83,
            "verse_number_padding_bottom": 31,
            "annotation_font_size": 21,
        },
    },
    "arabic": {
        "layout": {
            "padding": 60,
        },
        "text": {"font_size": 36, "line_spacing": 15, "color": TRANSPARENT},
        "word": {
            "font_size": 60,
            "word_spacing": 20,
            "row_spacing": 10,
            "max_rows_per_page": 3,
            "verse_number_size": 83,
            "verse_number_padding_bottom": 11,
            "annotation_font_size": 21,
            "word_padding": ARABIC_WORD_PADDING,
        },
    },
    "translation": {
        "layout": {
            "padding": 60,
            "timage_vertical_align": "center",
        },
        "text": {"font_size": 28, "line_spacing": 15, "max_width_subtract": 120},
        "word": {
            "font_size": 60,
            "word_spacing": 20,
            "row_spacing": 40,
            "max_rows_per_page": 3,
            "verse_number_size": 83,
            "verse_number_color": TRANSPARENT,
            "verse_number_padding_bottom": 31,
            "annotation_font_size": 21,
            "word_color": TRANSPARENT,
            "annotation_color": TRANSPARENT,
        },
    },
}

# === Known Resolutions ===
# Each entry maps resolution name -> (width, height) for each aspect ratio
_RESOLUTIONS: dict[str, dict[str, tuple[int, int]]] = {
    "landscape": {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "1440p": (2560, 1440),
        "2160p": (3840, 2160),
    },
    "story": {
        "720p": (720, 1280),
        "1080p": (1080, 1920),
        "1440p": (1440, 2560),
        "2160p": (2160, 3840),
    },
    "square": {
        "720p": (720, 720),
        "1080p": (1080, 1080),
        "1440p": (1440, 1440),
        "2160p": (2160, 2160),
    },
}

# Reference height for scaling (1080p)
# For landscape: use height (1080). For story: use width (1080). For square: either (1080).
# We normalize all presets to a "reference dimension" of 1080.
_REFERENCE_DIM: Final = 1080


def _get_reference_dimension(aspect_ratio: str, width: int, height: int) -> int:
    """Returns the reference dimension for scaling.

    Landscape: height is the reference (720, 1080, 1440, 2160).
    Story: width is the reference (720, 1080, 1440, 2160).
    Square: width = height, so either works.
    """
    return height if aspect_ratio == "landscape" else width


def _round_scale(base: int | float, ref_dim: int) -> int:
    """Scales a base value linearly with the reference dimension, rounded to nearest int."""
    return round(base * ref_dim / _REFERENCE_DIM)


def build_preset(
    aspect_ratio: str,
    mode: str,
    width: int,
    height: int,
) -> tuple[LayoutConfig, TextConfig, WordConfig]:
    """Builds a complete preset configuration for any resolution.

    Args:
        aspect_ratio: One of "landscape" (16:9), "story" (9:16), or "square" (1:1).
        mode: One of "default", "arabic", or "translation".
        width, height: Canvas dimensions in pixels.

    Returns:
        tuple[LayoutConfig, TextConfig, WordConfig]

    Raises:
        ValidationError: If aspect_ratio or mode is not recognized.
    """
    valid_aspects = ("landscape", "story", "square")
    valid_modes = ("default", "arabic", "translation")

    if aspect_ratio not in valid_aspects:
        raise ValidationError(f"Invalid aspect_ratio: '{aspect_ratio}'. Must be {valid_aspects}.")
    if mode not in valid_modes:
        raise ValidationError(f"Invalid mode: '{mode}'. Must be {valid_modes}.")

    # Select base config
    bases = {"landscape": _LANDSCAPE_BASE, "story": _STORY_BASE, "square": _SQUARE_BASE}
    base = bases[aspect_ratio][mode]

    layout_base = base["layout"]
    text_base = base["text"]
    word_base = base["word"]

    # Determine reference dimension for scaling
    ref_dim = _get_reference_dimension(aspect_ratio, width, height)

    padding_val = _round_scale(layout_base["padding"], ref_dim)

    # Build LayoutConfig
    layout_kwargs: dict = {
        "max_width": width,
        "image_height": height,
        "padding": Padding(padding_val, padding_val, padding_val, padding_val),
    }
    for key in ("wimage_vertical_align", "wimage_horizontal_align", "timage_vertical_align", "timage_horizontal_align"):
        if key in layout_base:
            layout_kwargs[key] = layout_base[key]

    # Handle y-offsets (scaled by ref_dim for fixed offsets, actual height for formulas)
    if "wimage_y_offset" in layout_base:
        layout_kwargs["wimage_y_offset"] = _round_scale(layout_base["wimage_y_offset"], ref_dim)
    elif "wimage_y_offset_formula" in layout_base:
        formula = layout_base["wimage_y_offset_formula"]
        if formula == "-height/2 + padding":
            layout_kwargs["wimage_y_offset"] = -height // 2 + padding_val

    if "timage_y_offset" in layout_base:
        layout_kwargs["timage_y_offset"] = _round_scale(layout_base["timage_y_offset"], ref_dim)
    elif "timage_y_offset_formula" in layout_base:
        formula = layout_base["timage_y_offset_formula"]
        if formula == "height/2 + height/8":
            layout_kwargs["timage_y_offset"] = height // 2 + height // 8
        elif formula == "height/2 + height/9":
            layout_kwargs["timage_y_offset"] = height // 2 + round(height / 9)

    layout_config = LayoutConfig(**layout_kwargs)

    # Build TextConfig
    text_kwargs: dict = {
        "font_size": _round_scale(text_base["font_size"], ref_dim),
        "line_spacing": _round_scale(text_base["line_spacing"], ref_dim),
        "max_width": width - _round_scale(text_base.get("max_width_subtract", 0), ref_dim),
    }
    if "color" in text_base:
        text_kwargs["color"] = text_base["color"]

    text_config = TextConfig(**text_kwargs)

    # Build WordConfig
    vnp_bottom = _round_scale(word_base["verse_number_padding_bottom"], ref_dim)
    vnp_top_side = 1 if ref_dim <= 1080 else 2

    word_kwargs: dict = {
        "font_size": _round_scale(word_base["font_size"], ref_dim),
        "word_spacing": _round_scale(word_base["word_spacing"], ref_dim),
        "row_spacing": _round_scale(word_base["row_spacing"], ref_dim),
        "max_rows_per_page": word_base["max_rows_per_page"],
        "balanced_wrapping": True,
        "verse_number_size": _round_scale(word_base["verse_number_size"], ref_dim),
        "verse_number_padding": Padding(vnp_top_side, vnp_bottom, vnp_top_side, vnp_top_side),
        "annotation_font_size": _round_scale(word_base["annotation_font_size"], ref_dim),
    }
    for key in ("word_padding", "verse_number_color", "word_color", "annotation_color"):
        if key in word_base:
            word_kwargs[key] = word_base[key]

    word_config = WordConfig(**word_kwargs)

    return layout_config, text_config, word_config


def _build_all_presets() -> dict:
    """Generates the full preset dictionary from base constants."""
    result: dict = {"landscape": {}, "story": {}, "square": {}}
    for aspect in ("landscape", "story", "square"):
        for mode in ("default", "arabic", "translation"):
            result[aspect][mode] = {}
            for res_name, (w, h) in _RESOLUTIONS[aspect].items():
                result[aspect][mode][res_name] = build_preset(aspect, mode, w, h)
    return result


_ALL_PRESETS = _build_all_presets()

# === Public Preset Dictionaries ===
#: Landscape (16:9) presets: PRESET["mode"]["resolution"] -> (LayoutConfig, TextConfig, WordConfig)
LANDSCAPE_PRESET: Final = _ALL_PRESETS["landscape"]

#: Story/Portrait (9:16) presets: PRESET["mode"]["resolution"] -> (LayoutConfig, TextConfig, WordConfig)
STORY_PRESET: Final = _ALL_PRESETS["story"]

#: Square (1:1) presets: PRESET["mode"]["resolution"] -> (LayoutConfig, TextConfig, WordConfig)
SQUARE_PRESET: Final = _ALL_PRESETS["square"]
