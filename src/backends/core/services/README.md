# Backend Core Services - PostgreSQL Vector Search

This directory contains **only** the core runtime backend services needed for the RAG API. All dataset preparation and data processing utilities have been moved to `scripts/`.

## 📁 Structure (Optimized)

### 🔌 Core Connection & State Management

#### `pg_connection_service.py`
**PostgreSQL connection pool and management**:
- Connection pooling (psycopg2)
- Connection lifecycle management
- Error handling and recovery
- Health checks

```python
from src.backends.core.services.pg_connection_service import get_connection_service

conn_service = get_connection_service()
with conn_service.get_cursor() as cursor:
    cursor.execute(...) 
```

#### `pg_monitoring_service.py`
**Database monitoring and diagnostics**:
- Table statistics
- Index health check
- Query performance metrics
- Health status reporting

### 🧠 Embedding & Vector Operations

#### `enhanced_embedding.py`
**Vector embedding generation** (primary service):
- Load embedding model (SentenceTransformer)
- Generate full JSON embeddings
- Per-field subvector generation
- Batch processing with normalization
- Multi-device support (CUDA/CPU)

```python
from src.backends.core.services.enhanced_embedding import create_embedding_service

service = create_embedding_service(model_name="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base")
full_vector, subvectors = service.prepare_record({"question": "Q", "answer": "A"})
```

### 💾 Data Insertion

#### `pg_vector_insert.py`
**Insert records with embeddings into PostgreSQL**:
- Single record insertion with vector + subvectors
- Batch insertion (efficient)
- Metadata handling
- Priority table selection (bases, answers, crawls, respons, chunks)

```python
from src.backends.core.services.pg_vector_insert import VectorInsertService

insert_service = VectorInsertService(embedding_service, conn_service)
record_id = insert_service.insert_record(
    table_name="answers",
    json_data={"question": "...", "answer": "..."},
    metadata={"author": "dev_team"}
)
```

### 🔍 Vector Search

#### `pg_vector_search.py`
**Priority-based semantic search with scoring**:
- Stage 1: Search `bases` table first (threshold 0.7)
- Stage 2: Search other tables with priority bonuses
- Subvector similarity matching
- Result ranking by combined score

```python
from src.backends.core.services.pg_vector_search import PriorityVectorSearchService

search_service = PriorityVectorSearchService(embedding_service, conn_service, threshold=0.7)
result = search_service.search(query="Cách cài Python?", top_k=5)
```

**Response Format**:
```json
{
  "query": "...",
  "results": [
    {
      "id": "uuid",
      "table": "bases|answers|crawls|respons|chunks",
      "similarity": 0.89,
      "priority_bonus": 0.03,
      "final_score": 0.92,
      "json": {...},
      "metadata": {...}
    }
  ]
}
```

### 📦 Data Access Patterns

#### `pg_vector_store.py`
**High-level store interface**:
- Unified API for insert/search/update operations
- Transaction management
- Batch operations
- Error handling

```python
from src.backends.core.services.pg_vector_store import PGVectorStore

store = PGVectorStore(embedding_service, connection_service)
inserted_ids = store.insert_batch("answers", data_list)
results = store.search("query", top_k=10)
```

### 🗂️ Index Management

#### `pg_index_manager.py`
**Index creation, validation, and maintenance**:
- IVFFlat index creation for vector similarity
- GIN indexes for JSONB queries
- Index statistics and optimization
- Index swap operations

```python
from src.backends.core.services.pg_index_manager import PostgreSQLIndexManager

index_mgr = PostgreSQLIndexManager(conn_service)
index_mgr.create_vector_index("answers", lists=100)
stats = index_mgr.get_index_stats("answers")
```

## 🎯 Architecture Principles

### 1. **Separation of Concerns**
- **Data preparation** → `scripts/` (setup-time)
- **Runtime operations** → `services/` (API-time)
- **Models & pipelines** → `src/backends/core/usecases/` (optional offline)

### 2. **Minimal Imports**
```python
# ❌ DON'T use from setup scripts
from scripts.pdf_extract_data import extractData

# ✅ DO use only core services
from src.backends.core.services.enhanced_embedding import create_embedding_service
from src.backends.core.services.pg_vector_search import PriorityVectorSearchService
```

### 3. **Connection Pooling**
All services use a **shared connection pool** for efficiency:
```python
# Get singleton connection service
conn_service = get_connection_service()

# Reuse across services
embedding_service = create_embedding_service()
insert_service = VectorInsertService(embedding_service, conn_service)
search_service = PriorityVectorSearchService(embedding_service, conn_service)
```

### 4. **Lazy Service Initialization**
Services are created on-demand (e.g., in API handlers), not at module load:

```python
# In API handler
@app.get("/search")
def search_endpoint(query: str):
    # Services initialized once per request if needed
    service = create_embedding_service()  # Cached or created
    results = search_service.search(query)
    return results
```

## 📊 Data Model

### Tables (Priority-based)
- **bases**: System knowledge (priority 0.0, threshold 0.7 immediate)
- **answers**: Dev Q&A (priority +0.03)
- **crawls**: Forum Q&A (priority +0.02)
- **respons**: User Q&A (priority +0.01)
- **chunks**: Document chunks (priority +0.00)

### Column Structure
| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `vectors` | VECTOR(768) | Full JSON embedding |
| `jsons` | JSONB | Original JSON data |
| `subvectors` | JSONB | Per-field embeddings |
| `created_at` | Timestamp | Record creation |
| `updated_at` | Timestamp | Last update |
| `metadata` | JSONB | Tags, source, author |

## 🚀 Usage Example

### Full Stack: Insert → Search

```python
from src.backends.core.services.enhanced_embedding import create_embedding_service
from src.backends.core.services.pg_connection_service import get_connection_service
from src.backends.core.services.pg_vector_insert import VectorInsertService
from src.backends.core.services.pg_vector_search import PriorityVectorSearchService

# Initialize services
embedding_srv = create_embedding_service()
conn_srv = get_connection_service()
insert_srv = VectorInsertService(embedding_srv, conn_srv)
search_srv = PriorityVectorSearchService(embedding_srv, conn_srv, threshold=0.7)

# Insert data
data = {
    "question": "Làm thế nào để cài Python?",
    "answer": "Tải từ python.org",
    "topic": "Installation"
}
record_id = insert_srv.insert_record("answers", data, metadata={"author": "team"})
print(f"Inserted: {record_id}")

# Search
results = search_srv.search("Cách cài Python", top_k=5)
for result in results:
    print(f"Score: {result['final_score']:.3f} | {result['json']}")
```

## ⚙️ Configuration

All runtime configuration is in `configs/configs.py`:
```python
USE_PG_VECTOR=true              # Enable pgvector
DATABASE_URL=postgresql://...   # Connection string
EMBEDDING_MODEL=...             # Model name (HF)
SEARCH_THRESHOLD=0.7            # Minimum similarity
VECTOR_DIMENSION=768            # Embedding dimension
```

## 🧪 Testing

Unit tests for core services:
```bash
# Test embedding service
python -m pytest test/test_vector_search.py::TestEnhancedEmbeddingService -v

# Integration test
python -m pytest test/test_integration_postgresql.py -v

# End-to-end API test
python -m pytest test/test_api_e2e.py -v
```

## 📈 Performance Notes

### Optimization Tips
1. **Batch Insert**: Use `insert_batch()` for large datasets (100+ records)
2. **Connection Pool**: Keep pool size reasonable (PG_POOL_SIZE=10)
3. **Index Tuning**: Adjust IVFFlat `lists` parameter based on dataset size
4. **Search Limit**: Use reasonable `top_k` (5-20 typically sufficient)

### Scaling
- Horizontal: Multiple API instances sharing PostgreSQL
- Vertical: Increase `PG_POOL_SIZE`, use better GPU for embeddings
- Database: Consider partitioning by priority table or time range

## 🔗 Related Files

- **API Endpoints**: `src/backends/api/v1/vector_api.py`
- **Models**: `src/backends/data/models/` (Pydantic schemas)
- **Pipelines** (Setup): `src/backends/core/usecases/pipelines.py`
- **Setup Scripts**: `scripts/` directory

---

**Last Updated**: 2026-03-31  
**Status**: ✅ Production Ready  
**Python Version**: 3.11+  
**PostgreSQL Version**: 14+ (with pgvector 0.5.1+)
