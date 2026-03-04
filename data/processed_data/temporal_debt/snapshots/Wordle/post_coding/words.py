'''

Word lists and word-selection helpers:
- ANSWER_LIST: curated list of 5-letter English words used for the daily answer.
- get_daily_word(date=None): deterministically picks a word based on date (UTC).
- get_random_word(): returns a random answer word.
'''

import random
from datetime import date as Date, datetime, timezone

# A modest curated list of 5-letter English words for daily answers.
# You can extend this list as desired.
ANSWER_LIST = [
    "apple", "brave", "crane", "delta", "eagle", "flame", "grape", "honey", "ivory", "joker",
    "kneel", "lemon", "mango", "noble", "ocean", "piano", "queen", "roast", "sunny", "tiger",
    "ultra", "vigor", "whale", "xenon", "yacht", "zesty", "adore", "bloom", "cider", "dolly",
    "ember", "fancy", "glove", "hazel", "irony", "jelly", "kitty", "lunar", "mirth", "nylon",
    "optic", "pride", "quilt", "rally", "salsa", "tease", "unite", "vivid", "waltz", "xylem",
    "yodel", "zebra", "angel", "bison", "chess", "dwell", "elite", "forgo", "gamma", "hippo",
    "inert", "jaunt", "karma", "linen", "metal", "nicer", "omega", "parer", "quake", "riper",
    "solar", "table", "unfed", "voter", "woven", "xerox", "yearn", "zonal", "aloft", "blaze",
    "canny", "drape", "expel", "femur", "gaily", "hoist", "ingot", "jolly", "knack", "lodge",
    "moult", "naiad", "ounce", "pleat", "radii", "sleigh", "theta", "udder", "vaunt", "worry",
    "wreak", "wrung", "yeast", "zesty"
]

def _utc_today() -> Date:
    return datetime.now(timezone.utc).date()

def get_daily_word(date: Date = None) -> str:
    """
    Deterministically return the daily word for the given UTC date.
    If date is None, use today's UTC date.
    Uses a fixed base date to compute an index into ANSWER_LIST.
    """
    base = Date(2021, 6, 19)  # Wordle-origin-like base date
    if date is None:
        date = _utc_today()
    if date < base:
        # If before base, wrap forward using absolute day difference
        idx = abs((base - date).days) % len(ANSWER_LIST)
        return ANSWER_LIST[idx]
    offset = (date - base).days
    idx = offset % len(ANSWER_LIST)
    return ANSWER_LIST[idx]

def get_random_word() -> str:
    """Return a random word from the ANSWER_LIST."""
    return random.choice(ANSWER_LIST)
