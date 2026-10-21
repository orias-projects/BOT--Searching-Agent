"""
PDF line/word/span helpers: font flags, coords, words, line size.
"""
import sys
from pathlib import Path

# Add parent scripts directory to path for commonMyUtils import
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import commonMyUtils as MyUtils


def fontFlags(span: dict) -> tuple:
    flags = span.get("flags", 0)
    b = bool(flags & 16)
    i = bool(flags & 2)
    u = bool(flags & 8)
    return b, i, u


def setAlign(position: dict, regionWidth: float) -> str:
    mid = abs(position["Mid"])
    left = position["Left"]
    if mid <= 0.01 * regionWidth:
        if left > 0.01 * regionWidth:
            return "Center"
        return "Justify"
    if position["Mid"] > 0.01 * regionWidth:
        return "Right"
    return "Left"


def setPosition(line: dict, prev_line: dict | None, next_line: dict | None, xStart: float, xEnd: float, xMid: float) -> tuple:
    left = round(line["Coords"]["X0"] - xStart, 1)
    right = round(xEnd - line["Coords"]["X1"], 1)
    mid = round(line["Coords"]["XM"] - xMid, 1)
    top = round(line["Coords"]["Y1"] - prev_line["Coords"]["Y1"], 1) if prev_line else 0
    bot = round(next_line["Coords"]["Y1"] - line["Coords"]["Y1"], 1) if next_line else 0
    return (left, right, mid, top, bot)


def extractWords(line: dict) -> list:
    spans = line.get("spans", [])
    if not spans or not line.get("text", "").strip():
        return []
    validSpans = [s for s in spans if s.get("text", "").strip()]
    if not validSpans:
        validSpans = spans
    words = []
    for s in validSpans:
        for raw in s.get("text", "").split():
            words.append((raw, s))
    return words


def getWordText(line: dict, index: int) -> str:
    words = extractWords(line)
    if -len(words) <= index < len(words):
        return words[index][0]
    return ""


def getWordFontSize(line: dict, index: int) -> float:
    words = extractWords(line)
    if -len(words) <= index < len(words):
        _, span = words[index]
        return round(span.get("size", 12.0), 1)
    return 0.0


def getWordCoord(line: dict, index: int) -> tuple:
    words = extractWords(line)
    if -len(words) <= index < len(words):
        _, span = words[index]
        x0, y0, x1, y1 = span["bbox"]
        return (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))
    return (0, 0, 0, 0)


def getLineFontSize(line: dict) -> float:
    words = extractWords(line)
    if not words:
        return 12.0
    sizes = [span.get("size", 12.0) for _, span in words]
    return round(sum(sizes) / len(sizes) * 2) / 2


def getLineCoord(line: dict) -> tuple:
    words = extractWords(line)
    if not words:
        return (0, 0, 0, 0, 0)
    coords = []
    for _, span in words:
        x0, y0, x1, y1 = span["bbox"]
        coords.append((round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)))
    x0 = coords[0][0]
    x1 = coords[-1][2]
    y0 = min(c[1] for c in coords)
    y1 = max(c[3] for c in coords)
    xm = round((x0 + x1) / 2, 1)
    return (x0, x1, xm, y0, y1)


def setLineSize(line: dict) -> tuple:
    x0 = line["Coords"]["X0"]
    x1 = line["Coords"]["X1"]
    y0 = line["Coords"]["Y0"]
    y1 = line["Coords"]["Y1"]
    return (round(x1 - x0, 1), round(y1 - y0, 1))


def setPageCoords(lines: list, pageGeneralSize: tuple) -> tuple:
    x0s = [round(l["Coords"]["X0"], 1) for l in lines]
    x1s = [round(l["Coords"]["X1"], 1) for l in lines]
    y0s = [round(l["Coords"]["Y0"], 1) for l in lines]
    y1s = [round(l["Coords"]["Y1"], 1) for l in lines]
    xStart = MyUtils.mostCommon(x0s)
    pageWidth = pageGeneralSize[1]
    threshold = pageWidth * 0.75
    x1Candidates = [x for x in x1s if x >= threshold]
    xEnd = MyUtils.mostCommon(x1Candidates) if x1Candidates else max(x1s)
    yStart = min(y0s)
    yEnd = max(y1s)
    xMid = round((xStart + xEnd) / 2, 1)
    yMid = round((yStart + yEnd) / 2, 1)
    return (xStart, yStart, xEnd, yEnd, xMid, yMid)


def setPageRegionSize(xStart: float, yStart: float, xEnd: float, yEnd: float) -> tuple:
    return (round(xEnd - xStart, 1), round(yEnd - yStart, 1))
