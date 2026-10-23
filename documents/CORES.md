# PostgreSQL Vector Search - Core Services Guide

## 📚 Overview

The core services implement the complete PostgreSQL + pgvector backend for semantic search with priority-based ranking and subvector support.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              API Layer (FastAPI)                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐        ┌──────────────────┐      │
│  │  Search API      │        │  Insert API      │      │
│  │  /vector-search  │        │  /vector-data    │      │
│  └────────┬─────────┘        └────────┬─────────┘      │
│           │                            │                 │
├─────────────────────────────────────────────────────────┤
│                   Core Services Layer                    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  PriorityVectorSearchService                   │    │
│  │  - 3-stage search algorithm                    │    │
│  │  - Subvector matching                          │    │
│  │  - Priority scoring                            │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  VectorInsertService                           │    │
│  │  - Insert records with full + subvectors      │    │
│  │  - Batch operations                            │    │
│  │  - Update/delete/get operations                │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌───────────────────────┬──────────────────┐          │
│  │ EnhancedEmbedding     │ PostgreSQLSchema │          │
│  │ Service              │ Manager          │          │
│  │ - Full embedding     │ - Table setup    │          │
│  │ - Subvectors         │ - Verification   │          │
│  │ - Batch processing   │ - Maintenance    │          │
│  └───────────────────────┴──────────────────┘          │
│                                                          │
│  ┌───────────────────────────────────────────────┐     │
│  │  PostgreSQLIndexManager                       │     │
│  │  - Index creation (IVFFlat/HNSW)            │     │
│  │  - Index optimization                        │     │
│  │  - Performance tuning                        │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
│  ┌───────────────────────────────────────────────┐     │
│  │  PostgreSQLConnectionService                 │     │
│  │  - Connection pooling                        │     │
│  │  - Transaction management                    │     │
│  │  - Health checks                             │     │
│  └───────────────────────────────────────────────┘     │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                 Database Layer                          │
│                                                          │
│  PostgreSQL + pgvector                                 │
│  ├─ 5 Priority-based tables                            │
│  ├─ UUID keys                                          │
│  ├─ VECTOR(768) with indexes                          │
│  ├─ JSONB for flexible data storage                   │
│  └─ Subvectors for field-level search                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Initialize Database Schema

```bash
# Run initialization script
python scripts/init_database.py --init

# Verify schema was created correctly
python scripts/init_database.py --verify

# Check health
python scripts/init_database.py --health
```

### 2. Use Services in Code

```python
from src.backends.core.services import (
    PostgreSQLConnectionService,
    PostgreSQLSchemaManager,
    EnhancedEmbeddingService,
    VectorInsertService,
    PriorityVectorSearchService,
)

# Initialize connection
connection_service = PostgreSQLConnectionService()

# Initialize schema manager
schema_manager = PostgreSQLSchemaManager(connection_service)
schema_manager.install_pgvector_extension()
schema_manager.create_all_tables()

# Initialize embedding service
embedding_service = EnhancedEmbeddingService(
    model_name="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base"
)

# Insert data
insert_service = VectorInsertService(embedding_service, connection_service)
record_id = insert_service.insert_record(
    table_name="answers",
    json_data={
        "question": "Làm thế nào để cài đặt Python?",
        "answer": "Tải từ python.org và cài đặt...",
        "topic": "Installation"
    },
    metadata={"author": "dev_team", "verified": True}
)

# Search
search_service = PriorityVectorSearchService(embedding_service, connection_service)
result = search_service.search("cách cài Python?")
print(result)
```

## 📖 Service Documentation

### PostgreSQLConnectionService

**Purpose**: Manage database connections with connection pooling

**Key Methods**:
- `get_connection()` - Get connection from pool
- `get_cursor()` - Get cursor with auto-commit
- `execute_query()` - Execute query and fetch results
- `execute_many()` - Batch execute
- `check_health()` - Health check
- `close()` - Close pool

**Example**:
```python
service = PostgreSQLConnectionService()

# Single query
result = service.execute_query(
    "SELECT * FROM bases WHERE id = %s",
    (record_id,),
    fetch="one"
)

# Batch insert
service.execute_many(
    "INSERT INTO answers (id, vectors, jsons, subvectors, metadata) VALUES (%s, %s, %s, %s, %s)",
    [
        (id1, vec1, json1, subvec1, meta1),
        (id2, vec2, json2, subvec2, meta2),
    ]
)
```

### EnhancedEmbeddingService

**Purpose**: Generate full and per-field embeddings for semantic search

**Key Methods**:
- `embed_text()` - Embed single or multiple texts
- `generate_full_embedding()` - Embed entire JSON document
- `generate_subvectors()` - Generate per-field embeddings
- `prepare_record()` - Generate both full + subvector embeddings
- `prepare_batch()` - Batch prepare multiple records
- `normalize_json_to_text()` - Flatten JSON to text

**Model**: `VoVanPhuc/sup-SimCSE-VietNamese-phobert-base` (768-dim)

**Example**:
```python
embedding_service = EnhancedEmbeddingService()

# Single text
vector = embedding_service.embed_text("Xin chào")  # (768,)

# Multiple texts
vectors = embedding_service.embed_text(["Xin chào", "Tạm biệt"])  # (2, 768)

# Prepare record with full + subvectors
json_data = {
    "question": "Python là gì?",
    "answer": "Python là ngôn ngữ lập trình...",
    "topic": "Programming"
}
full_vector, subvectors = embedding_service.prepare_record(json_data)
# full_vector: (768,) - embedding of entire JSON
# subvectors: {"question": [...], "answer": [...], "topic": [...]}
```

### PostgreSQLSchemaManager

**Purpose**: Create, verify, and maintain database schema

**Key Methods**:
- `install_pgvector_extension()` - Install pgvector in database
- `create_table()` - Create single table
- `create_all_tables()` - Create all 5 tables
- `verify_table_schema()` - Verify table columns and constraints
- `verify_all_tables()` - Verify all tables
- `get_table_schema()` - Get column info
- `get_table_stats()` - Get row count, size
- `get_all_table_stats()` - Get stats for all tables
- `check_indexes()` - Check if indexes exist
- `generate_health_report()` - Complete health check
- `truncate_table()` - Delete all rows (keep schema)
- `reset_all_tables()` - Truncate all tables
- `drop_table()` - Drop table (destructive)
- `drop_all_tables()` - Drop all tables (destructive)

**Example**:
```python
schema_manager = PostgreSQLSchemaManager(connection_service, vector_dimension=768)

# Setup
schema_manager.install_pgvector_extension()
schema_manager.create_all_tables()

# Verify
all_valid, results = schema_manager.verify_all_tables()
for table_name, (is_valid, issues) in results.items():
    print(f"{table_name}: {'✅' if is_valid else '❌'}")
    if issues:
        for issue in issues:
            print(f"  - {issue}")

# Monitor
stats = schema_manager.get_all_table_stats()
for table_name, stat in stats.items():
    print(f"{table_name}: {stat['row_count']:,} records, {stat['total_size']}")

# Health check
report = schema_manager.generate_health_report()
print(f"Status: {'✅ Healthy' if report['tables_valid'] else '❌ Issues found'}")
```

### VectorInsertService

**Purpose**: Insert, update, delete, retrieve records with vectors

**Key Methods**:
- `insert_record()` - Insert single record
- `insert_batch()` - Batch insert multiple records
- `update_record()` - Update record (optionally regenerate vectors)
- `delete_record()` - Delete record
- `get_record()` - Get record by ID
- `get_records()` - Get multiple records
- `get_all_records()` - Get all records from table

**Example**:
```python
insert_service = VectorInsertService(embedding_service, connection_service)

# Insert single record
record_id = insert_service.insert_record(
    table_name="answers",
    json_data={
        "question": "Làm thế nào để học Python?",
        "answer": "Bắt đầu với cơ bản..."
    },
    metadata={"source": "tutorial", "difficulty": "beginner"}
)

# Batch insert (more efficient for multiple records)
record_ids = insert_service.insert_batch(
    table_name="answers",
    json_data_list=[
        {"question": "Q1", "answer": "A1"},
        {"question": "Q2", "answer": "A2"},
    ],
    metadata_list=[
        {"source": "web"},
        {"source": "guide"},
    ]
)

# Update record
insert_service.update_record(
    table_name="answers",
    record_id=record_id,
    json_data={"question": "Updated Q", "answer": "Updated A"},
    regenerate_vectors=True  # Regenerate embeddings
)

# Get record
record = insert_service.get_record("answers", record_id)
print(record["jsons"], record["final_score"])  # if search result

# Delete record
insert_service.delete_record("answers", record_id)
```

### PriorityVectorSearchService

**Purpose**: Implement 3-stage priority-based semantic search

**Algorithm**:
1. **Stage 1**: Search `bases` table with threshold 0.7 → return immediately if found
2. **Stage 2**: Search all other tables with priority bonuses
   - `answers`: +0.03
   - `crawls`: +0.02
   - `respons`: +0.01
   - `chunks`: +0.00
3. **Stage 3**: Return "not found" message

**Key Methods**:
- `search()` - Main search (3-stage algorithm)
- `search_bases()` - Stage 1 search
- `search_all_tables()` - Stage 2 search
- `search_in_table()` - Search specific table
- `_compute_subvector_similarity()` - Compute field-level similarity

**Example**:
```python
search_service = PriorityVectorSearchService(
    embedding_service,
    connection_service,
    threshold=0.7
)

# Full 3-stage search
result = search_service.search("Làm thế nào để cài Python?")

if result["success"]:
    match = result["result"]
    print(f"Found in: {match['source']}")
    print(f"Score: {match['final_score']:.2f}")
    print(f"Data: {match['data']}")
else:
    print("Not found")

# Search specific table
results = search_service.search_in_table("answers", "query")
for match in results:
    print(f"  - {match['id']}: {match['final_score']:.2f}")
```

### PostgreSQLIndexManager

**Purpose**: Create, optimize, and monitor vector indexes

**Key Methods**:
- `create_ivfflat_index()` - Create IVFFlat index (good for <1M rows)
- `create_hnsw_index()` - Create HNSW index (good for >1M rows)
- `recommend_index_type()` - Recommend type based on row count
- `recommend_lists_parameter()` - Recommend IVFFlat `lists` param
- `get_row_count()` - Get table row count
- `get_table_indexes()` - Get all indexes for table
- `get_index_info()` - Get single index info
- `get_index_stats()` - Get index usage statistics
- `reindex_index()` - Rebuild single index
- `reindex_table()` - Rebuild all indexes for table
- `analyze_table()` - Analyze table statistics
- `vacuum_table()` - Vacuum table (reclaim space)
- `generate_optimization_report()` - Get optimization recommendations

**Example**:
```python
index_manager = PostgreSQLIndexManager(connection_service)

# Create indexes
index_manager.create_ivfflat_index("answers", lists=100)
# OR for large datasets
index_manager.create_hnsw_index("answers", m=16, ef_construction=64)

# Monitor index usage
stats = index_manager.get_index_stats("idx_answers_vectors_ivfflat")
print(f"Scans: {stats['scans']}, Size: {stats['size']}")

# Get optimization recommendations
report = index_manager.generate_optimization_report()
for table, info in report["tables"].items():
    print(f"{table}: {info['row_count']} rows")
    print(f"  Recommended index: {info['recommended_index_type']}")
    if info["recommendations"]:
        for rec in info["recommendations"]:
            print(f"  💡 {rec}")

# Optimize table
index_manager.vacuum_table("answers", analyze=True)
index_manager.reindex_table("answers")
```

## 📊 Database Schema

### 5 Priority-Based Tables

Each table has the same structure but is searched with different priority bonuses:

```sql
CREATE TABLE <table_name> (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Full document embedding (768 dims)
    vectors VECTOR(768) NOT NULL,
    
    -- Original data (flexible JSON)
    jsons JSONB NOT NULL,
    
    -- Per-field embeddings
    subvectors JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Optional metadata
    metadata JSONB DEFAULT '{}'::jsonb
);
```

### Table Priorities

| Priority | Table | Bonus | Use Case |
|----------|-------|-------|----------|
| 1 (Highest) | `bases` | 0.0 | System knowledge (threshold 0.7) |
| 2 | `answers` | +0.03 | Team-created Q&A |
| 3 | `crawls` | +0.02 | Community Q&A |
| 4 | `respons` | +0.01 | User feedback |
| 5 (Lowest) | `chunks` | +0.00 | Document chunks |

### Indexes

Each table has:
- **IVFFlat vector index** on `vectors` column (cosine similarity)
- **GIN index** on `jsons` column (for JSON queries)
- **GIN index** on `metadata` column
- **B-tree index** on `created_at` (for time-based queries)

## ⚙️ Configuration

### Environment Variables

```bash
# PostgreSQL Connection
DATABASE_URL=postgresql://user:password@host:5432/rag_vectors
# OR
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=your_password

# Vector Configuration
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base
VECTOR_DIMENSION=768

# Search Parameters
SEARCH_THRESHOLD=0.7

# Connection Pool
PG_POOL_SIZE=10
PG_MAX_OVERFLOW=5

# Batch Operations
BATCH_SIZE=32
```

## 🔧 Management Commands

### Database Initialization

```bash
# Full initialization
python scripts/init_database.py --init

# Verify existing schema
python scripts/init_database.py --verify

# Health check
python scripts/init_database.py --health

# Truncate all data (keep schema)
python scripts/init_database.py --reset

# Drop all tables (destructive!)
python scripts/init_database.py --drop
```

## 📈 Performance Tuning

### IVFFlat Index Parameters

The `lists` parameter controls:
- **Fewer lists** (e.g., 10): Faster build, less accurate
- **More lists** (e.g., 1000): Slower build, more accurate

**Recommendation**:
- < 100K rows: `lists = 100`
- 100K-1M rows: `lists = √(rows/1000)`
- > 1M rows: Use HNSW index instead

### HNSW Index Parameters

- **m**: Number of bidirectional links (default 16)
  - Lower (8-12): Faster search, less memory
  - Higher (16-24): More connections, better accuracy
- **ef_construction**: Build-time parameter (default 64)
  - Higher values take longer to build but produce better indexes

### Optimization Steps

```python
# 1. Analyze table statistics
index_manager.analyze_table("answers")

# 2. Vacuum to reclaim space
index_manager.vacuum_table("answers", analyze=True)

# 3. Get recommendations
report = index_manager.generate_optimization_report()

# 4. Rebuild indexes if needed
index_manager.reindex_table("answers")
```

## 🐛 Troubleshooting

### pgvector Extension Not Installed

```bash
# Run initialization
python scripts/init_database.py --init
```

### Connection Pool Exhausted

```python
# Increase connection pool size
connection_service = PostgreSQLConnectionService(
    max_connections=20
)
```

### Slow Search Queries

```python
# Check index usage
index_manager.get_all_index_stats(["bases", "answers", "crawls"])

# Optimize indexes based on report
report = index_manager.generate_optimization_report()
```

### Schema Drift

```python
# Generate health report to identify issues
report = schema_manager.generate_health_report()

# Verify all tables
all_valid, results = schema_manager.verify_all_tables()
```

## 📚 Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and algorithm
- [API.md](./API.md) - REST API endpoints
- [SETUP.md](./SETUP.md) - Setup and deployment guide
