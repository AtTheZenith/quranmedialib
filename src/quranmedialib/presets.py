"""Default presets for fonts, databases, and layout configurations.

This module provides:
- FONT_* constants: Predefined FontResource instances for shipped fonts
- DATABASE_* constants: Predefined DatabaseConfig instances for shipped databases
- build_preset(): Public builder function for any resolution
- LANDSCAPE_PRESET, STORY_PRESET, SQUARE_PRESET: Pre-built layout dictionaries

All layout definitions use UDim2 + AnchorPoint for resolution independence.
"""

from typing import Final

from quranmedialib.exceptions import ValidationError
from quranmedialib.modules.layout_engine import LayoutEngine, LayoutGuide
from quranmedialib.types import (
    AnchorPoint,
    DatabaseConfig,
    FontResource,
    FrameConfig,
    Padding,
    Preset,
    PresetLayout,
    TextConfig,
    UDim2,
    VerseConfig,
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


# === UDim2 Layout Definitions ===
# These are resolution-independent. One definition works at 720p, 1080p, 2160p.

_ARABIC_LAYOUT: dict[str, PresetLayout] = {
    "landscape": PresetLayout(
        position=UDim2(0.5, 0, 0.5, -150),
        size=UDim2(0.92, 0, 0.5, 0),
        anchor=AnchorPoint(0.5, 0.5),
    ),
    "story": PresetLayout(
        position=UDim2(0.5, 0, 0.5, 0),
        size=UDim2(0.85, 0, 0.4, 0),
        anchor=AnchorPoint(0.5, 0.5),
    ),
    "square": PresetLayout(
        position=UDim2(0.5, 0, 0.5, -100),
        size=UDim2(0.85, 0, 0.4, 0),
        anchor=AnchorPoint(0.5, 0.5),
    ),
}

_TRANSLATION_LAYOUT: dict[str, PresetLayout] = {
    "landscape": PresetLayout(
        position=UDim2(0.5, 0, 0.85, -120),
        size=UDim2(0.92, -100, 0.2, 0),
        anchor=AnchorPoint(0.5, 1.0),
    ),
    "story": PresetLayout(
        position=UDim2(0.5, 0, 0.85, 0),
        size=UDim2(0.85, -120, 0.25, 0),
        anchor=AnchorPoint(0.5, 1.0),
    ),
    "square": PresetLayout(
        position=UDim2(0.5, 0, 0.85, 0),
        size=UDim2(0.85, -120, 0.25, 0),
        anchor=AnchorPoint(0.5, 1.0),
    ),
}

# Known resolutions for preset dictionary generation
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


# === Mode-specific overrides ===
# These override specific fields per mode.

_MODE_OVERRIDES: dict[str, dict[str, dict]] = {
    "default": {
        "word": {
            "font_size": 80,
            "verse_number_size": 110,
            "verse_number_padding": Padding(1, 41, 1, 1),
            "annotation_font_size": 28,
        },
        "text": {
            "font_size": 36,
            "line_spacing": 10,
        },
        "verse": {
            "word_spacing": 20,
            "row_spacing": 30,
            "max_rows_per_page": 2,
        },
    },
    "arabic": {
        "word": {
            "font_size": 80,
            "word_padding": ARABIC_WORD_PADDING,
            "verse_number_size": 110,
            "verse_number_padding": Padding(1, 14, 1, 1),
            "annotation_font_size": 28,
        },
        "text": {
            "font_size": 36,
            "line_spacing": 10,
            "color": TRANSPARENT,
        },
        "verse": {
            "word_spacing": 20,
            "row_spacing": 10,
            "max_rows_per_page": 3,
        },
    },
    "translation": {
        "word": {
            "font_size": 80,
            "verse_number_size": 110,
            "verse_number_padding": Padding(1, 41, 1, 1),
            "verse_number_color": TRANSPARENT,
            "annotation_font_size": 28,
            "word_color": TRANSPARENT,
            "annotation_color": TRANSPARENT,
            "word_padding": Padding(8, 8, 0, 0),
        },
        "text": {
            "font_size": 36,
            "line_spacing": 10,
        },
        "verse": {
            "word_spacing": 20,
            "row_spacing": 30,
            "max_rows_per_page": 5,
        },
    },
}


_ASPECT_OVERRIDES: dict[str, dict[str, dict]] = {
    "square": {
        "word": {
            "font_size": 60,
            "verse_number_size": 83,
            "annotation_font_size": 21,
        },
        "text": {
            "font_size": 28,
            "line_spacing": 15,
        },
    },
}


def build_preset(
    aspect_ratio: str,
    mode: str,
    width: int,
    height: int,
) -> Preset:
    """Builds a complete preset configuration for any resolution.

    Args:
        aspect_ratio: One of "landscape" (16:9), "story" (9:16), or "square" (1:1).
        mode: One of "default", "arabic", or "translation".
        width, height: Canvas dimensions in pixels.

    Returns:
        Preset: Unified configuration for rendering.

    Raises:
        ValidationError: If aspect_ratio or mode is not recognized.
    """
    valid_aspects = ("landscape", "story", "square")
    valid_modes = ("default", "arabic", "translation")

    if aspect_ratio not in valid_aspects:
        raise ValidationError(f"Invalid aspect_ratio: '{aspect_ratio}'. Must be {valid_aspects}.")
    if mode not in valid_modes:
        raise ValidationError(f"Invalid mode: '{mode}'. Must be {valid_modes}.")

    # Get mode overrides
    mode_cfg = _MODE_OVERRIDES[mode]
    aspect_cfg = _ASPECT_OVERRIDES.get(aspect_ratio, {})

    # Helper to merge overrides
    def _merge(base: dict, mode_ov: dict, aspect_ov: dict) -> dict:
        result = dict(base)
        result.update(mode_ov)
        result.update(aspect_ov)
        return result

    # Word config
    word_defaults = {
        "word_spacing": 10,
        "row_spacing": 20,
        "max_rows_per_page": 3,
        "balanced_wrapping": False,
        "word_color": WHITE,
        "annotation_color": WHITE,
        "background_color": TRANSPARENT,
    }
    word_kwargs = _merge(word_defaults, mode_cfg.get("word", {}), aspect_cfg.get("word", {}))
    word_config = WordConfig(**word_kwargs)

    # Text config
    text_defaults = {
        "max_width": width - 100,
        "balanced_wrapping": True,
    }
    text_kwargs = _merge(text_defaults, mode_cfg.get("text", {}), aspect_cfg.get("text", {}))
    text_config = TextConfig(**text_kwargs)

    # Verse config
    verse_defaults = {
        "word_spacing": 10,
        "row_spacing": 20,
        "max_rows_per_page": 3,
        "balanced_wrapping": True,
    }
    verse_kwargs = _merge(verse_defaults, mode_cfg.get("verse", {}), aspect_cfg.get("verse", {}))
    verse_config = VerseConfig(**verse_kwargs)

    frame_config = FrameConfig(
        background_color=TRANSPARENT,
        max_width=width,
        image_height=height,
        aspect_ratio=aspect_ratio,
    )

    return Preset(
        frame=frame_config,
        word=word_config,
        verse=verse_config,
        text=text_config,
    )


def build_layout_guide(aspect_ratio: str, canvas_width: int, canvas_height: int) -> LayoutGuide:
    """Build a resolved LayoutGuide from the preset layout definitions.

    Args:
        aspect_ratio: One of "landscape", "story", "square".
        canvas_width: Canvas width in pixels.
        canvas_height: Canvas height in pixels.

    Returns:
        LayoutGuide with resolved pixel rects for arabic and translation areas.
    """
    engine = LayoutEngine(canvas_width, canvas_height)
    return LayoutGuide(
        arabic=engine.resolve_rect(_ARABIC_LAYOUT[aspect_ratio]),
        translation=engine.resolve_rect(_TRANSLATION_LAYOUT[aspect_ratio]),
    )


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
#: Landscape (16:9) presets: PRESET["mode"]["resolution"] -> Preset
LANDSCAPE_PRESET: Final = _ALL_PRESETS["landscape"]

#: Story/Portrait (9:16) presets: PRESET["mode"]["resolution"] -> Preset
STORY_PRESET: Final = _ALL_PRESETS["story"]

#: Square (1:1) presets: PRESET["mode"]["resolution"] -> Preset
SQUARE_PRESET: Final = _ALL_PRESETS["square"]
