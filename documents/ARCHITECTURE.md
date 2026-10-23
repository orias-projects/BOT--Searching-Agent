# Kiến trúc Hệ thống

## Tổng quan

RAG System được thiết kế theo kiến trúc **Modular Monolith**, cho phép tách biệt các concerns nhưng vẫn deploy như một ứng dụng đơn.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                   │
│                    (Browser / API Consumer)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         WEB_API                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Routes    │  │ Middlewares │  │   Request Validation    │  │
│  │  (FastAPI)  │  │   (CORS)    │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          CORE                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │    Services     │  │    Usecases     │  │   LLM Services  │  │
│  │ (pgVectorSearch │  │  (pipelines)    │  │  (summarizer)   │  │
│  │  pgVectorInsert)│  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────────┐
│       DATABASE            │   │       DATA_PIPELINE           │
│  ┌─────────────────────┐  │   │  ┌─────────────────────────┐  │
│  │  Connection Pool    │  │   │  │  Extractors (PDF)       │  │
│  │  (pgConnectionSvc)  │  │   │  └─────────────────────────┘  │
│  └─────────────────────┘  │   │  ┌─────────────────────────┐  │
│  ┌─────────────────────┐  │   │  │  Processors (Chunking)  │  │
│  │   Schema Manager    │  │   │  └─────────────────────────┘  │
│  └─────────────────────┘  │   │  ┌─────────────────────────┐  │
│  ┌─────────────────────┐  │   │  │  Loaders (DB Upload)    │  │
│  │   PostgreSQL +      │  │   │  └─────────────────────────┘  │
│  │   pgvector          │  │   │                               │
│  └─────────────────────┘  │   └───────────────────────────────┘
└───────────────────────────┘
```

---

## Modules Chi tiết

### 1. DATA_PIPELINE

Xử lý dữ liệu từ raw documents đến vector embeddings.

```
data_pipeline/
├── extractors/          # Trích xuất dữ liệu từ files
│   ├── pdfExtractData.py    # Đọc PDF, trích xuất text
│   ├── pdfMergeData.py      # Gộp dữ liệu từ nhiều sources
│   ├── pdfQualityCheck.py   # Kiểm tra chất lượng extraction
│   └── commonPdfProcess.py  # Utilities cho PDF
│
├── processors/          # Xử lý và chunking text
│   ├── jsonChunkMaster.py   # Chunking chính
│   ├── jsonChunkUnder.py    # Sub-chunking
│   ├── jsonGetStructures.py # Phân tích cấu trúc
│   └── jsonSchemaExt.py     # Schema extraction
│
└── loaders/             # Load data vào database
    ├── upload_to_db.py      # Upload vectors
    ├── init_db.py           # Khởi tạo database
    └── migrate_faiss.py     # Migrate từ FAISS
```

**Flow xử lý:**
```
PDF → Extract → Chunk → Embed → Store in pgvector
```

### 2. WEB_API

API Gateway cho external access.

```
web_api/
├── routes/
│   ├── app.py              # FastAPI application
│   ├── vector_api.py       # Vector search endpoints
│   └── vector_endpoints.py # Additional endpoints
│
└── middlewares/
    └── __init__.py         # CORS, Auth, Logging
```

**Endpoints chính:**
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/search` | Tìm kiếm vector |
| POST | `/api/v1/insert` | Insert vector mới |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/tables/{name}/count` | Đếm records |

### 3. CORE

Business logic và services.

```
core/
├── services/            # Database services
│   ├── pgConnectionService.py   # Connection pool
│   ├── pgVectorSearch.py        # Priority-based search
│   ├── pgVectorInsert.py        # Batch insert
│   ├── pgVectorStore.py         # Vector store interface
│   ├── pgIndexManager.py        # Index management
│   ├── pgMonitoringService.py   # Monitoring
│   └── enhancedEmbedding.py     # Embedding service
│
├── usecases/            # Business pipelines
│   └── pipelines.py     # RAG pipelines
│
├── llm/                 # LLM integration
│   └── summarizerRunner.py
│
├── legacy/              # Legacy FAISS support
│   ├── faissEmbedding.py
│   ├── faissSearching.py
│   └── sqliteVectorStore.py
│
└── infra/               # Infrastructure
    └── model_loader.py  # Model loading utilities
```

### 4. DATABASE

Database schema và management.

```
database/
├── sql/                 # SQL files
│   ├── extension.sql    # Enable extensions
│   ├── schema.sql       # Table definitions
│   └── index.sql        # Index definitions
│
├── tools/               # Management tools
│   └── pgSchemaManager.py
│
├── models/              # Data models
│
└── docker-compose.yml   # PostgreSQL container
```

### 5. CONFIGS

Cấu hình hệ thống.

```
configs/
├── settings.py          # Python settings (từ .env)
└── configs.json         # Static configuration
```

---

## Data Flow

### Search Flow

```
1. User Query
   │
   ▼
2. Embedding Service (PhoBERT)
   │ Chuyển query thành vector 768 dimensions
   ▼
3. Priority Vector Search
   │ Tìm trong 5 tables với priority scoring:
   │ - bases:   +0.00 (highest, threshold 0.7)
   │ - answers: +0.03
   │ - crawls:  +0.02
   │ - respons: +0.01
   │ - chunks:  +0.00
   ▼
4. Result Ranking
   │ adjusted_score = cosine_similarity + priority_bonus
   ▼
5. Return Top-K Results
```

### Insert Flow

```
1. JSON Data Input
   │
   ▼
2. Field Extraction
   │ Trích xuất các fields cần embed
   ▼
3. Embedding Generation
   │ Tạo vector cho mỗi field (subvectors)
   │ Tạo combined vector (main vector)
   ▼
4. Batch Insert
   │ INSERT INTO table (context, vector, vectors, ...)
   ▼
5. Index Update
   │ HNSW index tự động cập nhật
```

---

## Database Schema

### Tables

| Table | Priority | Use Case |
|-------|----------|----------|
| `bases` | Highest | System knowledge base |
| `answers` | +0.03 | Dev team Q&A |
| `crawls` | +0.02 | Crawled forum data |
| `respons` | +0.01 | User feedback |
| `chunks` | Base | Document chunks |

### Columns (Common)

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
category JSONB           -- Phân loại
context JSONB NOT NULL   -- Nội dung chính
vectors JSONB            -- Subvectors per field
vector VECTOR(768)       -- Main embedding
metadata JSONB           -- Additional metadata
created_at TIMESTAMP
```

### Indexes

- **HNSW Index**: Cho vector similarity search (cosine)
- **GIN Index**: Cho JSONB queries (tùy chọn)

---

## Scalability Considerations

### Hiện tại (Monolith)
- Single process, multiple workers
- Connection pooling (10-15 connections)
- Suitable for < 1M vectors

### Tương lai (Microservices)
- Tách `data_pipeline` thành worker service
- Tách `web_api` thành API gateway
- Sử dụng message queue (Redis/RabbitMQ)
- Horizontal scaling với load balancer
