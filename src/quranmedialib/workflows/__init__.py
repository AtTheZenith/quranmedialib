"""High-level workflows for QuranMediaLib."""

from quranmedialib.workflows.isolate_words import IsolateWordsWorkflow
from quranmedialib.workflows.surah import SurahWorkflow
from quranmedialib.workflows.verse import VerseWorkflow
from quranmedialib.workflows.verse_range import VerseRangeWorkflow

__all__ = ["IsolateWordsWorkflow", "VerseWorkflow", "SurahWorkflow", "VerseRangeWorkflow"]
