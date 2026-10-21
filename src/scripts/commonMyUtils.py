"""
Common utilities: JSON/CSV/XLSX handling, text preprocessing, flattening, chunkmap.

Shared utility module used by both backend services and setup scripts.
"""
import json
import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

try:
    import openpyxl
except ImportError:
    openpyxl = None

import pandas as pd

DEFAULT_NON_KEEP_PATTERN = re.compile(
    r"[^\w\s\(\)\.\,\;\:\-\+]", flags=re.UNICODE
)

def exc(func, fallback=None):
    try:
        return func()
    except Exception as e:
        logging.warning(e)
        return fallback


def fileExists(path: str) -> bool:
    return os.path.exists(path)


def readJson(path: str) -> Any:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def writeJson(data: Any, path: str, indent: int = 2) -> None:
    dirPath = os.path.dirname(path)
    if dirPath:
        os.makedirs(dirPath, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def insertJson(data: Any, path: str, indent: int = 2) -> None:
    dirPath = os.path.dirname(path)
    if dirPath:
        os.makedirs(dirPath, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def readJsonl(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def writeJsonl(data: List[dict], path: str) -> None:
    dirPath = os.path.dirname(path)
    if dirPath:
        os.makedirs(dirPath, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def insertJsonl(data: List[dict], path: str) -> None:
    dirPath = os.path.dirname(path)
    if dirPath:
        os.makedirs(dirPath, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def jsonConvert(data: Any, pretty: bool = True) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2 if pretty else None)


def jsonlConvert(data: List[dict]) -> str:
    return "\n".join(json.dumps(item, ensure_ascii=False) for item in data)


# ==============================
# UNIQUE FUNCTIONS
# ==============================


def sortRecords(data: List[dict], keys: List[str]) -> List[dict]:
    return sorted(data, key=lambda x: tuple(x.get(k) for k in keys))


def mostCommon(values: List[Any]) -> Any:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def preprocessText(
    text: Any,
    nonKeepPattern: re.Pattern = DEFAULT_NON_KEEP_PATTERN,
    maxCharsPerText: int | None = None,
) -> Any:
    if isinstance(text, list):
        return [
            preprocessText(t, nonKeepPattern=nonKeepPattern, maxCharsPerText=maxCharsPerText)
            for t in text
        ]
    if isinstance(text, str):
        s = text.strip()
        s = nonKeepPattern.sub("", s)
        s = re.sub(r"[ ]{2,}", " ", s)
        if maxCharsPerText is not None and len(s) > maxCharsPerText:
            s = s[:maxCharsPerText]
        return s
    return text


def preprocessData(
    data: Any,
    nonKeepPattern: re.Pattern = DEFAULT_NON_KEEP_PATTERN,
    maxCharsPerText: int | None = None,
) -> Any:
    if isinstance(data, dict):
        return {
            k: preprocessData(v, nonKeepPattern=nonKeepPattern, maxCharsPerText=maxCharsPerText)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [
            preprocessData(x, nonKeepPattern=nonKeepPattern, maxCharsPerText=maxCharsPerText)
            for x in data
        ]
    return preprocessText(
        data, nonKeepPattern=nonKeepPattern, maxCharsPerText=maxCharsPerText
    )


def flattenJson(
    data: Any,
    prefix: str = "",
    flattenMode: str = "split",
    joinSep: str = "\n",
) -> Dict[str, Any]:
    flat: Dict[str, Any] = {}

    def _recur(node: Any, pfx: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                newPfx = f"{pfx}{k}" if not pfx else f"{pfx}.{k}"
                _recur(v, newPfx)
            return
        if isinstance(node, list):
            if flattenMode == "split":
                for i, item in enumerate(node):
                    idxKey = f"{pfx}[{i}]"
                    _recur(item, idxKey)
            elif flattenMode == "join":
                joined = joinSep.join(str(x).strip() for x in node if str(x).strip())
                flat[pfx] = joined
            else:
                flat[pfx] = node
            return
        flat[pfx] = node

    _recur(data, prefix.rstrip("."))
    return flat


def deduplicatesByKey(pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    seenPerKey: Dict[str, set] = {}
    filtered: List[Tuple[str, str]] = []
    for key, text in pairs:
        textNorm = text.strip()
        if not textNorm:
            continue
        baseKey = re.sub(r"\[\d+\]", "", key)
        if baseKey not in seenPerKey:
            seenPerKey[baseKey] = set()
        if textNorm in seenPerKey[baseKey]:
            continue
        seenPerKey[baseKey].add(textNorm)
        filtered.append((key, textNorm))
    return filtered


def writeChunkmap(
    mapChunkPath: str, segmentPath: str, chunkGroups: List[List[int]]
) -> None:
    with open(mapChunkPath, "w", encoding="utf-8") as f:
        f.write("{\n")
        f.write('  "index_to_chunk": {\n')
        items = list(enumerate(chunkGroups))
        for i, (idx, group) in enumerate(items):
            groupStr = "[" + ", ".join(map(str, group)) + "]"
            comma = "," if i < len(items) - 1 else ""
            f.write(f'    "{idx}": {groupStr}{comma}\n')
        f.write("  },\n")
        f.write("  \"meta\": {\n")
        f.write(f'    "count": {len(chunkGroups)},\n')
        f.write(f'    "source": "{os.path.basename(segmentPath)}"\n')
        f.write("  }\n")
        f.write("}\n")
