# 🚀 Quick Setup Guide - RAG System

## Mục lục
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Setup tự động (Khuyến nghị)](#setup-tự-động-khuyến-nghị)
- [Setup thủ công](#setup-thủ-công)
- [Troubleshooting](#troubleshooting)

---

## Yêu cầu hệ thống

### ✅ Phải có
- **Windows 10/11**
- **Python 3.8+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 12+** - [Download](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
- **Git** - [Download](https://git-scm.com/downloads)

### 📦 Tùy chọn
- **PostgreSQL pgvector extension** - Thường đi kèm PostgreSQL 12+
- **Visual C++ Redistributable** - Cho một số Python packages

---

## Setup tự động (Khuyến nghị)

### Bước 1: Clone repository

```powershell
git clone <repository_url>
cd BOT--RAG-Agent
```

### Bước 2: Chạy setup script

```powershell
# PowerShell (Run as Administrator recommended)
.\setup_native.ps1
```

Script sẽ tự động:
1. ✅ Kiểm tra Python & PostgreSQL
2. ✅ Tạo virtual environment (.venv)
3. ✅ Cài đặt dependencies
4. ✅ Tạo database `rag_vectors`
5. ✅ Setup extensions (vector, uuid-ossp)
6. ✅ Tạo tables và indexes
7. ✅ Tạo file `.env`
8. ✅ (Optional) Tải embedding model

### Bước 3: Khởi động server

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start server
python run.py
```

### Bước 4: Mở trình duyệt

```
http://localhost:8000
```

---

## Setup thủ công

Nếu script tự động không hoạt động, làm theo các bước sau:

### 1. Cài đặt PostgreSQL

1. Download PostgreSQL từ [PostgreSQL Downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Chọn phiên bản 12 trở lên
3. Trong quá trình cài đặt:
   - Đặt mật khẩu cho user `postgres` (ghi nhớ!)
   - Port mặc định: 5432
   - Chọn cài đặt **pgAdmin** (optional)
   - Chọn cài đặt **Stack Builder** → Chọn **pgvector extension**

### 2. Kiểm tra PostgreSQL

```powershell
# Kiểm tra version
psql --version

# Kiểm tra service đang chạy
Get-Service -Name "postgresql*"

# Nếu service dừng, khởi động:
Start-Service postgresql-x64-*
```

### 3. Tạo Virtual Environment

```powershell
# Tạo venv
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip
```

### 4. Cài đặt Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Tạo Database

```powershell
# Login vào PostgreSQL
psql -U postgres

# Trong psql prompt:
CREATE DATABASE rag_vectors;
\c rag_vectors

# Thoát psql
\q
```

### 6. Chạy SQL Scripts

```powershell
# Set password environment variable
$env:PGPASSWORD = "your_password"

# Run scripts
psql -U postgres -d rag_vectors -f databases\.sql\extension.sql
psql -U postgres -d rag_vectors -f databases\.sql\schema.sql
psql -U postgres -d rag_vectors -f databases\.sql\index.sql

# Clear password
$env:PGPASSWORD = $null
```

### 7. Tạo file .env

Tạo file `.env` trong thư mục gốc:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=your_password_here
DATABASE_URL=postgresql://postgres:your_password_here@localhost:5432/rag_vectors

# Vector Search Configuration
USE_PG_VECTOR=true
SEARCH_THRESHOLD=0.7

# Embedding Model
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base
EMBEDDING_DEVICE=cpu

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:8000"]

# Logging
LOG_LEVEL=INFO
```

**⚠️ Lưu ý:** Nếu mật khẩu có ký tự đặc biệt (như `@`), cần URL-encode trong DATABASE_URL:
- `LongK@170105` → `LongK%40170105`

### 8. Khởi động Server

```powershell
# Activate venv (nếu chưa)
.\.venv\Scripts\Activate.ps1

# Run server
python run.py
```

---

## Import dữ liệu (Optional)

### Từ database khác

```powershell
# Export data từ database cũ
pg_dump -h old_host -U postgres -d old_database `
  -t bases -t answers -t chunks -t crawls -t respons `
  --data-only `
  --inserts `
  > data_backup.sql

# Import vào database mới
$env:PGPASSWORD = "your_password"
psql -U postgres -d rag_vectors -f data_backup.sql
$env:PGPASSWORD = $null
```

### Từ CSV files

Xem hướng dẫn chi tiết trong [DATABASE.md](DATABASE.md)

---

## Troubleshooting

### Lỗi: `psql: command not found`

**Nguyên nhân:** PostgreSQL chưa có trong PATH

**Giải pháp:**
1. Tìm thư mục cài đặt PostgreSQL (thường ở `C:\Program Files\PostgreSQL\<version>\bin`)
2. Thêm vào PATH:
   ```powershell
   # PowerShell (Run as Admin)
   $pgPath = "C:\Program Files\PostgreSQL\16\bin"
   [Environment]::SetEnvironmentVariable("Path", $env:Path + ";$pgPath", "Machine")
   ```
3. Mở terminal mới và test lại

### Lỗi: `python: command not found`

**Giải pháp:**
1. Reinstall Python từ [python.org](https://www.python.org/downloads/)
2. Trong quá trình cài đặt, **tick vào "Add Python to PATH"**
3. Hoặc thêm thủ công vào PATH

### Lỗi: `could not translate host name`

**Nguyên nhân:** DATABASE_URL có định dạng sai (thường do ký tự `@` trong password)

**Giải pháp:**
1. Mở `.env`
2. URL-encode password:
   - `@` → `%40`
   - `#` → `%23`
   - `?` → `%3F`
   - ` ` (space) → `%20`

Ví dụ:
```
# Password gốc: LongK@170105
DATABASE_URL=postgresql://postgres:LongK%40170105@localhost:5432/rag_vectors
```

### Lỗi: `Extension "vector" does not exist`

**Giải pháp:**

**Option 1:** Cài qua Stack Builder
1. Mở **Stack Builder** (đi kèm PostgreSQL installer)
2. Chọn PostgreSQL instance
3. Tìm và cài **pgvector**

**Option 2:** Compile từ source
```powershell
# Clone pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# Build & Install (cần Visual Studio)
# Chi tiết: https://github.com/pgvector/pgvector#windows
```

**Option 3:** Dùng pre-built binary
- Download từ [pgvector releases](https://github.com/pgvector/pgvector/releases)

### Lỗi: `function cosine_similarity does not exist`

**Giải pháp:**

Chạy lại extension.sql:

```powershell
$env:PGPASSWORD = "your_password"
psql -U postgres -d rag_vectors -f databases\.sql\extension.sql
$env:PGPASSWORD = $null
```

Verify:
```sql
-- Trong psql
\c rag_vectors
SELECT proname FROM pg_proc WHERE proname = 'cosine_similarity';
```

### Lỗi: `No module named 'psycopg2'`

**Giải pháp:**

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Install psycopg2-binary
pip install psycopg2-binary
```

### Lỗi: Port 8000 đã được sử dụng

**Giải pháp:**

**Option 1:** Đổi port trong `.env`:
```env
API_PORT=8001
```

**Option 2:** Kill process đang dùng port 8000:
```powershell
# Tìm process
netstat -ano | findstr :8000

# Kill process (replace PID)
Stop-Process -Id <PID> -Force
```

### Lỗi: Embedding model tải quá lâu

**Nguyên nhân:** Model ~400MB, tải từ HuggingFace lần đầu

**Giải pháp:**
1. Chờ tải xong (chỉ 1 lần, sau đó cache)
2. Hoặc tải trước:
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
   ```

---

## Kiểm tra Setup thành công

### Test Database Connection

```powershell
$env:PGPASSWORD = "your_password"
psql -U postgres -d rag_vectors -c "SELECT version();"
psql -U postgres -d rag_vectors -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname='public';"
$env:PGPASSWORD = $null
```

Kết quả mong đợi: 5 tables (bases, answers, chunks, crawls, respons)

### Test API

1. Start server: `python run.py`
2. Mở trình duyệt: `http://localhost:8000`
3. Test search endpoint:
   ```powershell
   curl -X POST http://localhost:8000/api/v1/search/vector `
     -H "Content-Type: application/json" `
     -d '{"query": "test", "top_k": 1}'
   ```

---

## Uninstall / Cleanup

### Xóa toàn bộ

```powershell
# Xóa virtual environment
Remove-Item -Recurse -Force .venv

# Xóa database
$env:PGPASSWORD = "your_password"
psql -U postgres -c "DROP DATABASE IF EXISTS rag_vectors;"
$env:PGPASSWORD = $null

# Xóa cache model (optional)
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface"
```

---

## Liên kết hữu ích

- [README.md](README.md) - Tổng quan dự án
- [SETUP.md](SETUP.md) - Hướng dẫn setup chi tiết
- [API.md](API.md) - API documentation
- [DATABASE.md](DATABASE.md) - Database schema
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture

---

## Hỗ trợ

Nếu gặp lỗi không nằm trong danh sách trên:

1. Kiểm tra logs trong console
2. Kiểm tra file `.env` có đúng format không
3. Kiểm tra PostgreSQL service đang chạy
4. Xem [SETUP.md](SETUP.md) để biết thêm chi tiết

**Happy coding! 🚀**
