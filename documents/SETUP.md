# Hướng dẫn Cài đặt Chi tiết

## Yêu cầu hệ thống

### Phần cứng
- RAM: Tối thiểu 8GB (khuyến nghị 16GB cho model embedding)
- Disk: 10GB trống
- GPU: Tùy chọn (CUDA-compatible để tăng tốc embedding)

### Phần mềm
- Python 3.10 trở lên
- PostgreSQL 14+ với pgvector extension
- Git

---

## Bước 1: Cài đặt PostgreSQL

### Windows (Native Installation)

1. Tải PostgreSQL từ: https://www.postgresql.org/download/windows/
2. Cài đặt với các tùy chọn mặc định
3. Cài pgvector extension:
   ```cmd
   cd "C:\Program Files\PostgreSQL\<version>\bin"
   psql -U postgres -c "CREATE EXTENSION vector;"
   ```

### Windows (Docker)

```bash
cd .msversion/database
docker-compose up -d
```

### Kiểm tra cài đặt

```bash
# Kiểm tra PostgreSQL đang chạy
pg_isready -h localhost -p 5432

# Kiểm tra pgvector
psql -U postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

## Bước 2: Cài đặt Python Environment

### Tạo Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### Cài đặt Dependencies

```bash
pip install --upgrade pip
pip install -r .msversion/requirements.txt
```

### Cài đặt PyTorch (GPU - tùy chọn)

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## Bước 3: Cấu hình Environment Variables

### Tạo file .env

```bash
cd .msversion
copy .env.example .env
```

### Nội dung file .env

```env
# PostgreSQL Connection
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/rag_vectors

# Individual variables (alternative)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD

# Feature flags
USE_PG_VECTOR=true

# Search settings
SEARCH_THRESHOLD=0.7
VECTOR_DIMENSION=768

# Embedding model
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base

# Priority bonuses for search ranking
PRIORITY_BASES=0.0
PRIORITY_ANSWERS=0.03
PRIORITY_CRAWLS=0.02
PRIORITY_RESPONS=0.01
PRIORITY_CHUNKS=0.0

# Connection pool
PG_POOL_SIZE=10
PG_MAX_OVERFLOW=5
```

---

## Bước 4: Khởi tạo Database

### Tạo Database

```bash
# Windows (với PGPASSWORD)
set PGPASSWORD=YOUR_PASSWORD
createdb -U postgres rag_vectors

# Linux/Mac
PGPASSWORD=YOUR_PASSWORD createdb -U postgres rag_vectors
```

### Chạy SQL Scripts

```bash
cd .msversion/database

# Enable extensions
psql -U postgres -d rag_vectors -f sql/extension.sql

# Tạo tables
psql -U postgres -d rag_vectors -f sql/schema.sql

# Tạo indexes
psql -U postgres -d rag_vectors -f sql/index.sql
```

### Kiểm tra kết quả

```sql
-- Kết nối database
psql -U postgres -d rag_vectors

-- Kiểm tra tables
\dt

-- Kiểm tra extensions
SELECT extname, extversion FROM pg_extension;
```

---

## Bước 5: Chạy ứng dụng

### Development mode

```bash
cd .msversion
python run.py
```

### Production mode

```bash
cd .msversion
uvicorn web_api.routes.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Kiểm tra API

```bash
# Health check
curl http://localhost:8000/health

# Swagger UI
# Mở browser: http://localhost:8000/docs
```

---

## Troubleshooting

### Lỗi: "psycopg2 not found"

```bash
pip install psycopg2-binary
```

### Lỗi: "CUDA out of memory"

Giảm batch size hoặc sử dụng CPU:
```python
# Trong code
device = "cpu"  # thay vì "cuda"
```

### Lỗi: "Connection refused" (PostgreSQL)

```bash
# Windows
net start postgresql-x64-18

# Kiểm tra port
netstat -an | findstr 5432
```

### Lỗi: "pgvector extension not found"

```sql
-- Trong psql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Liên hệ hỗ trợ

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub repository.
