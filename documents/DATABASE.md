# Database Documentation

## Overview

Hệ thống sử dụng **PostgreSQL 16** với extension **pgvector 0.8.2** cho vector similarity search.

---

## Connection

### Connection String

```
postgresql://postgres:PASSWORD@localhost:5432/rag_vectors
```

### Environment Variables

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=your_password
```

---

## Extensions

| Extension | Version | Purpose |
|-----------|---------|---------|
| `vector` | 0.8.2 | Vector similarity search |
| `uuid-ossp` | 1.1 | UUID generation |
| `pg_trgm` | 1.6 | Trigram text search (optional) |
| `unaccent` | 1.1 | Remove accents (optional) |

### Enable Extensions

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

---

## Tables

### Schema Overview

Tất cả 5 tables có cấu trúc giống nhau, khác nhau về mục đích sử dụng và priority trong search.

```sql
CREATE TABLE IF NOT EXISTS <table_name> (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category JSONB,                    -- Phân loại/tags
    context JSONB NOT NULL,            -- Nội dung chính
    vectors JSONB,                     -- Subvectors per field
    vector VECTOR(768),                -- Main embedding vector
    metadata JSONB,                    -- Additional metadata
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table Descriptions

#### 1. `bases` (Priority: Highest)

**Purpose:** System knowledge base - kiến thức cốt lõi của hệ thống.

**Use case:** FAQ chính thức, thông tin quan trọng cần ưu tiên.

**Threshold:** 0.7 (nếu match >= 0.7, trả về ngay không search tiếp).

```sql
-- Example data
INSERT INTO bases (context, category) VALUES (
    '{"question": "Giờ làm việc của thư viện?", "answer": "Thư viện mở cửa từ 7h-21h"}',
    '{"topic": "facilities", "verified": true}'
);
```

#### 2. `answers` (Priority: +0.03)

**Purpose:** Q&A do team phát triển tạo ra.

**Use case:** Câu trả lời đã được kiểm duyệt bởi experts.

```sql
INSERT INTO answers (context, metadata) VALUES (
    '{"question": "Cách đăng ký học phần", "answer": "Đăng nhập portal..."}',
    '{"author": "admin", "created_date": "2024-01-15"}'
);
```

#### 3. `crawls` (Priority: +0.02)

**Purpose:** Q&A crawl từ diễn đàn, forums.

**Use case:** Dữ liệu từ nguồn bên ngoài (Stack Overflow, forums, etc.)

```sql
INSERT INTO crawls (context, metadata) VALUES (
    '{"question": "Lỗi khi đăng ký", "answer": "Thử xóa cache..."}',
    '{"source_url": "https://forum.example.com/...", "crawled_at": "2024-01-10"}'
);
```

#### 4. `respons` (Priority: +0.01)

**Purpose:** Q&A từ phản hồi của users/testers.

**Use case:** Feedback loop, continuous improvement.

```sql
INSERT INTO respons (context, metadata) VALUES (
    '{"question": "Câu hỏi từ user", "answer": "Trả lời sau khi verify"}',
    '{"user_id": "user123", "feedback_type": "question"}'
);
```

#### 5. `chunks` (Priority: +0.00)

**Purpose:** Document chunks từ PDFs, docs.

**Use case:** Tài liệu dài được chia nhỏ để search.

```sql
INSERT INTO chunks (context, metadata) VALUES (
    '{"text": "Nội dung đoạn văn...", "document_id": "doc123"}',
    '{"page": 5, "chunk_index": 2, "total_chunks": 50}'
);
```

---

## Indexes

### Vector Index (HNSW)

```sql
-- Sử dụng HNSW cho fast approximate nearest neighbor search
CREATE INDEX idx_<table>_vector ON <table> 
    USING hnsw (vector vector_cosine_ops);
```

**HNSW Parameters:**
- `m`: Số connections per layer (default: 16)
- `ef_construction`: Size of dynamic candidate list (default: 64)

### When to use IVFFlat vs HNSW

| Aspect | HNSW | IVFFlat |
|--------|------|---------|
| Speed | Faster | Slower |
| Memory | Higher | Lower |
| Accuracy | Higher | Lower |
| Build time | Slower | Faster |
| Updates | Good | Need rebuild |
| Best for | < 10M vectors | > 10M vectors |

---

## Queries

### Basic Vector Search

```sql
-- Tìm top 5 records gần nhất với query vector
SELECT 
    id,
    context,
    1 - (vector <=> '[0.1, 0.2, ...]'::vector) AS similarity
FROM bases
WHERE vector IS NOT NULL
ORDER BY vector <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;
```

### Priority-based Search

```sql
-- Search với priority scoring
WITH search_results AS (
    SELECT 
        id,
        'bases' as table_name,
        context,
        1 - (vector <=> $1::vector) as similarity,
        0.0 as priority_bonus
    FROM bases
    WHERE vector IS NOT NULL
    
    UNION ALL
    
    SELECT 
        id,
        'answers',
        context,
        1 - (vector <=> $1::vector),
        0.03
    FROM answers
    WHERE vector IS NOT NULL
)
SELECT 
    *,
    similarity + priority_bonus as adjusted_score
FROM search_results
WHERE similarity >= 0.5
ORDER BY adjusted_score DESC
LIMIT 10;
```

### Count Records

```sql
SELECT 
    'bases' as table_name, COUNT(*) FROM bases
UNION ALL
SELECT 'answers', COUNT(*) FROM answers
UNION ALL
SELECT 'chunks', COUNT(*) FROM chunks;
```

### JSONB Queries

```sql
-- Tìm theo category
SELECT * FROM bases 
WHERE category @> '{"topic": "academic"}';

-- Tìm trong context
SELECT * FROM answers 
WHERE context->>'question' ILIKE '%đăng ký%';
```

---

## Maintenance

### Vacuum & Analyze

```sql
-- Chạy định kỳ (hàng tuần)
VACUUM ANALYZE bases;
VACUUM ANALYZE answers;
VACUUM ANALYZE chunks;
```

### Reindex

```sql
-- Khi index bị fragmented
REINDEX INDEX idx_bases_vector;
```

### Check Table Size

```sql
SELECT 
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Check Index Usage

```sql
SELECT 
    indexrelname as index_name,
    idx_scan as times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public';
```

---

## Backup & Restore

### Backup

```bash
# Full backup
pg_dump -U postgres -d rag_vectors -F c -f backup.dump

# Schema only
pg_dump -U postgres -d rag_vectors --schema-only -f schema.sql

# Data only
pg_dump -U postgres -d rag_vectors --data-only -f data.sql
```

### Restore

```bash
# Restore full backup
pg_restore -U postgres -d rag_vectors -c backup.dump

# Restore from SQL
psql -U postgres -d rag_vectors -f schema.sql
psql -U postgres -d rag_vectors -f data.sql
```

---

## Performance Tips

1. **Connection Pooling**: Sử dụng pool size 10-20 connections
2. **Batch Inserts**: Insert nhiều records cùng lúc (100-500 per batch)
3. **Index Maintenance**: VACUUM ANALYZE sau khi insert lớn
4. **Query Optimization**: Sử dụng EXPLAIN ANALYZE để debug
5. **Memory Settings**: Tăng `shared_buffers` và `work_mem` cho datasets lớn

```sql
-- Check slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```
