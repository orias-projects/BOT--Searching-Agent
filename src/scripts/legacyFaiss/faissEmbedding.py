"""
Build FAISS index from segment JSON: flatten, encode, dedupe, write mapping.
"""
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
import torch

# Add parent scripts directory to path for commonMyUtils import
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import commonMyUtils as MyUtils

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class DirectFaissIndexer:
    def __init__(
        self,
        indexer: Any,
        device: str = "cpu",
        batch_size: int = 32,
        show_progress: bool = False,
        flatten_mode: str = "split",
        join_sep: str = "\n",
        allowed_schema_types: Tuple[str, ...] = ("string", "array", "dict"),
        max_chars_per_text: Optional[int] = None,
        normalize: bool = True,
        verbose: bool = False,
        listPolicy: str = "split",
    ):
        self.indexer = indexer
        self.device = device
        self.batch_size = batch_size
        self.show_progress = show_progress
        self.flatten_mode = flatten_mode
        self.join_sep = join_sep
        self.allowed_schema_types = allowed_schema_types
        self.max_chars_per_text = max_chars_per_text
        self.normalize = normalize
        self.verbose = verbose
        self.listPolicy = listPolicy
        self._non_keep_pattern = re.compile(
            r"[^\w\s\(\)\.\,\;\:\-–]", flags=re.UNICODE
        )

    @staticmethod
    def _baseKeyForSchema(key: str) -> str:
        return re.sub(r"\[\d+\]", "", key)

    def _eligibleBySchema(self, key: str, schema: Optional[Dict[str, str]]) -> bool:
        if schema is None:
            return True
        baseKey = self._baseKeyForSchema(key)
        typ = schema.get(baseKey)
        return (typ in self.allowed_schema_types) if typ is not None else False

    def _preprocessData(self, data: Any) -> Any:
        if MyUtils and hasattr(MyUtils, "preprocessData"):
            return MyUtils.preprocessData(
                data,
                nonKeepPattern=self._non_keep_pattern,
                maxCharsPerText=self.max_chars_per_text,
            )
        return data

    def _flattenJson(self, data: Any) -> Dict[str, Any]:
        if self.listPolicy == "merge":

            def _mergeLists(obj):
                if isinstance(obj, dict):
                    return {k: _mergeLists(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    if all(isinstance(i, (str, int, float)) for i in obj):
                        return self.join_sep.join(map(str, obj))
                    return [_mergeLists(v) for v in obj]
                return obj

            data = _mergeLists(data)
        return MyUtils.flattenJson(
            data, prefix="", flattenMode=self.flatten_mode, joinSep=self.join_sep
        )

    def _encodeTexts(self, texts: List[str]) -> torch.Tensor:
        try:
            return self.indexer.encode(
                sentences=texts,
                batch_size=self.batch_size,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=self.show_progress,
            )
        except RuntimeError as e:
            if "CUDA out of memory" in str(e):
                try:
                    self.indexer.to("cpu")
                except Exception:
                    pass
                return self.indexer.encode(
                    sentences=texts,
                    batch_size=self.batch_size,
                    convert_to_tensor=True,
                    device="cpu",
                    show_progress_bar=self.show_progress,
                )
            raise e

    @staticmethod
    def _l2Normalize(mat: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return mat / norms

    def _createFaissIndex(self, matrix: np.ndarray) -> faiss.Index:
        dim = int(matrix.shape[1])
        index = faiss.IndexFlatIP(dim)
        index.add(matrix.astype("float32"))
        return index

    def deduplicatesWithMask(
        self,
        pairs: List[Tuple[str, str]],
        chunk_map: List[int],
    ) -> Tuple[List[Tuple[str, str]], List[List[int]]]:
        assert len(pairs) == len(chunk_map)
        seen_per_key: Dict[str, Dict[str, int]] = {}
        filtered_pairs: List[Tuple[str, str]] = []
        chunkGroups: List[List[int]] = []
        for (key, text), c in zip(pairs, chunk_map):
            text_norm = text.strip()
            if not text_norm:
                continue
            base_key = re.sub(r"\[\d+\]", "", key)
            if base_key not in seen_per_key:
                seen_per_key[base_key] = {}
            if text_norm in seen_per_key[base_key]:
                idx = seen_per_key[base_key][text_norm]
                if c not in chunkGroups[idx]:
                    chunkGroups[idx].append(c)
                continue
            seen_per_key[base_key][text_norm] = len(filtered_pairs)
            filtered_pairs.append((key, text_norm))
            chunkGroups.append([c])
        return filtered_pairs, chunkGroups

    def buildFromJson(
        self,
        segmentPath: str,
        schemaDict: Optional[Dict],
        faissPath: str,
        mapDataPath: str,
        mappingPath: str,
        mapChunkPath: Optional[str] = None,
    ) -> Tuple[Any, Dict, Dict, List]:
        assert os.path.exists(segmentPath), f"Không thấy file JSON: {segmentPath}"
        os.makedirs(os.path.dirname(faissPath), exist_ok=True)
        os.makedirs(os.path.dirname(mapDataPath), exist_ok=True)
        os.makedirs(os.path.dirname(mappingPath), exist_ok=True)
        if mapChunkPath:
            os.makedirs(os.path.dirname(mapChunkPath), exist_ok=True)
        schema = schemaDict
        dataObj = MyUtils.readJson(segmentPath)
        dataList = dataObj if isinstance(dataObj, list) else [dataObj]
        pairList: List[Tuple[str, str]] = []
        chunkMap: List[int] = []
        for chunkId, item in enumerate(dataList, start=1):
            processed = self._preprocessData(item)
            flat = self._flattenJson(processed)
            for k, v in flat.items():
                if not self._eligibleBySchema(k, schema):
                    continue
                if isinstance(v, str) and v.strip():
                    pairList.append((k, v.strip()))
                    chunkMap.append(chunkId)
        if not pairList:
            raise ValueError("Không tìm thấy nội dung văn bản hợp lệ để encode.")
        pairList, chunkGroups = self.deduplicatesWithMask(pairList, chunkMap)
        keys = [k for k, _ in pairList]
        texts = [t for _, t in pairList]
        embsT = self._encodeTexts(texts)
        embs = embsT.detach().cpu().numpy()
        if self.normalize:
            embs = self._l2Normalize(embs)
        faissIndex = self._createFaissIndex(embs)
        indexToKey = {str(i): k for i, k in enumerate(keys)}
        mapping = {
            "meta": {
                "count": len(keys),
                "dim": int(embs.shape[1]),
                "metric": "ip",
                "normalized": bool(self.normalize),
            },
            "index_to_key": indexToKey,
        }
        mapData = {
            "items": [{"index": i, "key": k, "text": t} for i, (k, t) in enumerate(pairList)],
            "meta": {
                "count": len(keys),
                "flatten_mode": self.flatten_mode,
                "schema_used": schema is not None,
                "listPolicy": self.listPolicy,
            },
        }
        return faissIndex, mapping, mapData, chunkGroups

    def buildVectorsFromJson(
        self,
        segmentPath: str,
        schemaDict: Optional[Dict],
    ) -> Tuple[List[str], List[str], np.ndarray, List[List[int]]]:
        """
        Trích xuất keys, texts, embeddings và chunk_groups từ segment JSON
        (dùng cho build index PostgreSQL, không ghi file FAISS).
        """
        assert os.path.exists(segmentPath), f"Không thấy file JSON: {segmentPath}"
        schema = schemaDict
        dataObj = MyUtils.readJson(segmentPath)
        dataList = dataObj if isinstance(dataObj, list) else [dataObj]
        pairList: List[Tuple[str, str]] = []
        chunkMap: List[int] = []
        for chunkId, item in enumerate(dataList, start=1):
            processed = self._preprocessData(item)
            flat = self._flattenJson(processed)
            for k, v in flat.items():
                if not self._eligibleBySchema(k, schema):
                    continue
                if isinstance(v, str) and v.strip():
                    pairList.append((k, v.strip()))
                    chunkMap.append(chunkId)
        if not pairList:
            raise ValueError("Không tìm thấy nội dung văn bản hợp lệ để encode.")
        pairList, chunkGroups = self.deduplicatesWithMask(pairList, chunkMap)
        keys = [k for k, _ in pairList]
        texts = [t for _, t in pairList]
        embsT = self._encodeTexts(texts)
        embs = embsT.detach().cpu().numpy()
        if self.normalize:
            embs = self._l2Normalize(embs)
        return keys, texts, embs.astype("float32"), chunkGroups
