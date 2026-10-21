"""
Vietnamese semantic chunking: sentence split, extractive filter, semantic grouping.
"""
import re
from typing import Any, List

import numpy as np
from underthesea import sent_tokenize


class ChunkUndertheseaBuilder:
    def __init__(
        self,
        embedder: Any,
        device: str = "cpu",
        minWords: int = 256,
        maxWords: int = 768,
        simThreshold: float = 0.7,
        keySentRatio: float = 0.4,
    ):
        if embedder is None:
            raise ValueError("❌ Cần truyền mô hình embedder đã load sẵn.")
        self.embedder = embedder
        self.device = device
        self.minWords = minWords
        self.maxWords = maxWords
        self.simThreshold = simThreshold
        self.keySentRatio = keySentRatio

    def _splitSentences(self, text: str) -> List[str]:
        text = re.sub(r"[\x00-\x1f]+", " ", text)
        try:
            sents = sent_tokenize(text)
        except Exception:
            sents = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sents if len(s.strip()) > 2]

    def _encode(self, sentences: List[str]) -> np.ndarray:
        try:
            return self.embedder.encode(
                sentences,
                convert_to_numpy=True,
                show_progress_bar=False,
                device=str(self.device),
            )
        except TypeError:
            return self.embedder.encode(
                sentences, convert_to_numpy=True, show_progress_bar=False
            )
        except RuntimeError as e:
            if "CUDA" in str(e):
                return self.embedder.encode(
                    sentences,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                    device="cpu",
                )
            raise e

    def _extractiveFilter(self, sentences: List[str]) -> List[str]:
        if len(sentences) <= 3:
            return sentences
        embeddings = self._encode(sentences)
        meanVec = np.mean(embeddings, axis=0)
        sims = np.dot(embeddings, meanVec) / (
            np.linalg.norm(embeddings, axis=1) * np.linalg.norm(meanVec)
        )
        k = max(1, int(len(sentences) * self.keySentRatio))
        idx = np.argsort(-sims)[:k]
        idx.sort()
        return [sentences[i] for i in idx]

    def _semanticGroup(self, sentences: List[str]) -> List[str]:
        if not sentences:
            return []
        embeddings = self._encode(sentences)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        chunks, curChunk, curLen = [], [], 0
        for i, sent in enumerate(sentences):
            wc = len(sent.split())
            if not curChunk:
                curChunk.append(sent)
                curLen = wc
                continue
            sim = np.dot(embeddings[i - 1], embeddings[i])
            tooLong = curLen + wc > self.maxWords
            tooShort = curLen < self.minWords
            topicChanged = sim < self.simThreshold
            if tooLong or (not tooShort and topicChanged):
                chunks.append(" ".join(curChunk))
                curChunk = [sent]
                curLen = wc
            else:
                curChunk.append(sent)
                curLen += wc
        if curChunk:
            chunks.append(" ".join(curChunk))
        return chunks

    def build(self, fullText: str) -> List[dict]:
        allSentences = self._splitSentences(fullText)
        filtered = self._extractiveFilter(allSentences)
        chunks = self._semanticGroup(filtered)
        return [{"Index": i, "Content": chunk} for i, chunk in enumerate(chunks, start=1)]
