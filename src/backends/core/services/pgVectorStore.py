"""
Vector store dùng PostgreSQL + pgvector: lưu embedding và tìm kiếm tương tự (cosine).
Tương thích format kết quả với FAISS (index, key, text, faissScore, chunkIDs).
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger(__name__)

try:
    from pgvector.psycopg2 import register_vector
except ImportError:
    register_vector = None


class PGVectorStore:
    """
    Lưu và tìm kiếm vector trong PostgreSQL (extension pgvector).
    Một bảng dùng cột index_name để phân tách index chính vs index service (Categories).
    """

    TABLE_NAME = "embeddings"
    INDEX_MAIN = "default"

    def __init__(
        self,
        connection_string: str,
        index_name: str = INDEX_MAIN,
        dimension: int = 768,
        table_name: str = TABLE_NAME,
    ) -> None:
        if not connection_string or not connection_string.strip():
            raise ValueError("connection_string không được rỗng")
        if register_vector is None:
            raise ImportError("Cần cài pgvector: pip install pgvector")
        self._connection_string = connection_string.strip()
        self._index_name = index_name
        self._dimension = dimension
        self._table_name = table_name
        self._conn: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> psycopg2.extensions.connection:
        if self._conn is not None and not self._conn.closed:
            return self._conn
        self._conn = psycopg2.connect(self._connection_string)
        register_vector(self._conn)
        return self._conn

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning("Đóng kết nối PG: %s", e)
            self._conn = None

    def ensure_extension_and_table(self) -> None:
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    id BIGSERIAL PRIMARY KEY,
                    index_name VARCHAR(128) NOT NULL,
                    key TEXT,
                    text TEXT NOT NULL,
                    chunk_ids JSONB NOT NULL DEFAULT '[]',
                    embedding vector({self._dimension}) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{self._table_name}_index_name "
                f"ON {self._table_name} (index_name)"
            )
        conn.commit()

    def delete_index(self) -> None:
        """Xóa toàn bộ bản ghi của index_name hiện tại (để build lại)."""
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self._table_name} WHERE index_name = %s",
                (self._index_name,),
            )
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
        chunk_ids_json = [json.dumps(ids) for ids in chunk_ids_per_row]
        emb_list = np.asarray(embeddings, dtype="float32")
        rows = [
            (self._index_name, k, t, cids, emb_list[i])
            for i, (k, t, cids) in enumerate(zip(keys, texts, chunk_ids_json))
        ]
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO {self._table_name} (index_name, key, text, chunk_ids, embedding)
                VALUES %s
                """,
                rows,
                template="(%s, %s, %s, %s::jsonb, %s)",
                page_size=500,
            )
        conn.commit()

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm theo cosine similarity (embedding đã chuẩn hóa L2).
        Trả về format giống FAISS: index, key, text, faissScore, chunkIDs.
        """
        conn = self.connect()
        q = np.asarray(query_embedding, dtype="float32")
        if q.ndim == 2:
            q = q[0]
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, key, text, chunk_ids,
                       1 - (embedding <=> %s) AS score
                FROM {self._table_name}
                WHERE index_name = %s
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (q, self._index_name, q, top_k),
            )
            rows = cur.fetchall()
        results = []
        for idx, (pg_id, key, text, chunk_ids_json, score) in enumerate(rows):
            chunk_ids = json.loads(chunk_ids_json) if isinstance(chunk_ids_json, str) else (chunk_ids_json or [])
            results.append({
                "index": pg_id,
                "key": key,
                "text": text,
                "faissScore": float(score),
                "chunkIDs": chunk_ids,
            })
        return results

    def count(self) -> int:
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) FROM {self._table_name} WHERE index_name = %s",
                (self._index_name,),
            )
            return cur.fetchone()[0]

    def __enter__(self) -> "PGVectorStore":
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
