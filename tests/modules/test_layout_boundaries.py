from quranmedialib.modules.text_layout import StyledWord, wrap_rich_text_balanced


def create_mock_word(text: str, width: float, height: int = 50, ascent: int = 30) -> StyledWord:
    """Create a StyledWord with a specific width for layout testing."""
    # Use a dummy font object with a mock getlength if needed,
    # but StyledWord takes width as an argument.
    return StyledWord(
        text=text,
        font=None,  # type: ignore
        color=(255, 255, 255, 255),
        width=width,
        height=height,
        ascent=ascent,
    )


def test_balance_lines_empty():
    """Test wrapping an empty list of words."""
    assert wrap_rich_text_balanced([], 1000) == []


def test_balance_lines_single_oversized_word():
    """Test a single word that exceeds the max_width."""
    words = [create_mock_word("LongWord", 1200)]
    lines = wrap_rich_text_balanced(words, 1000)
    assert len(lines) == 1
    assert len(lines[0].words) == 1


def test_balance_lines_perfect_fit():
    """Test words that fit exactly into the max_width."""
    # 3 words of 300px = 900px
    words = [create_mock_word("W1", 300), create_mock_word("W2", 300), create_mock_word("W3", 300)]
    lines = wrap_rich_text_balanced(words, 900)
    assert len(lines) == 1
    assert len(lines[0].words) == 3


def test_balance_lines_extreme_width():
    """Test extremely large max_width."""
    words = [create_mock_word(f"W{i}", 100) for i in range(10)]
    lines = wrap_rich_text_balanced(words, 10000)
    assert len(lines) == 1
    assert len(lines[0].words) == 10


def test_balance_lines_minimum_width():
    """Test extremely small max_width."""
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    lines = wrap_rich_text_balanced(words, 50)  # Every word is 100, max is 50
    assert len(lines) == 5
    for line in lines:
        assert len(line.words) == 1


def test_balance_lines_pyramid_shape():
    """Test the inverted pyramid balancing logic."""
    # words: [100, 100, 100, 100, 100]
    # max_width: 300
    words = [create_mock_word(f"W{i}", 100) for i in range(5)]
    lines = wrap_rich_text_balanced(words, 300)

    assert len(lines) == 2
    assert len(lines[0].words) == 3
    assert len(lines[1].words) == 2


def test_balance_lines_large_fonts():
    """Test words with extremely large widths."""
    words = [create_mock_word("Giant", 5000), create_mock_word("Tiny", 10)]
    lines = wrap_rich_text_balanced(words, 1000)
    assert len(lines) == 2
    assert lines[0].words[0].width == 5000
