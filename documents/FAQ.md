# ❓ Frequently Asked Questions (FAQ)

Tổng hợp các câu hỏi thường gặp về hệ thống RAG.

---

## 📋 Mục lục

1. [Setup & Installation](#setup--installation)
2. [Database](#database)
3. [Vector Search](#vector-search)
4. [API & Integration](#api--integration)
5. [Performance](#performance)
6. [Troubleshooting](#troubleshooting)
7. [Development](#development)

---

## Setup & Installation

### Q: Tôi cần cài đặt những gì trước khi bắt đầu?

**A:** Bạn cần:
1. **Python 3.8+** - [Download](https://www.python.org/downloads/)
2. **PostgreSQL 12+** - [Download](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
3. **pgvector extension** - Thường đi kèm PostgreSQL hoặc cài qua Stack Builder
4. **Git** - [Download](https://git-scm.com/downloads)

Xem chi tiết: [QUICKSTART.md](QUICKSTART.md)

---

### Q: Tôi có thể dùng Python 3.7 được không?

**A:** Không khuyến nghị. Dự án yêu cầu Python 3.8+ vì:
- Type hints features (từ 3.8+)
- FastAPI requires Python 3.8+
- Một số dependencies không support 3.7

Tốt nhất dùng Python 3.9 trở lên.

---

### Q: Setup script `setup_native.ps1` báo lỗi "execution policy", làm sao?

**A:** PowerShell mặc định block scripts. Fix:

```powershell
# Option 1: Cho phép script trong session hiện tại
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Option 2: Cho phép vĩnh viễn cho user
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Sau đó chạy lại
.\setup_native.ps1
```

---

### Q: Tôi không có quyền Admin, có cài được không?

**A:** Có, nhưng:
- PostgreSQL: Cần admin để cài service. Hoặc dùng portable version
- Python: Có thể cài ở user level (tick "Install for current user only")
- Script: Chạy được không cần admin

Nếu không có admin, xem xét dùng Docker Desktop (cũng cần admin lần đầu).

---

## Database

### Q: Tại sao phải dùng PostgreSQL? Dùng SQLite/MySQL được không?

**A:** PostgreSQL bắt buộc vì:
- **pgvector extension** - Chỉ có trên PostgreSQL
- Hỗ trợ VECTOR data type cho embeddings
- HNSW indexing cho fast similarity search
- JSONB cho flexible metadata

SQLite/MySQL không có tính năng này.

---

### Q: Làm sao biết pgvector đã cài đặt chưa?

**A:** Kiểm tra:

```sql
-- Trong psql
\dx

-- Hoặc
SELECT * FROM pg_extension WHERE extname = 'vector';
```

Nếu không thấy, chạy:

```sql
CREATE EXTENSION vector;
```

Nếu báo lỗi "extension does not exist", cài pgvector trước (xem [DEPLOYMENT.md](DEPLOYMENT.md)).

---

### Q: Password database của tôi có ký tự đặc biệt (@, #, ?), làm sao setup?

**A:** URL-encode password trong DATABASE_URL:

```env
# Password gốc: MyPass@123#Test
# URL-encoded: MyPass%40123%23Test

DATABASE_URL=postgresql://postgres:MyPass%40123%23Test@localhost:5432/rag_vectors
```

Bảng encode:
- `@` → `%40`
- `#` → `%23`
- `?` → `%3F`
- `&` → `%26`
- `=` → `%3D`
- ` ` (space) → `%20`

Tool: https://www.urlencoder.org/

---

### Q: Database có bao nhiêu bảng? Khác nhau như thế nào?

**A:** 5 bảng với cấu trúc giống nhau, khác mục đích:

| Bảng | Mục đích | Priority Bonus |
|------|----------|----------------|
| `bases` | Kiến thức nền tảng | +0.0 |
| `answers` | Câu trả lời FAQ (ưu tiên cao nhất) | +0.03 |
| `crawls` | Dữ liệu crawl từ web | +0.02 |
| `respons` | Đóng góp từ người dùng | +0.01 |
| `chunks` | Text chunks từ documents | +0.0 |

Khi search, kết quả từ `answers` sẽ được ưu tiên.

---

### Q: Backup database như thế nào?

**A:** Dùng `pg_dump`:

```powershell
# Backup toàn bộ database
$env:PGPASSWORD = "your_password"
pg_dump -U postgres -d rag_vectors -f backup_$(Get-Date -Format 'yyyyMMdd').sql

# Chỉ backup data (không schema)
pg_dump -U postgres -d rag_vectors --data-only -f data_backup.sql

# Backup một bảng cụ thể
pg_dump -U postgres -d rag_vectors -t bases -f bases_backup.sql

$env:PGPASSWORD = $null
```

Restore:

```powershell
$env:PGPASSWORD = "your_password"
psql -U postgres -d rag_vectors -f backup.sql
$env:PGPASSWORD = $null
```

---

## Vector Search

### Q: Embedding model nặng bao nhiêu? Tải ở đâu?

**A:** 
- **Model:** VoVanPhuc/sup-SimCSE-VietNamese-phobert-base
- **Size:** ~400MB
- **Source:** HuggingFace
- **First run:** Tự động tải về `~/.cache/huggingface/`
- **Sau đó:** Dùng cache, không tải lại

Nếu muốn tải trước:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
```

---

### Q: Tôi có GPU, làm sao dùng để tăng tốc?

**A:** Sửa trong `.env`:

```env
EMBEDDING_DEVICE=cuda
```

Cài CUDA-enabled PyTorch:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

Verify:

```python
import torch
print(torch.cuda.is_available())  # True
```

---

### Q: Search threshold 0.7 có nghĩa là gì? Nên set bao nhiêu?

**A:** 
- **Threshold:** Cosine similarity tối thiểu (0.0 - 1.0)
- **0.7:** Khá tương đồng (default, balanced)
- **0.8-0.9:** Rất tương đồng (strict, ít kết quả)
- **0.5-0.6:** Tương đồng một phần (loose, nhiều kết quả)

Điều chỉnh trong `.env`:

```env
SEARCH_THRESHOLD=0.75  # Tăng độ chính xác
```

Hoặc per request:

```python
results = search_vector(query, top_k=5, threshold=0.8)
```

---

### Q: Tìm kiếm bằng tiếng Anh có hoạt động không?

**A:** Có, nhưng kém hơn tiếng Việt vì:
- Model PhoBERT train trên corpus tiếng Việt
- Embedding space tối ưu cho tiếng Việt

Nếu cần tiếng Anh tốt hơn, xem xét:
- Multilingual model: `paraphrase-multilingual-MiniLM-L12-v2`
- English model: `all-MiniLM-L6-v2`

Cấu hình trong `.env`:

```env
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

---

## API & Integration

### Q: API có yêu cầu authentication không?

**A:** Hiện tại **KHÔNG** (v0.2.0). Đây là planned feature.

Production: Nên implement authentication (JWT, API keys, OAuth).

Xem TODO trong [README.md](README.md#-todo)

---

### Q: Có rate limiting không?

**A:** Hiện tại **KHÔNG**. Đây là planned feature.

Temporary workaround với Nginx:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20;
    proxy_pass http://localhost:8000;
}
```

---

### Q: CORS policy block request từ frontend, sửa sao?

**A:** Thêm origin vào CORS_ORIGINS trong `.env`:

```env
# Development
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:8000"]

# Production
CORS_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
```

Hoặc tạm thời allow all (KHÔNG nên ở production):

```env
CORS_ORIGINS=["*"]
```

---

### Q: Làm sao integrate vào React/Vue/Angular app?

**A:** 

**React example:**

```jsx
async function searchVector(query) {
  const response = await fetch('http://localhost:8000/api/v1/search/vector', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: 5 })
  });
  const data = await response.json();
  return data.results;
}

function SearchComponent() {
  const [results, setResults] = useState([]);
  
  const handleSearch = async (query) => {
    const data = await searchVector(query);
    setResults(data);
  };
  
  return (/* UI */)
}
```

Xem full example: [docs/API_INTEGRATION.md](docs/) (TODO)

---

## Performance

### Q: Search chậm (>1s), làm sao tối ưu?

**A:** Checklist:

1. **Kiểm tra indexes:**
   ```sql
   \d bases  -- Xem indexes
   ```
   Nên có HNSW index trên cột `vector`.

2. **Tạo HNSW index nếu chưa có:**
   ```sql
   CREATE INDEX idx_bases_vector ON bases USING hnsw (vector vector_cosine_ops);
   ```

3. **Connection pooling:** Tăng pool size
   ```env
   PG_POOL_SIZE=20
   PG_MAX_OVERFLOW=10
   ```

4. **Giảm top_k:** Search ít kết quả hơn
   ```python
   search_vector(query, top_k=3)  # Thay vì 10
   ```

5. **Cache embeddings:** Cache query embeddings cho repeat queries

---

### Q: Server chiếm nhiều RAM, tại sao?

**A:** 
- **Embedding model:** ~1-2GB RAM
- **PostgreSQL connection pool:** ~100-500MB
- **Python runtime:** ~100-200MB

Total: ~2-3GB là bình thường.

Nếu quá cao:
1. Giảm connection pool size
2. Dùng `EMBEDDING_DEVICE=cpu` thay vì GPU (GPU RAM khác)
3. Restart server định kỳ

---

### Q: Có thể scale horizontally (nhiều servers) không?

**A:** Có, nhưng cần:
1. **Shared PostgreSQL:** Tất cả servers cùng connect 1 database
2. **Load balancer:** Nginx, HAProxy để phân phối requests
3. **Stateless API:** Không lưu state trên server (đã stateless)

Architecture:

```
[Load Balancer]
    |
    ├─> [API Server 1] ─┐
    ├─> [API Server 2] ─┼─> [PostgreSQL]
    └─> [API Server 3] ─┘
```

---

## Troubleshooting

### Q: Lỗi "ModuleNotFoundError: No module named 'X'"

**A:** 
1. Kiểm tra virtual environment đã activate chưa:
   ```powershell
   # Prompt nên có (.venv)
   .\.venv\Scripts\Activate.ps1
   ```

2. Cài lại dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Kiểm tra module cụ thể:
   ```bash
   pip show <module_name>
   ```

---

### Q: Lỗi "function cosine_similarity does not exist"

**A:** Chạy extension.sql:

```powershell
$env:PGPASSWORD = "your_password"
psql -U postgres -d rag_vectors -f databases\.sql\extension.sql
$env:PGPASSWORD = $null
```

Verify:

```sql
SELECT proname FROM pg_proc WHERE proname = 'cosine_similarity';
```

---

### Q: API trả về 500 Internal Server Error

**A:** 
1. Xem logs để biết error cụ thể:
   ```bash
   # Terminal đang chạy server sẽ hiện error
   ```

2. Common causes:
   - Database connection failed → Check .env
   - Missing function → Run extension.sql
   - Model load failed → Check internet, HuggingFace accessible

3. Debug mode:
   ```env
   LOG_LEVEL=DEBUG
   ```

---

## Development

### Q: Làm sao contribute code?

**A:** Xem [CONTRIBUTING.md](CONTRIBUTING.md)

Quick steps:
1. Fork repository
2. Create branch: `git checkout -b feature/your-feature`
3. Make changes
4. Test
5. Submit PR

---

### Q: Cấu trúc code như thế nào?

**A:**

```
src/
├── backends/
│   ├── api/          # FastAPI routes
│   ├── core/         # Business logic
│   └── database/     # DB connections
└── data_pipeline/    # Data processing (future)
```

Xem chi tiết: [ARCHITECTURE.md](ARCHITECTURE.md)

---

### Q: Có test suite không?

**A:** Đang development (v0.2.0).

Planned:
- Unit tests: `pytest`
- Integration tests: TestClient
- Coverage: `pytest-cov`

Xem TODO: [README.md](README.md#-todo)

---

### Q: Tôi muốn thêm một nguồn dữ liệu mới (ví dụ: bảng `faqs`), làm sao?

**A:** 

1. **Tạo bảng** (clone từ bảng khác):
   ```sql
   CREATE TABLE faqs (
       id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
       category JSONB,
       context JSONB NOT NULL,
       vectors JSONB,
       vector VECTOR(768),
       metadata JSONB,
       created_at TIMESTAMP DEFAULT NOW()
   );
   
   CREATE INDEX idx_faqs_vector ON faqs USING hnsw (vector vector_cosine_ops);
   ```

2. **Thêm vào search** (`src/backends/core/services/vectorSearch.py`):
   ```python
   tables = ['bases', 'answers', 'chunks', 'crawls', 'respons', 'faqs']
   priorities = {
       'bases': 0.0,
       'answers': 0.03,
       'faqs': 0.025,  # <-- Thêm priority
       # ...
   }
   ```

3. **Import data** vào bảng `faqs`

Done!

---

## 📚 Tài liệu khác

- [QUICKSTART.md](QUICKSTART.md) - Quick setup
- [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment
- [API.md](API.md) - API documentation
- [DATABASE.md](DATABASE.md) - Database schema
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guide

---

**Không tìm thấy câu trả lời?**

- 🐛 [Open an issue](../../issues)
- 💬 [Start a discussion](../../discussions)
- 📧 Contact maintainers
