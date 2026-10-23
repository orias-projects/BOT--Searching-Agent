"""
Core services for RAG backend - PostgreSQL Vector Search only.

Vector Search Services (Runtime):
- PostgreSQL Connection Service: Connection pooling and management
- Enhanced Embedding Service: Generate full and per-field embeddings
- Vector Insert Service: Insert/update/delete records with vectors
- Vector Search Service: Priority-based semantic search
- PostgreSQL Index Manager: Index creation, optimization, monitoring

Setup/Data Processing (in scripts/):
- PDF extract/merge/quality check services (scripts/data_processing/)
- JSON chunking services (scripts/json_processing/)
- PostgreSQL Schema Manager (scripts/db_tools/)
- Text processing utilities (scripts/)
- FAISS and SQLite Vector Store (scripts/legacy_faiss/)
"""

# Vector Search Services
from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService
from src.backends.core.services.enhancedEmbedding import EnhancedEmbeddingService
from src.backends.core.services.pgVectorInsert import VectorInsertService
from src.backends.core.services.pgVectorSearch import PriorityVectorSearchService
from src.backends.core.services.pgIndexManager import PostgreSQLIndexManager

__all__ = [
    # PostgreSQL Vector Search
    "PostgreSQLConnectionService",
    "EnhancedEmbeddingService",
    "VectorInsertService",
    "PriorityVectorSearchService",
    "PostgreSQLIndexManager",
]
