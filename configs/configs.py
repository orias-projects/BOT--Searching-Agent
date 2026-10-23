"""
Config values: paths and model names.
Paths aligned with project structure (STRUCTURE.md).
"""
import logging
import os

import faiss
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_USE_CUDA_DSA"] = "1"


def _database_url_from_env() -> str:
    """Lấy connection string từ biến môi trường. Không hardcode mật khẩu."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url.strip()
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "rag_vectors")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    if not password:
        return ""
    from urllib.parse import quote_plus
    safe_password = quote_plus(password)
    return f"postgresql://{user}:{safe_password}@{host}:{port}/{name}"


class AppConfig:
    """
    Cấu hình ứng dụng: đường dẫn, model, và (tùy chọn) PostgreSQL / SQLite vector DB.
    Paths relative to project root (STRUCTURE.md).
    """

    def __init__(self, pdfname: str = "HNMU") -> None:
        assets_folder = "assets/resources"
        data_folder = "databases/jsons"
        pdf_folder = "uploads/pdfs"
        models_folder = "models/resource"

        self._data: dict = {
            "pdfPath": f"{pdf_folder}/{pdfname}.pdf",
            "exceptPath": f"{assets_folder}/ex.exceptions.json",
            "markerPath": f"{assets_folder}/ex.markers.json",
            "statusPath": f"{assets_folder}/ex.status.json",
            "rawDataPath": f"{data_folder}/{pdfname}/{pdfname}_Extract_Raw.json",
            "rawLvlsPath": f"{data_folder}/{pdfname}/{pdfname}_Extract_Levels.json",
            "structsPath": f"{data_folder}/{pdfname}/{pdfname}_Chunks_Struct.json",
            "segmentPath": f"{data_folder}/{pdfname}/{pdfname}_Chunks_Segment.json",
            "schemaPath": f"{data_folder}/{pdfname}/{pdfname}_Chunks_Schema.json",
            "faissPath": f"{data_folder}/{pdfname}/{pdfname}_Embedding_Index.faiss",
            "mappingPath": f"{data_folder}/{pdfname}/{pdfname}_Embedding_Mapping.json",
            "mapDataPath": f"{data_folder}/{pdfname}/{pdfname}_Embedding_MapData.json",
            "mapChunkPath": f"{data_folder}/{pdfname}/{pdfname}_Embedding_MapChunk.json",
            "metaPath": f"{data_folder}/{pdfname}/{pdfname}_Embedding_Meta.json",
            "DATA_KEY": "contents",
            "EMBE_KEY": "embeddings",
            "SEARCH_EGINE": faiss.IndexFlatIP,
            "RERANK_MODEL": "BAAI/bge-reranker-base",
            "CHUNKS_MODEL": "paraphrase-multilingual-MiniLM-L12-v2",
            "EMBEDD_MODEL": "VoVanPhuc/sup-SimCSE-VietNamese-phobert-base",
            "RESPON_MODEL": "gpt-3.5-turbo",
            "SUMARY_MODEL": "LongK171/bartpho-syllable-vnexpress",
            "WORD_LIMIT": 1000,
            "modelsFolder": models_folder,
            "databaseUrl": _database_url_from_env(),
            "usePgVector": os.environ.get("USE_PG_VECTOR", "0").strip().lower() in ("1", "true", "yes"),
            "sqliteDbPath": os.environ.get("SQLITE_DB_PATH", "databases/vectors/rag_vectors.db").strip(),
            "useSqliteVector": os.environ.get("USE_SQLITE_VECTOR", "0").strip().lower() in ("1", "true", "yes"),
            "embeddingDim": int(os.environ.get("EMBEDDING_DIM", "768")),
        }

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key: str):
        return self._data[key]


def ConfigValues(pdfname: str = "HNMU") -> AppConfig:
    """Factory: trả về instance AppConfig (tương thích code cũ)."""
    return AppConfig(pdfname=pdfname)
