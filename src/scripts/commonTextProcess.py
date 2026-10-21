"""
Text process: Vietnamese syllables, merge text, similarity, Roman numerals.
"""
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

# Add scripts directory to path for relative imports
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import commonMyUtils

ex = commonMyUtils.exc

VALID_ONSETS = [
    "b", "c", "ch", "d", "đ", "g", "gh", "gi",
    "h", "k", "kh", "l", "m", "n", "ng", "ngh",
    "nh", "p", "ph", "q", "r", "s", "t", "th",
    "tr", "v", "x",
]

VALID_NUCLEI = [
    "a", "ă", "â", "e", "ê", "i", "o", "ô", "ơ", "u", "ư", "y",
    "ia", "iê", "ya", "ua", "uô", "ưa", "ươ",
    "ai", "ao", "au", "ay", "âu", "ây",
    "eo", "êu",
    "ia", "iê", "yê",
    "oi", "ôi", "ơi",
    "ua", "uô", "ươ", "ưu", "uy", "uya",
]

VALID_CODAS = ["c", "ch", "m", "n", "ng", "nh", "p", "t"]


def isAbbreviation(word: str) -> bool:
    w = word.lower()
    w = re.sub(r"[^a-zăâêôơưđ]", "", w)
    if not w:
        return True
    onset = None
    for o in sorted(VALID_ONSETS, key=len, reverse=True):
        if w.startswith(o):
            onset = o
            break
    rest = w[len(onset) :] if onset else w
    if onset is None and rest and rest[0] not in "aeiouyăâêôơư":
        return True
    coda = None
    for c in sorted(VALID_CODAS, key=len, reverse=True):
        if rest.endswith(c):
            coda = c
            break
    nucleus = rest[: -len(coda)] if coda else rest
    if not nucleus:
        return True
    if nucleus not in VALID_NUCLEI:
        return True
    parts = [p for p in [onset, nucleus, coda] if p]
    if len(parts) > 3:
        return True
    return False


def normalizeWord(w: str) -> str:
    return re.sub(r"[^A-Za-zÀ-ỹĐđ0-9]", "", w)


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def isRoman(s: str) -> bool:
    return bool(re.fullmatch(r"[IVXLC]+", s))


def romanToInt(s: str) -> int:
    romanNumerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    result, prev = 0, 0
    for c in reversed(s):
        val = romanNumerals.get(c, 0)
        if val < prev:
            result -= val
        else:
            result += val
            prev = val
    return result


def stripExtraSpaces(s: str) -> str:
    if not isinstance(s, str):
        return s
    return re.sub(r"\s+", " ", s).strip()


def mergeTxt(rawDataDict: dict, jsonKey: str, jsonField: str) -> str:
    paragraphs = rawDataDict.get(jsonKey, [])
    merged = "\n".join(
        p.get(jsonField, "").strip() for p in paragraphs if p.get(jsonField)
    )
    merged = re.sub(r"\n{2,}", "\n", merged.strip())
    return merged
