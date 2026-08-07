"""
Tests for the timage module.
"""

import hashlib
import os

import pytest
from PIL import Image, ImageDraw, ImageOps

from quranmedialib import LANDSCAPE_PRESET
from quranmedialib.modules.text_layout import wrap_rich_text_balanced
from quranmedialib.modules.timage import (
    _parse_rich_text,
    format_isolation_text,
    get_timage,
    normalize_highlight_style,
    prepare_translation_segments,
)
from quranmedialib.types import TextConfig, get_font_path


def _verify_pyramid(text: str, max_width: int, filename: str | None = None):
    """Helper to verify that a given text wraps into an inverted pyramid at max_width."""
    config = TextConfig(max_width=max_width)
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    styled_words = _parse_rich_text(text, config, draw)

    lines = wrap_rich_text_balanced(styled_words, config.max_width)
    widths = [line.width for line in lines]

    assert len(lines) > 0, "Expected at least one line."
    for i in range(len(widths) - 1):
        assert widths[i] >= widths[i + 1], (
            f"Pyramid violation at line {i}: {widths[i]} is not >= {widths[i + 1]} in width sequence {widths}"
        )

    # Save image for human review if a filename is provided
    if filename:
        output_dir = "./output/test/timage/pyramid"
        os.makedirs(output_dir, exist_ok=True)
        if img := get_timage(text, config):
            # Add a border to visualize the max_width
            img_with_border = ImageOps.expand(img, border=2, fill="gray")
            img_with_border.save(f"{output_dir}/{filename}.png")

    return widths


def test_timage_rendering():
    """Verifies that various rich text formats render correctly to images."""
    output_dir = "./output/test/timage"
    os.makedirs(output_dir, exist_ok=True)

    text_config = LANDSCAPE_PRESET["default"]["1080p"].text

    test_cases = [
        ("plain", "Hello World!"),
        ("bold_red", "#b#ff0000ff#Bold Red Text#"),
        ("italic_green", "#i#00ff00ff#Italic Green Text#"),
        ("bold_italic_blue", "#b#0000ffff#Bold Italic Blue Text#"),
        ("center_vertical", "#b#ffffffff#Centered in 400px height#"),
    ]

    for filename, text in test_cases:
        max_height = 400 if filename == "center_vertical" else None
        img = get_timage(text, text_config, max_height=max_height)
        assert img is not None

        img = ImageOps.expand(img, border=2, fill="white")

        img.save(f"{output_dir}/{filename}.png")


@pytest.mark.parametrize(
    "name, text, max_width",
    [
        ("short", "This is a short text that will form a pyramid.", 400),
        (
            "lorem",
            (
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut "
                "labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco "
                "laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in "
                "voluptate velit esse cillum dolore eu fugiat nulla pariatur."
            ),
            1200,
        ),
        ("single", "Short", 400),
        ("long_word", "A very very long single word that might break things", 300),
    ],
    ids=["short", "lorem", "single", "long_word"],
)
def test_timage_pyramid(name: str, text: str, max_width: int) -> None:
    """
    Tests the 'Descending Line Balancing' logic across different scales.
    """
    widths = _verify_pyramid(text, max_width, filename=name)
    if len(widths) > 1:
        print(f"Pyramid widths for '{name}' (max_width={max_width}): {widths}")


if __name__ == "__main__":
    # Allow running manually
    test_timage_rendering()
    _verify_pyramid("This is a short text that will form a pyramid.", 300, filename="manual")


# === Validation Tests ===


def test_timage_empty_text() -> None:
    """Test that get_timage returns None for empty text."""
    result = get_timage("", TextConfig())
    assert result is None


def test_timage_none_text() -> None:
    """Test that get_timage returns None for None text."""
    result = get_timage(None, TextConfig())  # type: ignore
    assert result is None


def test_timage_none_config() -> None:
    """Test that get_timage handles None config by using defaults."""
    # get_timage creates a default TextConfig when config is None
    result = get_timage("test", None)  # type: ignore
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


def test_timage_negative_max_height() -> None:
    """Test that get_timage raises error for negative max_height."""
    config = TextConfig()
    # Negative max_height causes PIL to reject the canvas dimensions
    with pytest.raises(ValueError, match="Width and height must be >= 0"):
        get_timage("test", config, max_height=-100)


def test_timage_invalid_rich_text_format() -> None:
    """Test that get_timage handles malformed rich text."""
    config = TextConfig()

    # Malformed tags (missing closing tag)
    result = get_timage("#b#unclosed bold text", config)
    assert result is not None  # Should handle gracefully

    # Invalid hex color
    result = get_timage("#invalidhex#text", config)
    assert result is not None  # Should handle gracefully


@pytest.mark.benchmark
def test_timage_very_long_text() -> None:
    """Test that get_timage handles long text without crashing.

    Inputs above the pyramid word cap must fall back to greedy wrapping
    (bounded) instead of entering the balanced search, while staying within the
    character/word input limits enforced for untrusted text.
    """
    config = TextConfig(max_width=1200)
    sentence = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore "
        "et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut "
        "aliquip ex ea commodo consequat."
    )
    very_long_text = sentence * 8

    assert len(very_long_text) < 10_000, "must stay under the character limit"
    result = get_timage(very_long_text, config)
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


def test_timage_balanced_pyramid_within_word_cap() -> None:
    """Test that a realistic number of words still gets balanced wrapping."""
    config = TextConfig(max_width=1200)
    text = (
        "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium "
        "doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore "
        "veritatis et quasi architecto beatae vitae dicta sunt explicabo."
    ) * 4  # ~100 words, within the 256-word pyramid cap

    result = get_timage(text, config)
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


# === Format Isolation Text Bounds Tests ===


def test_format_isolation_text_negative_target_index() -> None:
    """Test that format_isolation_text raises ValueError for negative target_index."""
    from quranmedialib.modules.timage import format_isolation_text, prepare_translation_segments

    segments = prepare_translation_segments(["text1", "text2"])

    with pytest.raises(ValueError, match="target_index must be non-negative"):
        format_isolation_text(segments, target_index=-1, highlight_style="#b#FF0000#")


def test_format_isolation_text_out_of_bounds_target_index() -> None:
    """Test that format_isolation_text raises ValueError for out-of-bounds target_index."""
    from quranmedialib.modules.timage import format_isolation_text, prepare_translation_segments

    segments = prepare_translation_segments(["text1", "text2", "text3"])

    with pytest.raises(ValueError, match="target_index.*out of bounds"):
        format_isolation_text(segments, target_index=10, highlight_style="#b#FF0000#")


def test_format_isolation_text_valid_target_index() -> None:
    """Test that format_isolation_text works correctly for valid target_index."""
    from quranmedialib.modules.timage import format_isolation_text, prepare_translation_segments

    segments = prepare_translation_segments(["text1", "text2", "text3"])

    result = format_isolation_text(segments, target_index=1, highlight_style="#b#FF0000#")
    assert result is not None
    assert isinstance(result, str)


# === timage Config Edge Cases (Round 2) ===


def test_timage_negative_line_spacing() -> None:
    """Test that get_timage handles negative line_spacing."""
    config = TextConfig(line_spacing=-10, max_width=500)
    result = get_timage("test text with negative spacing", config)
    # Should produce a valid image (negative spacing may overlap lines)
    assert result is not None
    assert result.size[0] > 0
    assert result.size[1] > 0


def test_normalize_highlight_style_none_input() -> None:
    """Test normalize_highlight_style with None input."""

    result = normalize_highlight_style(None)  # type: ignore
    # Should return a default style string
    assert isinstance(result, str)
    assert len(result) > 0


def test_prepare_translation_segments_none_input() -> None:
    """Test prepare_translation_segments with None input."""
    result = prepare_translation_segments(None)  # type: ignore
    # Should return empty list or handle gracefully
    assert isinstance(result, list)


def test_timage_empty_styled_words() -> None:
    """Test that get_timage returns None for text that produces no styled words."""
    config = TextConfig(max_width=500)
    # Text with only whitespace should produce no styled words
    result = get_timage("   \t\n   ", config)
    assert result is None


def test_timage_very_large_font_size() -> None:
    """Test that TextConfig raises ValueError for font_size exceeding MAX_FONT_SIZE."""
    from quranmedialib.types import MAX_FONT_SIZE

    # Font size exceeding MAX_FONT_SIZE should raise ValueError during config creation
    with pytest.raises(ValueError, match="font_size exceeds maximum limit"):
        TextConfig(font_size=MAX_FONT_SIZE + 1, max_width=500)


def _assert_format_isolation_text_target_index_bounds(segments, target_index):
    # Index 0
    result_0 = format_isolation_text(segments, target_index=target_index, highlight_style="#b#FF0000#")
    assert result_0 is not None
    assert "#b#" in result_0  # Should contain highlight


def test_format_isolation_text_target_index_bounds() -> None:
    """Test format_isolation_text with index exactly 0 and len-1."""
    segments = prepare_translation_segments(["first", "second", "third"])

    _assert_format_isolation_text_target_index_bounds(segments, 0)
    _assert_format_isolation_text_target_index_bounds(segments, 2)


def test_timage_single_word_no_wrapping() -> None:
    """Test that get_timage with a single word produces one line."""
    config = TextConfig(max_width=500)
    result = get_timage("singleword", config)
    assert result is not None
    assert result.size[1] > 0


def test_timage_none_max_width() -> None:
    """Test that get_timage works when config.max_width is None."""
    config = TextConfig()  # default max_width is None
    result = get_timage("test text with no max width", config)
    assert result is not None
    assert result.size[0] > 0


# === Rich Text Parsing: Return-Value Tests ===


def _parse(text: str, config: TextConfig | None = None):
    """Parse rich text into StyledWords using a throwaway draw surface."""
    cfg = config or TextConfig(font_size=36, max_width=500)
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    return _parse_rich_text(text, cfg, draw)


def test_parse_plain_text_default_styling() -> None:
    """Plain text yields one StyledWord per token with default color and no bold."""
    cfg = TextConfig(font_size=36, max_width=500)
    words = _parse("Hello world", cfg)

    assert [w.text for w in words] == ["Hello", " ", "world"]
    assert all(w.color == cfg.color for w in words)
    assert all(not w.simulate_bold for w in words)
    assert all(str(w.font.path) == str(cfg.font_path) for w in words)


def test_parse_bold_tag_sets_simulate_bold() -> None:
    """A #b# tag must produce words flagged for bold simulation with the tag color."""
    cfg = TextConfig(font_size=36, max_width=500)
    words = _parse("#b#ff0000ff#Bold#", cfg)

    assert len(words) == 1
    assert words[0].text == "Bold"
    assert words[0].simulate_bold is True
    assert words[0].color == (255, 0, 0, 255)


def test_parse_italic_tag_uses_italic_font() -> None:
    """An #i# tag must use the configured italic font and tag color."""
    cfg = TextConfig(font_size=36, max_width=500)
    words = _parse("#i#00ff00ff#Italic#", cfg)

    assert len(words) == 1
    assert words[0].text == "Italic"
    assert words[0].simulate_bold is False
    assert words[0].color == (0, 255, 0, 255)
    assert str(words[0].font.path) == str(cfg.italic_font_path)


def test_parse_italic_respects_custom_italic_font_path() -> None:
    """Italic styling must honor config.italic_font_path, not a hardcoded naming rule."""
    cfg = TextConfig(font_size=36, max_width=500, italic_font_path=str(get_font_path("inter.ttf")))
    words = _parse("#i#00ff00ff#Italic#", cfg)

    assert str(words[0].font.path) == str(cfg.italic_font_path)


def test_parse_combined_bold_italic_tag() -> None:
    """A #bi# tag must apply italic font plus bold simulation with the tag color."""
    cfg = TextConfig(font_size=36, max_width=500)
    words = _parse("#bi#0000ffff#Bold Italic#", cfg)

    assert [w.text for w in words] == ["Bold", " ", "Italic"]
    assert all(w.simulate_bold for w in words)
    assert all(w.color == (0, 0, 255, 255) for w in words)
    assert all(str(w.font.path) == str(cfg.italic_font_path) for w in words)


def test_parse_six_digit_hex_color() -> None:
    """A 24-bit (6-digit) color must be accepted and rendered fully opaque."""
    cfg = TextConfig(font_size=36, max_width=500)
    words = _parse("#b#ff0000#Red#", cfg)

    assert len(words) == 1
    assert words[0].text == "Red"
    assert words[0].simulate_bold is True
    assert words[0].color == (255, 0, 0, 255)


def test_parse_mandatory_closing_tag_enforced() -> None:
    """An unclosed tag must not be treated as a rich text tag."""
    words = _parse("plain #b#ff0000ff#unclosed", TextConfig(font_size=36, max_width=500))

    assert all(not w.simulate_bold for w in words)
    assert "#b#ff0000ff#unclosed" in "".join(w.text for w in words)


def test_format_isolation_text_emits_modern_tags() -> None:
    """Isolation output must use the modern grammar: one independent tag per word."""
    segments = prepare_translation_segments(["word1", "word2", "word3"])
    result = format_isolation_text(segments, target_index=1, highlight_style="#b#FF0000#")

    assert result == "#b#00000000#word1# #b#FF0000#word2# #b#00000000#word3#"

    # The emitted string must round-trip through the parser as separate words.
    words = _parse(result)
    assert [w.text for w in words] == ["word1", " ", "word2", " ", "word3"]
    assert words[0].color == (0, 0, 0, 0)  # transparent placeholder
    assert words[2].color == (255, 0, 0, 255)  # highlighted target
    assert words[2].simulate_bold is True


def test_normalize_highlight_style_preserves_explicit_color() -> None:
    """An explicit 6- or 8-digit color in the highlight style must be preserved."""
    assert normalize_highlight_style("#b#FF0000#") == "#b#FF0000#"
    assert normalize_highlight_style("#b#ff0000ff#") == "#b#ff0000ff#"
    assert normalize_highlight_style("#i#00ff00#") == "#i#00ff00#"


def test_normalize_highlight_style_defaults_to_gold() -> None:
    """Bare or missing styles must resolve to a full modern tag with the default gold color."""
    assert normalize_highlight_style(None) == "#b#ffd700ff#"
    assert normalize_highlight_style("#b#") == "#b#ffd700ff#"
    assert normalize_highlight_style("#bi#") == "#bi#ffd700ff#"


def test_draw_combined_bold_italic_differs_from_plain() -> None:
    """Bold-italic text must render distinct from plain and from bold alone."""
    cfg = TextConfig(font_size=36, max_width=500)
    bi_img = get_timage("#bi#ffffffff#Bold Italic#", cfg)
    plain_img = get_timage("Bold Italic", cfg)
    bold_img = get_timage("#b#ffffffff#Bold Italic#", cfg)

    assert bi_img is not None and plain_img is not None and bold_img is not None
    assert list(bi_img.get_flattened_data()) != list(plain_img.get_flattened_data())
    assert list(bi_img.get_flattened_data()) != list(bold_img.get_flattened_data())
    assert _ink_count(bi_img) > _ink_count(plain_img)


def test_draw_six_digit_hex_color_applied() -> None:
    """A 24-bit color tag must produce the opaque color on canvas."""
    cfg = TextConfig(font_size=36, max_width=500)
    img = get_timage("#b#ff0000#Red#", cfg)

    assert img is not None
    red_pixels = [p for p in img.get_flattened_data() if p[3] != 0 and p[0] > 200 and p[1] < 60 and p[2] < 60]
    assert len(red_pixels) > 0


def test_parse_mixed_plain_and_styled_segments() -> None:
    """Mixed text must preserve ordering and per-segment styling."""
    cfg = TextConfig(font_size=36, max_width=500)
    words = _parse("pre #b#ff0000ff#bold# #i#00ff00ff#ital# post", cfg)

    assert [w.text for w in words] == ["pre", " ", "bold", " ", "ital", " ", "post"]
    assert words[2].simulate_bold is True
    assert words[2].color == (255, 0, 0, 255)
    assert words[4].simulate_bold is False
    assert words[4].color == (0, 255, 0, 255)
    assert str(words[4].font.path) == str(cfg.italic_font_path)
    assert words[0].color == cfg.color and words[-1].color == cfg.color


def test_parse_tag_text_preserves_internal_whitespace() -> None:
    """Spaces inside a tag must be preserved as explicit space tokens."""
    words = _parse("#b#ff0000ff#Bold Red Text#")
    assert [w.text for w in words] == ["Bold", " ", "Red", " ", "Text"]
    assert all(w.simulate_bold for w in words)
    assert all(w.color == (255, 0, 0, 255) for w in words)


# === Rich Text Rendering: What Is Drawn ===


def _ink_count(img: Image.Image) -> int:
    """Count non-transparent pixels."""
    return sum(1 for p in img.get_flattened_data() if p[3] != 0)


def test_draw_bold_differs_from_plain() -> None:
    """Bold text must render visibly bolder than the same plain text."""
    cfg = TextConfig(font_size=36, max_width=500)
    bold_img = get_timage("#b#ffffffff#Bold#", cfg)
    plain_img = get_timage("Bold", cfg)

    assert bold_img is not None and plain_img is not None
    # Simulated bold reserves its stroke ink in the advance (one width per side)
    # so the right-most glyph never clips, unlike the plain-text advance.
    stroke_px = 2 * 1
    assert bold_img.width == plain_img.width + stroke_px
    assert list(bold_img.get_flattened_data()) != list(plain_img.get_flattened_data())
    assert _ink_count(bold_img) > _ink_count(plain_img)


def test_draw_italic_differs_from_plain() -> None:
    """Italic text must render with slanted glyphs, distinct from plain."""
    cfg = TextConfig(font_size=36, max_width=500)
    italic_img = get_timage("#i#ffffffff#Italic#", cfg)
    plain_img = get_timage("Italic", cfg)

    assert italic_img is not None and plain_img is not None
    assert list(italic_img.get_flattened_data()) != list(plain_img.get_flattened_data())


def test_draw_tag_color_applied_to_pixels() -> None:
    """The tag color must be the color actually drawn on the canvas."""
    cfg = TextConfig(font_size=36, max_width=500)
    img = get_timage("#b#ff0000ff#Bold#", cfg)

    assert img is not None
    red_pixels = [p for p in img.get_flattened_data() if p[3] != 0 and p[0] > 200 and p[1] < 60 and p[2] < 60]
    assert len(red_pixels) > 0


def test_draw_mixed_line_keeps_bold_segment_bolder() -> None:
    """In a mixed line, the bold segment must render bolder than the plain segments."""
    cfg = TextConfig(font_size=36, max_width=500)
    mixed_img = get_timage("#b#ffffffff#Bold# plain", cfg)
    plain_img = get_timage("Bold plain", cfg)

    assert mixed_img is not None and plain_img is not None
    assert list(mixed_img.get_flattened_data()) != list(plain_img.get_flattened_data())
    assert _ink_count(mixed_img) > _ink_count(plain_img)


def _pixel_hash(img: Image.Image) -> str:
    """SHA-256 of the raw pixel bytes. Fast whole-image fingerprint."""
    return hashlib.sha256(img.tobytes()).hexdigest()


def test_draw_all_styles_pairwise_distinct() -> None:
    """Normal, bold, italic, and bold-italic must each render to unique pixels.

    Uses pixel hashes so a style that silently fails to render (0 pixel diff
    against another variant) is detected immediately. Pairwise hash comparison is
    RELATIVE: it catches a style regressing toward another. It cannot detect
    absolute corruption that preserves distinctness (e.g. a broken font sheet
    rendering tofu in every mode). The absolute non-blank guard below closes
    that gap; the canonical pixel-diff scenarios give cross-version coverage.
    """
    cfg = TextConfig(font_size=36, max_width=500)
    word = "Distinct"

    renders = {
        "plain": get_timage(word, cfg),
        "b": get_timage("#b#ffffffff#Distinct#", cfg),
        "i": get_timage("#i#ffffffff#Distinct#", cfg),
        "bi": get_timage("#bi#ffffffff#Distinct#", cfg),
    }

    assert all(v is not None for v in renders.values())

    hashes = {name: _pixel_hash(img) for name, img in renders.items()}
    assert len(set(hashes.values())) == len(renders), (
        f"Expected all styles to render distinctly, got duplicate pixels: {hashes}"
    )

    # Absolute guard: a wholesale failure must not pass just because the four
    # styles still hash differently while rendering blank/tofu.
    for name, img in renders.items():
        assert _ink_count(img) > 0, f"style '{name}' rendered blank ({hashes[name][:16]})"

    output_dir = "./output/test/timage/styles"
    os.makedirs(output_dir, exist_ok=True)
    for name, img in renders.items():
        img.save(f"{output_dir}/{name}.png")


def test_draw_timage_deterministic() -> None:
    """Same input must produce byte-identical output across runs.

    This is the assumption the golden pixel-diff system relies on. Non-determinism
    here would make reference updates and cross-version `compare` reports flaky.
    """
    cfg = TextConfig(font_size=36, max_width=500)
    text = "#b#ffffffff#Bold# #i#00ff00ff#Italic# #bi#0000ffff#Both#"

    first = get_timage(text, cfg)
    second = get_timage(text, cfg)

    assert first is not None and second is not None
    assert first.tobytes() == second.tobytes(), "get_timage output is not deterministic"


def test_draw_detects_tag_color_on_canvas() -> None:
    """The rendered canvas must contain pixels in the exact tag color."""
    cfg = TextConfig(font_size=36, max_width=500)
    img = get_timage("#b#123456ff#Colored#", cfg)

    assert img is not None
    pixels = img.get_flattened_data()
    exact = (0x12, 0x34, 0x56, 0xFF)
    matching = [p for p in pixels if p == exact]
    assert matching, "No pixel matched the exact tag color (0x123456ff)"


def test_non_token_hashtags_warn_by_default(caplog) -> None:
    """Stray '#' must warn, point out the malformed tag, and show correct usage."""
    cfg = TextConfig(font_size=36, max_width=500)
    get_timage("plain #b#ff0000ff#Bold# and #ff0000#stray# text", cfg)

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    message = str(warnings[0].message)
    assert "not part of a rich text tag" in message
    assert "'#ff0000#stray#'" in message
    assert "#<style>#<color>#text#" in message
    assert "ignore_non_token_hashtags" in message


def test_non_token_hashtags_warn_points_out_missing_color(caplog) -> None:
    """A tag missing its color must be flagged with the correct syntax hint."""
    cfg = TextConfig(font_size=36, max_width=500)
    get_timage("see #b#Bold# here", cfg)

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1
    message = str(warnings[0].message)
    assert "'#b#Bold#'" in message
    assert "#<style>#<color>#text#" in message


def test_non_token_hashtags_suppressed_when_ignored(caplog) -> None:
    """ignore_non_token_hashtags=True must silence the warning yet still parse tags."""
    cfg = TextConfig(font_size=36, max_width=500, ignore_non_token_hashtags=True)
    img = get_timage("plain #b#ff0000ff#Bold# and #ff0000#stray# text", cfg)

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert not warnings, f"Expected no warnings, got: {warnings}"
    assert img is not None
    # Valid tags must still be parsed and rendered with their styling.
    red_pixels = [p for p in img.get_flattened_data() if p[3] != 0 and p[0] > 200 and p[1] < 60 and p[2] < 60]
    assert len(red_pixels) > 0


def test_no_warning_for_clean_rich_text(caplog) -> None:
    """Fully valid rich text must not trigger the stray-hashtag warning."""
    cfg = TextConfig(font_size=36, max_width=500)
    get_timage("#b#ffffffff#Bold# and #b#ff0000ff#Red# text", cfg)

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert not warnings, f"Expected no warnings, got: {warnings}"


def test_text_character_limit_enforced() -> None:
    """A text input exceeding MAX_TEXT_CHARS must be rejected before rendering."""
    cfg = TextConfig(font_size=36, max_width=500)
    from quranmedialib import MAX_TEXT_CHARS

    over = "a" * (MAX_TEXT_CHARS + 1)
    with pytest.raises(ValueError, match="exceeds maximum"):
        get_timage(over, cfg)
    assert get_timage("a" * MAX_TEXT_CHARS, cfg) is not None


def test_text_word_limit_enforced() -> None:
    """A text input exceeding MAX_TEXT_WORDS is rejected even under the char cap."""
    cfg = TextConfig(font_size=36, max_width=500)
    from quranmedialib import MAX_TEXT_WORDS

    over = "a " * (MAX_TEXT_WORDS + 1)
    assert len(over) < 10_000, "word-limit test must stay under the character cap"
    with pytest.raises(ValueError, match="exceeding maximum"):
        get_timage(over, cfg)


def test_overlong_word_canvas_is_clamped(caplog) -> None:
    """A word wider than the container must clamp to MAX_CANVAS_DIMENSION, not OOM."""
    cfg = TextConfig(font_size=100, max_width=50)
    img = get_timage("w" * 3000, cfg)

    assert img is not None
    from quranmedialib.types import MAX_CANVAS_DIMENSION

    assert img.width <= MAX_CANVAS_DIMENSION
    assert img.height <= MAX_CANVAS_DIMENSION
    clamp_warnings = [r for r in caplog.records if r.levelname == "WARNING" and "clamping" in str(r.message)]
    assert clamp_warnings, "Expected a canvas-clamp warning for an over-long word"
