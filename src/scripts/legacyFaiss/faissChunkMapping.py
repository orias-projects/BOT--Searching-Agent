"""
Chunk mapping: extract chunks from reranked results, filter fields, collect text.
"""
from typing import Any, Dict, Iterable, List, Optional


def _orderedUniqueChunkIDs(reranked: List[Dict[str, Any]]) -> List[int]:
    seen, ordered = set(), []
    for r in reranked:
        for cid in r.get("chunkIDs", []):
            if isinstance(cid, (int, str)) and str(cid).isdigit():
                cid = int(cid)
                if cid not in seen:
                    seen.add(cid)
                    ordered.append(cid)
    return ordered


def _filterFieldsRecursive(obj: Any, dropLower: set) -> Any:
    if isinstance(obj, dict):
        return {
            k: _filterFieldsRecursive(v, dropLower)
            for k, v in obj.items()
            if k.lower() not in dropLower
        }
    if isinstance(obj, list):
        return [_filterFieldsRecursive(x, dropLower) for x in obj]
    return obj


def _iterValuesNoKeys(obj: Any) -> Iterable[str]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iterValuesNoKeys(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iterValuesNoKeys(item)
    elif isinstance(obj, str):
        for line in obj.splitlines():
            yield line
    else:
        yield str(obj)


def _getByPath(obj: Any, path: str) -> Any:
    parts = path.split(".")

    def _step(o, idx=0):
        if idx == len(parts):
            return o
        key = parts[idx]
        if isinstance(o, dict):
            if key not in o:
                return None
            return _step(o[key], idx + 1)
        if isinstance(o, list):
            collected = [_step(it, idx) for it in o]
            flat = []
            for v in collected:
                if v is None:
                    continue
                if isinstance(v, list):
                    flat.extend(v)
                else:
                    flat.append(v)
            return flat
        return None

    return _step(obj, 0)


def extractChunks(
    reranked: List[Dict[str, Any]],
    segmentDict: List[Dict[str, Any]],
    nChunks: Optional[int] = None,
    dropFields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not reranked:
        return []
    orderedIds = _orderedUniqueChunkIDs(reranked)
    if nChunks is not None:
        orderedIds = orderedIds[: int(nChunks)]
    dropLower = set(x.lower() for x in (dropFields or []))
    out = []
    seen = set()
    for cid in orderedIds:
        if cid in seen:
            continue
        seen.add(cid)
        if 1 <= cid <= len(segmentDict):
            data = segmentDict[cid - 1]
            filtered = _filterFieldsRecursive(data, dropLower) if dropLower else data
            out.append({"chunk_id": cid, "data": filtered})
    return out


def collectChunkText(chunks: List[Dict[str, Any]]) -> str:
    if not chunks:
        return "(Không có chunk nào)"
    lines = []
    for ch in chunks:
        for line in _iterValuesNoKeys(ch["data"]):
            lines.append(line)
        lines.append("")
    return "\n".join(lines).strip()


def extractFields(
    chunks: List[Dict[str, Any]],
    fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    results = []
    for ch in chunks:
        data = ch["data"]
        if not isinstance(data, dict):
            results.append({"chunk_id": ch["chunk_id"], "fields": data})
            continue
        if fields is None:
            payload = dict(data)
        else:
            payload = {f: _getByPath(data, f) for f in fields}
        results.append({"chunk_id": ch["chunk_id"], "fields": payload})
    return results


def processChunksPipeline(
    reranked: List[Dict[str, Any]],
    segmentDict: List[Dict[str, Any]],
    dropFields: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    nChunks: Optional[int] = None,
) -> Dict[str, Any]:
    chunksJson = extractChunks(
        reranked=reranked,
        segmentDict=segmentDict,
        nChunks=nChunks,
        dropFields=dropFields,
    )
    chunksText = collectChunkText(chunksJson)
    extractedFields = extractFields(chunksJson, fields=fields)
    return {
        "chunksJson": chunksJson,
        "chunksText": chunksText,
        "extractedFields": extractedFields,
    }
