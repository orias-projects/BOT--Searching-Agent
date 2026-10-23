"""
Merge PDF lines into paragraphs: style, alignment, validators, builder.
"""
from collections import Counter
from statistics import mean, multimode


class MergeUtils:
    @staticmethod
    def mergeStyle(styles):
        digits = [list(str(s).zfill(4)) for s in styles]
        minDigits = [min(int(d[i]) for d in digits) for i in range(4)]
        return int("".join(str(d) for d in minDigits))

    @staticmethod
    def mostCommon(values):
        if not values:
            return None
        count = Counter(values)
        most = count.most_common(1)
        return most[0][0] if most else None


class MergeValidator:
    @staticmethod
    def canMerge(prev, curr, idxPrev=None, idxCurr=None):
        if MergeValidator.isNewPara(curr):
            return False
        if not MergeValidator.isSameFontSize(prev, curr):
            return False
        if not MergeValidator.isSameStyle(prev, curr):
            return False
        if not MergeValidator.isNear(prev, curr):
            return False
        if MergeValidator.isSameAlign(prev, curr):
            return True
        if MergeValidator.isBadAlign(prev, curr):
            return False
        if MergeValidator.canMergeWithAlign(prev) or MergeValidator.canMergeWithLeft(prev, curr):
            return True
        return False

    @staticmethod
    def isNewPara(line):
        return line.get("MarkerText") not in (None, "", " ")

    @staticmethod
    def isSameFontSize(prev, curr):
        return abs(prev["FontSize"] - curr["FontSize"]) <= 0.7

    @staticmethod
    def isSameStyle(prev, curr):
        return (
            MergeValidator.isSameLineStyle(prev, curr)
            or MergeValidator.isSameFirstStyle(prev, curr)
            or MergeValidator.isSameLastStyle(prev, curr)
            or MergeValidator.isSameWordStyle(prev, curr)
        )

    @staticmethod
    def isSameLineStyle(prev, curr):
        return prev["Style"] == curr["Style"]

    @staticmethod
    def isSameLineFStyle(prev, curr):
        return prev["Style"] % 1000 == curr["Style"] % 1000

    @staticmethod
    def isSameLineCase(prev, curr):
        return prev["Style"] // 1000 == curr["Style"] // 1000

    @staticmethod
    def isSameFirstStyle(prev, curr):
        return prev["Style"] == curr["Words"]["First"]["Style"]

    @staticmethod
    def isSameFirstFStyle(prev, curr):
        return prev["Style"] % 1000 == curr["Words"]["First"]["Style"] % 1000

    @staticmethod
    def isSameFirstCase(prev, curr):
        return prev["Style"] // 1000 == curr["Words"]["First"]["Style"] // 1000

    @staticmethod
    def isSameLastStyle(prev, curr):
        return prev["Words"]["Last"]["Style"] == curr["Style"]

    @staticmethod
    def isSameLastFStyle(prev, curr):
        return prev["Words"]["Last"]["Style"] % 1000 == curr["Style"] % 1000

    @staticmethod
    def isSameLastCase(prev, curr):
        return prev["Words"]["Last"]["Style"] // 1000 == curr["Style"] // 1000

    @staticmethod
    def isSameWordStyle(prev, curr):
        return prev["Words"]["Last"]["Style"] == curr["Words"]["First"]["Style"]

    @staticmethod
    def isSameWordFStyle(prev, curr):
        return prev["Words"]["Last"]["Style"] % 1000 == curr["Words"]["First"]["Style"] % 1000

    @staticmethod
    def isSameWordCase(prev, curr):
        return prev["Words"]["Last"]["Style"] // 1000 == curr["Words"]["First"]["Style"] // 1000

    @staticmethod
    def isNear(prev, curr):
        if "Position" not in prev or "Position" not in curr:
            return False
        if "LineHeight" not in curr:
            return False
        higCurr = curr["LineHeight"]
        topPrev = prev["Position"]["Top"]
        topCurr = curr["Position"]["Top"]
        botCurr = curr["Position"]["Bot"]
        return (topCurr < topPrev * 2) and ((topCurr < botCurr * 2) or botCurr <= 3.0) and (topCurr < higCurr * 5)

    @staticmethod
    def isSameAlign(prev, curr):
        return prev.get("Align") == curr.get("Align")

    @staticmethod
    def isBadAlign(prev, curr):
        return prev.get("Align") != "right" and curr.get("Align") == "right"

    @staticmethod
    def isNoSameAlign0(prev):
        return prev.get("Align") == "Justify"

    @staticmethod
    def isNoSameAlignC(prev):
        return prev.get("Align") == "Center"

    @staticmethod
    def isNoSameAlignR(prev):
        return prev.get("Align") == "Right"

    @staticmethod
    def isNoSameAlignL(prev, curr):
        return prev.get("Align") == "Left" and curr.get("Align") == "Justify"

    @staticmethod
    def canMergeWithAlign(prev):
        return (
            MergeValidator.isNoSameAlign0(prev)
            or MergeValidator.isNoSameAlignC(prev)
            or MergeValidator.isNoSameAlignR(prev)
        )

    @staticmethod
    def canMergeWithLeft(prev, curr):
        return MergeValidator.isNoSameAlignL(prev, curr)


class ParagraphBuilder:
    def __init__(self, lines, paraId, general=None):
        self.lines = lines
        self.paraId = paraId
        self.general = general

    def build(self):
        text = " ".join([ln["Text"] for ln in self.lines])
        markerText = self.lines[0]["MarkerText"]
        markerType = self.lines[0]["MarkerType"]
        style = MergeUtils.mergeStyle([ln["Style"] for ln in self.lines])
        fsValues = [ln["FontSize"] for ln in self.lines if ln.get("FontSize") is not None]
        if fsValues:
            modes = multimode(fsValues)
            if len(modes) == 1:
                fontSize = modes[0]
            else:
                if self.general and self.general.get("commonFontSize") is not None:
                    target = self.general["commonFontSize"]
                    fontSize = min(modes, key=lambda x: abs(x - target))
                else:
                    fontSize = mean(fsValues)
            fontSize = round(fontSize, 1)
        else:
            fontSize = 12.0
        align = MergeUtils.mostCommon([ln["Align"] for ln in self.lines]) or self.lines[-1]["Align"]
        return {
            "Paragraph": self.paraId,
            "Text": text,
            "MarkerText": markerText,
            "MarkerType": markerType,
            "Style": style,
            "FontSize": fontSize,
            "Align": align,
        }


class GeneralUpdater:
    def __init__(self, mergedJson):
        self.mergedJson = mergedJson
        self.paragraphs = mergedJson.get("paragraphs", [])
        self.general = mergedJson["general"]
        self.total = len(self.paragraphs)

    def recompute(self):
        self._updateFontSizes()
        self._updateMarkers()
        return self.mergedJson

    def _updateFontSizes(self):
        fsValues = [p["FontSize"] for p in self.paragraphs if p.get("FontSize") is not None]
        fsCounter = Counter(fsValues)
        commonFontSizes = [{"FontSize": round(fs, 1), "Count": cnt} for fs, cnt in fsCounter.most_common()]
        commonFontSize = commonFontSizes[0]["FontSize"] if commonFontSizes else None
        self.general.update({"commonFontSize": commonFontSize, "commonFontSizes": commonFontSizes})

    def _updateMarkers(self):
        mkValues = [p["MarkerType"] for p in self.paragraphs if p.get("MarkerType")]
        mkCounter = Counter(mkValues)
        threshold = max(1, int(self.total * 0.005))
        commonMarkers = [m for m, c in mkCounter.most_common(10) if c >= threshold]
        self.general.update({"commonMarkers": commonMarkers})


class ParagraphMerger:
    def merge(self, baseJson):
        general = baseJson["general"]
        lines = baseJson["lines"]
        paragraphs = []
        buffer = []
        for i, curr in enumerate(lines):
            if not buffer:
                buffer.append(curr)
                continue
            prev = lines[i - 1]
            if MergeValidator.canMerge(prev, curr, i - 1, i):
                buffer.append(curr)
            else:
                builder = ParagraphBuilder(buffer, len(paragraphs) + 1, general)
                paragraphs.append(builder.build())
                buffer = [curr]
        if buffer:
            builder = ParagraphBuilder(buffer, len(paragraphs) + 1, general)
            paragraphs.append(builder.build())
        merged = {"general": general, "paragraphs": paragraphs}
        updater = GeneralUpdater(merged)
        return updater.recompute()
