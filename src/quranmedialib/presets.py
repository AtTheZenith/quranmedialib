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
    ResolvedRect,
    TextConfig,
    UDim2,
    VerseConfig,
    VerticalAlignment,
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
        size=UDim2(1.0, -100, 1.0, 0),
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
        position=UDim2(0.5, 0, 0.85, -8),
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


# Per-(aspect, mode) overrides. Values match v3.0.0. Only fields that differ from
# the mode defaults are listed (minimal overrides). Word font sizes for square are
# common to all three square modes in v3.
_ASPECT_OVERRIDES: dict[str, dict[str, dict[str, dict]]] = {
    "story": {
        "default": {
            "text": {"line_spacing": 15},
            "verse": {"row_spacing": 40, "max_rows_per_page": 8},
        },
        "arabic": {
            "text": {"line_spacing": 15},
            "verse": {"max_rows_per_page": 8},
        },
        "translation": {
            "text": {"line_spacing": 15},
            "verse": {"row_spacing": 40, "max_rows_per_page": 8},
        },
    },
    "square": {
        "default": {
            "word": {
                "font_size": 60,
                "verse_number_size": 83,
                "verse_number_padding": Padding(1, 31, 1, 1),
                "annotation_font_size": 21,
            },
            "text": {"font_size": 28, "line_spacing": 15},
            "verse": {"row_spacing": 40, "max_rows_per_page": 3},
        },
        "arabic": {
            "word": {
                "font_size": 60,
                "verse_number_size": 83,
                "verse_number_padding": Padding(1, 11, 1, 1),
                "annotation_font_size": 21,
            },
            "text": {"line_spacing": 15},
        },
        "translation": {
            "word": {
                "font_size": 60,
                "verse_number_size": 83,
                "verse_number_padding": Padding(1, 31, 1, 1),
                "annotation_font_size": 21,
            },
            "text": {"font_size": 28, "line_spacing": 15},
            "verse": {"row_spacing": 40, "max_rows_per_page": 3},
        },
    },
}

# Text max_width margin at 1080p reference, per aspect ratio (v3 values).
_MAX_WIDTH_SUBTRACT: Final[dict[str, int]] = {"landscape": 100, "story": 120, "square": 120}


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

    # Determine reference dimension for resolution scaling (matches v3)
    ref_dim = height if aspect_ratio == "landscape" else width

    def _scale(val: int | float) -> int:
        return round(val * ref_dim / 1080)

    # Get mode overrides
    mode_cfg = _MODE_OVERRIDES[mode]
    aspect_cfg = _ASPECT_OVERRIDES.get(aspect_ratio, {}).get(mode, {})

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
    # Scale resolution-dependent word fields
    for k in ("font_size", "word_spacing", "verse_number_size", "annotation_font_size"):
        if k in word_kwargs:
            word_kwargs[k] = _scale(word_kwargs[k])
    # Scale verse_number_padding bottom value
    if "verse_number_padding" in word_kwargs:
        vnp = word_kwargs["verse_number_padding"]
        word_kwargs["verse_number_padding"] = Padding(vnp.top, _scale(vnp.bottom), vnp.left, vnp.right)
    word_config = WordConfig(**word_kwargs)

    # Text config
    text_defaults = {
        "max_width": width - _scale(_MAX_WIDTH_SUBTRACT[aspect_ratio]),
        "balanced_wrapping": True,
    }
    text_kwargs = _merge(text_defaults, mode_cfg.get("text", {}), aspect_cfg.get("text", {}))
    # Scale resolution-dependent text fields
    for k in ("font_size", "line_spacing"):
        if k in text_kwargs:
            text_kwargs[k] = _scale(text_kwargs[k])
    text_config = TextConfig(**text_kwargs)

    # Verse config
    verse_defaults = {
        "word_spacing": 10,
        "row_spacing": 20,
        "max_rows_per_page": 3,
        "balanced_wrapping": True,
    }
    verse_kwargs = _merge(verse_defaults, mode_cfg.get("verse", {}), aspect_cfg.get("verse", {}))
    # Scale resolution-dependent verse fields
    for k in ("word_spacing", "row_spacing"):
        if k in verse_kwargs:
            verse_kwargs[k] = _scale(verse_kwargs[k])
    verse_config = VerseConfig(**verse_kwargs)

    frame_config = FrameConfig(
        background_color=TRANSPARENT,
        max_width=width,
        image_height=height,
        aspect_ratio=aspect_ratio,
        mode=mode,
    )

    return Preset(
        frame=frame_config,
        word=word_config,
        verse=verse_config,
        text=text_config,
    )


def _v3_content_width(aspect_ratio: str, frame_width: int, frame_height: int) -> int:
    """Compute v3-compatible content width accounting for resolution-scaled padding.

    v3 padding = round(base_padding * ref_dim / 1080), content_width = width - 2 * padding.
    Base padding: landscape=50, story=60, square=60.
    """
    base_padding = {"landscape": 50, "story": 60, "square": 60}.get(aspect_ratio, 50)
    ref_dim = frame_height if aspect_ratio == "landscape" else frame_width
    padding = round(base_padding * ref_dim / 1080)
    return frame_width - 2 * padding


def _v3_arabic_padding(aspect_ratio: str, frame_width: int, frame_height: int) -> int:
    """Compute v3-compatible padding for a given aspect ratio and frame dimensions.

    Landscape scales by height (1080 at 1080p); story and square scale by width.

    Args:
        aspect_ratio: One of "landscape", "story", or "square".
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.

    Returns:
        Scaled padding value in pixels.
    """
    base = {"landscape": 50, "story": 60, "square": 60}.get(aspect_ratio, 50)
    ref_dim = frame_height if aspect_ratio == "landscape" else frame_width
    return round(base * ref_dim / 1080)


def build_layout_guide(
    aspect_ratio: str,
    frame_width: int,
    frame_height: int,
    mode: str = "default",
) -> LayoutGuide:
    """Build a resolved LayoutGuide matching v3's per-aspect, per-mode placement.

    The arabic rect is the box the VImage content is centred within; the
    translation rect is where translation images are placed. v3's per-mode
    wimage/timage y-offsets are folded into the rect top so that the layer_at
    centring/bottom-anchoring reproduces v3's Frame.layer math exactly.

    Args:
        aspect_ratio: One of "landscape", "story", or "square".
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.
        mode: One of "default", "arabic", or "translation".

    Returns:
        LayoutGuide with resolved pixel rects for arabic and translation areas.
    """
    engine = LayoutEngine(frame_width, frame_height)
    padding = _v3_arabic_padding(aspect_ratio, frame_width, frame_height)
    content_width = frame_width - 2 * padding
    available_height = frame_height - 2 * padding

    arabic = _resolve_arabic_rect(
        aspect_ratio, mode, engine, frame_width, frame_height, padding, content_width, available_height
    )
    translation = _resolve_translation_rect(
        aspect_ratio, mode, engine, frame_height, padding, content_width, available_height
    )
    return LayoutGuide(arabic=arabic, translation=translation)


def translation_placement(
    rect: ResolvedRect,
    image_width: int,
    image_height: int,
    aspect_ratio: str,
    mode: str,
) -> tuple[ResolvedRect, bool]:
    """Return the paste rect and keep_bottom flag for a translation image.

    Reproduces v3's per-mode timage anchoring: landscape/default is
    bottom-anchored (keep_bottom), story/square default is top-anchored, and
    translation mode is vertically centred within the rect. Arabic mode has no
    visible translation, so the centred placement is used harmlessly.

    Args:
        rect: The resolved translation rect from the layout guide.
        image_width: Translation image width in pixels.
        image_height: Translation image height in pixels.
        aspect_ratio: One of "landscape", "story", or "square".
        mode: One of "default", "arabic", or "translation".

    Returns:
        Tuple of the paste rect and whether to keep the image bottom-anchored.
    """
    if mode == "default" and aspect_ratio == "landscape":
        return rect, True
    x = rect.left + (rect.width - image_width) // 2
    y = rect.top if mode == "default" else rect.top + (rect.height - image_height) // 2
    return ResolvedRect(x, y, image_width, image_height), False


def arabic_vertical_alignment(aspect_ratio: str, mode: str) -> VerticalAlignment:
    """Return the vertical alignment for the arabic content block.

    v3 bottom-anchors arabic content only for square/default mode; all
    other combos are vertically centred.

    Args:
        aspect_ratio: One of "landscape", "story", or "square".
        mode: One of "default", "arabic", or "translation".

    Returns:
        VerticalAlignment.BOTTOM for square/default, else VerticalAlignment.CENTER.
    """
    if aspect_ratio == "square" and mode == "default":
        return VerticalAlignment.BOTTOM
    return VerticalAlignment.CENTER


def _resolve_arabic_rect(
    aspect_ratio: str,
    mode: str,
    engine: LayoutEngine,
    frame_width: int,
    frame_height: int,
    padding: int,
    content_width: int,
    available_height: int,
) -> ResolvedRect:
    """Resolve the arabic content rect for a given aspect and mode.

    v3 wimage placement is always horizontally centred. The vertical offset is
    baked into the rect top so that layer_at centring lands the content where
    v3's Frame.layer math puts it.

    Args:
        aspect_ratio: One of "landscape", "story", or "square".
        mode: One of "default", "arabic", or "translation".
        engine: LayoutEngine for the frame dimensions.
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.
        padding: Scaled v3 padding value.
        content_width: Frame width minus horizontal padding.
        available_height: Frame height minus vertical padding.

    Returns:
        ResolvedRect for the arabic content area.
    """
    if aspect_ratio == "landscape" and mode == "default":
        # Landscape default keeps the UDim2 layout (bakes the -150 offset);
        # only the width needs the v3 per-resolution override.
        arabic = engine.resolve_rect(_ARABIC_LAYOUT["landscape"])
        return ResolvedRect(
            arabic.left,
            arabic.top,
            _v3_content_width(aspect_ratio, frame_width, frame_height),
            arabic.height,
        )
    if aspect_ratio == "square" and mode == "default":
        # Square default bottom-anchors the content (-height/2 + padding).
        offset = -frame_height // 2 + padding
        return ResolvedRect(padding, padding + offset, content_width, available_height)
    # Story (all modes) and non-default modes are centred with no vertical offset.
    return ResolvedRect(padding, padding, content_width, available_height)


def _resolve_translation_rect(
    aspect_ratio: str,
    mode: str,
    engine: LayoutEngine,
    frame_height: int,
    padding: int,
    content_width: int,
    available_height: int,
) -> ResolvedRect:
    """Resolve the translation rect for a given aspect and mode.

    Args:
        aspect_ratio: One of "landscape", "story", or "square".
        mode: One of "default", "arabic", or "translation".
        engine: LayoutEngine for the frame dimensions.
        frame_height: Frame height in pixels.
        padding: Scaled v3 padding value.
        content_width: Frame width minus horizontal padding.
        available_height: Frame height minus vertical padding.

    Returns:
        ResolvedRect for the translation area.
    """
    if mode == "default":
        if aspect_ratio == "landscape":
            # Landscape default is bottom-anchored (-120 offset); keep the
            # UDim2 layout which is already verified to match v3.
            return engine.resolve_rect(_TRANSLATION_LAYOUT["landscape"])
        if aspect_ratio == "story":
            offset = round(frame_height // 2 + frame_height // 8)
            return ResolvedRect(padding, padding + offset, content_width, available_height)
        # Square default: height/2 + height/9.
        offset = round(frame_height // 2 + frame_height // 9)
        return ResolvedRect(padding, padding + offset, content_width, available_height)
    # Arabic and translation modes: translation is either unused or centred.
    return ResolvedRect(padding, padding, content_width, available_height)


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
