
import cProfile
import pstats
from quranmedialib import VerseWorkflow, LANDSCAPE_PRESET, DatabaseManager
from quranmedialib.types import WordItem
from PIL import Image

def run_simulated_surah():
    db = DatabaseManager()
    preset = LANDSCAPE_PRESET["default"]["1080p"]
    workflow = VerseWorkflow(preset)
    
    # Simulate Al-Baqarah (roughly 286 verses)
    # We'll just do a few to see where time goes, then scale.
    for surah in [2]:
        verses = db.get_verses_from_surah(surah)
        for ayah_text in verses:
            translation = [db.get_translation_from_verse(surah, 1)] # Simplified
            list(workflow.get_iterator(surah=surah, ayah=1, translations=translation))

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()
    run_simulated_surah()
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumulative")
    stats.print_stats(50)
