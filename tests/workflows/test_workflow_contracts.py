"""Contract tests for all QuranMediaLib workflows.

Ensures that all workflows implement the BaseWorkflow interface consistently
and handle common parameters and error cases in a standardized way.
"""

from typing import Iterator

import pytest
from PIL import Image

from quranmedialib import LANDSCAPE_PRESET, IsolateWordsWorkflow, SurahWorkflow, VerseRangeWorkflow, VerseWorkflow
from quranmedialib.workflows.base import BaseWorkflow


@pytest.fixture(params=[VerseWorkflow, SurahWorkflow, VerseRangeWorkflow, IsolateWordsWorkflow])
def workflow_class(request):
    """Fixture providing each workflow class for parameterized testing."""
    return request.param


def test_workflow_inheritance(workflow_class) -> None:
    """Verify that every workflow inherits from BaseWorkflow."""
    assert issubclass(workflow_class, BaseWorkflow)


def test_workflow_init_null_configs_rejected(workflow_class) -> None:
    """Verify that all workflows reject None configurations during init."""

    with pytest.raises(ValueError, match="must not be None"):
        workflow_class(None)


def test_workflow_iterator_contract(workflow_class) -> None:
    """Verify that get_iterator returns an Iterator of image lists (layers)."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = workflow_class(preset)

    # We use very basic params to avoid DB errors during contract check
    # Surah 108 is short (3 verses)
    params = {
        VerseWorkflow: {"surah": 108, "ayah": 1, "translations": ["Test Translation"]},
        SurahWorkflow: {"surah": 108},
        VerseRangeWorkflow: {"surah": 108, "start_ayah": 1, "end_ayah": 1, "translations": [["Test Translation"]]},
        IsolateWordsWorkflow: {
            "surah": 108,
            "ayah": 1,
            "verse_words": ["Test", "Words"],
            "word_indices": [1],
            "translations": ["Test Translation"],
        },
    }

    # get_iterator should return an Iterator
    iterator = workflow.get_iterator(**params[workflow_class])
    assert isinstance(iterator, Iterator)

    # Result of iteration should be list of PIL Images
    first_result = next(iterator)
    assert isinstance(first_result, list)
    assert len(first_result) > 0
    assert isinstance(first_result[0], Image.Image)


def test_workflow_repr_standardization(workflow_class) -> None:
    """Verify that workflows have a standardized __repr__ implementation."""
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = workflow_class(preset)

    repr_str = repr(workflow)
    assert workflow_class.__name__ in repr_str
    assert "frame=" in repr_str
    assert "text=" in repr_str
    assert "word=" in repr_str
