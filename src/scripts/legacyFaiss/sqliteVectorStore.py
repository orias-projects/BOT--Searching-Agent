"""
Vector store dùng SQLite + sqlite-vec: lưu embedding và tìm kiếm tương tự (cosine).
Tương thích format kết quả với FAISS (index, key, text, faissScore, chunkIDs).
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import sqlite3
    import sqlite_vec
except ImportError:
    sqlite_vec = None


class SQLiteVectorStore:
    """
    Lưu và tìm kiếm vector trong SQLite (extension sqlite-vec).
    Một bảng dùng cột index_name (partition key) để phân tách index chính vs service (Categories).
    """

    INDEX_MAIN = "default"
    INDEX_SERVICE = "Categories"
    _TABLE_PREFIX = "vec_"

    def __init__(
        self,
        db_path: str,
        index_name: str = INDEX_MAIN,
        dimension: int = 768,
    ) -> None:
        if not db_path or not db_path.strip():
            raise ValueError("db_path không được rỗng")
        if sqlite_vec is None:
            raise ImportError("Cần cài sqlite-vec: pip install sqlite-vec")
        self._db_path = os.path.abspath(db_path.strip())
        self._index_name = index_name
        self._dimension = dimension
        safe_name = index_name.replace(" ", "_").replace("-", "_")
        self._table_name = f"{self._TABLE_PREFIX}{safe_name}"
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._conn.enable_load_extension(False)
        self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning("Đóng kết nối SQLite: %s", e)
            self._conn = None

    def ensure_extension_and_table(self) -> None:
        conn = self.connect()
        conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {self._table_name} USING vec0(
                embedding float[{self._dimension}] distance_metric=cosine,
                +key text,
                +content text,
                +chunk_ids text
            )
            """
        )
        conn.commit()

    def delete_index(self) -> None:
        """Xóa toàn bộ bản ghi (để build lại)."""
        conn = self.connect()
        conn.execute(f"DELETE FROM {self._table_name}")
        conn.commit()

    def insert_batch(
        self,
        keys: List[str],
        texts: List[str],
        embeddings: np.ndarray,
        chunk_ids_per_row: List[List[int]],
    ) -> None:
        if not keys or len(keys) != len(texts) != embeddings.shape[0] != len(chunk_ids_per_row):
            raise ValueError("keys, texts, embeddings, chunk_ids_per_row phải cùng độ dài")
        conn = self.connect()
        emb_arr = np.asarray(embeddings, dtype="float32")
        with conn:
            for i, (k, t, cids) in enumerate(zip(keys, texts, chunk_ids_per_row)):
                emb_blob = emb_arr[i].tobytes()
                chunk_ids_str = json.dumps(cids)
                conn.execute(
                    f"""
                    INSERT INTO {self._table_name}(embedding, key, content, chunk_ids)
                    VALUES (?, ?, ?, ?)
                    """,
                    (emb_blob, k or "", t or "", chunk_ids_str),
                )
        conn.commit()

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm theo cosine distance (sqlite-vec distance_metric=cosine).
        Trả về format giống FAISS: index, key, text, faissScore, chunkIDs.
        Với cosine distance, nhỏ hơn = giống hơn; dùng 1 - distance làm score.
        """
        conn = self.connect()
        q = np.asarray(query_embedding, dtype="float32")
        if q.ndim == 2:
            q = q[0]
        q_blob = q.tobytes()
        cur = conn.execute(
            f"""
            SELECT rowid, key, content, chunk_ids, distance
            FROM {self._table_name}
            WHERE embedding MATCH ? AND k = ?
            ORDER BY distance
            """,
            (q_blob, top_k),
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            rowid = row[0]
            key = row[1] or ""
            content = row[2] or ""
            chunk_ids_raw = row[3]
            distance = float(row[4])
            try:
                chunk_ids = json.loads(chunk_ids_raw) if chunk_ids_raw else []
            except Exception:
                chunk_ids = []
            score = max(0.0, 1.0 - distance)
            results.append({
                "index": rowid,
                "key": key,
                "text": content,
                "faissScore": score,
                "chunkIDs": chunk_ids,
            })
        return results

    def count(self) -> int:
        conn = self.connect()
        cur = conn.execute(f"SELECT COUNT(*) FROM {self._table_name}")
        return cur.fetchone()[0]

    def __enter__(self) -> "SQLiteVectorStore":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
