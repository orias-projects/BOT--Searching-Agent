# 📖 DEPLOYMENT GUIDE - RAG System

Hướng dẫn triển khai hệ thống RAG từ con số 0 trên máy mới.

---

## 📋 MỤC LỤC

1. [Chuẩn bị môi trường](#1-chuẩn-bị-môi-trường)
2. [Cài đặt PostgreSQL](#2-cài-đặt-postgresql)
3. [Setup dự án](#3-setup-dự-án)
4. [Cấu hình hệ thống](#4-cấu-hình-hệ-thống)
5. [Import dữ liệu](#5-import-dữ-liệu)
6. [Chạy ứng dụng](#6-chạy-ứng-dụng)
7. [Production deployment](#7-production-deployment)

---

## 1. CHUẨN BỊ MÔI TRƯỜNG

### Windows 10/11

#### A. Cài đặt Python 3.8+

1. Download Python từ [python.org](https://www.python.org/downloads/)
2. Chạy installer
3. **QUAN TRỌNG:** Tick ✅ "Add Python to PATH"
4. Chọn "Customize installation"
5. Tick ✅ "pip", "py launcher"
6. Tick ✅ "Add Python to environment variables"
7. Click "Install"

**Verify:**
```powershell
python --version
# Python 3.11.x hoặc cao hơn

pip --version
# pip 23.x.x
```

#### B. Cài đặt Git

1. Download từ [git-scm.com](https://git-scm.com/downloads)
2. Chạy installer với default settings
3. Khởi động lại terminal

**Verify:**
```powershell
git --version
# git version 2.x.x
```

#### C. Visual C++ Redistributable (optional)

Một số Python packages cần Visual C++:

1. Download [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. Install

---

## 2. CÀI ĐẶT POSTGRESQL

### A. Download PostgreSQL

1. Vào [PostgreSQL Downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
2. Chọn phiên bản **12 trở lên** (khuyến nghị 14+)
3. Chọn platform: **Windows x86-64**
4. Download installer

### B. Cài đặt PostgreSQL

1. Chạy installer với quyền Administrator
2. Chọn thư mục cài đặt (ví dụ: `E:\_DevTools\PostgreSQL`)
3. Chọn components:
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4 (GUI tool)
   - ✅ Stack Builder (để cài extensions)
   - ✅ Command Line Tools

4. Cấu hình:
   - **Data Directory:** Để mặc định hoặc chọn ổ đĩa có dung lượng lớn
   - **Password:** Đặt mật khẩu cho superuser `postgres` (GHI NHỚ!)
   - **Port:** 5432 (mặc định)
   - **Locale:** Default locale

5. Click "Next" → "Install"

### C. Cài đặt pgvector Extension

**Option 1: Qua Stack Builder (Khuyến nghị)**

1. Mở **Stack Builder** (từ Start Menu → PostgreSQL)
2. Chọn PostgreSQL instance
3. Expand "Spatial Extensions"
4. Tìm và chọn **pgvector**
5. Download & Install

**Option 2: Compile từ source**

```powershell
# Yêu cầu: Visual Studio hoặc Build Tools
git clone https://github.com/pgvector/pgvector.git
cd pgvector

# Build (cần nmake từ Visual Studio)
nmake /F Makefile.win
nmake /F Makefile.win install
```

**Option 3: Pre-built binary**

Download từ [pgvector releases](https://github.com/pgvector/pgvector/releases)

### D. Thêm PostgreSQL vào PATH

1. Mở System Properties → Advanced → Environment Variables
2. Hoặc dùng PowerShell (Run as Admin):

```powershell
# Thay đổi path nếu cài ở nơi khác
$pgPath = "C:\Program Files\PostgreSQL\14\bin"

# Thêm vào PATH
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";$pgPath",
    "Machine"
)
```

3. Mở terminal mới và verify:

```powershell
psql --version
# psql (PostgreSQL) 14.x
```

### E. Khởi động PostgreSQL Service

```powershell
# Kiểm tra service
Get-Service -Name "postgresql*"

# Nếu stopped, khởi động:
Start-Service postgresql-x64-14  # Thay đổi version nếu cần

# Set tự động khởi động khi boot
Set-Service -Name "postgresql-x64-14" -StartupType Automatic
```

---

## 3. SETUP DỰ ÁN

### A. Clone Repository

```powershell
# Chọn thư mục làm việc
cd E:\_DevResources\Personal

# Clone project
git clone <repository_url> BOT--RAG-Agent
cd BOT--RAG-Agent
```

### B. Tạo Virtual Environment

```powershell
# Tạo venv
python -m venv .venv

# Activate
.\.venv\Scripts\Activate.ps1

# Nếu gặp lỗi ExecutionPolicy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Upgrade pip
python -m pip install --upgrade pip
```

### C. Cài đặt Dependencies

```powershell
# Đảm bảo venv đã activate (prompt có (.venv))
pip install -r requirements.txt

# Nếu gặp lỗi với psycopg2, dùng binary:
pip install psycopg2-binary

# Verify installation
pip list | Select-String "psycopg2|fastapi|sentence-transformers"
```

---

## 4. CẤU HÌNH HỆ THỐNG

### A. Tạo Database

```powershell
# Login vào PostgreSQL
psql -U postgres

# Trong psql prompt:
CREATE DATABASE rag_vectors;

# Verify
\l

# Connect vào database mới
\c rag_vectors

# Exit
\q
```

### B. Chạy SQL Scripts

```powershell
# Set password environment (để không nhập lại)
$env:PGPASSWORD = "your_password_here"

# 1. Tạo extensions và functions
psql -U postgres -d rag_vectors -f databases\.sql\extension.sql

# 2. Tạo tables
psql -U postgres -d rag_vectors -f databases\.sql\schema.sql

# 3. Tạo indexes
psql -U postgres -d rag_vectors -f databases\.sql\index.sql

# Clear password từ environment
$env:PGPASSWORD = $null
```

**Verify:**

```powershell
$env:PGPASSWORD = "your_password"

# Kiểm tra extensions
psql -U postgres -d rag_vectors -c "\dx"

# Kiểm tra tables
psql -U postgres -d rag_vectors -c "\dt"

# Kiểm tra function
psql -U postgres -d rag_vectors -c "SELECT proname FROM pg_proc WHERE proname = 'cosine_similarity';"

$env:PGPASSWORD = $null
```

Kết quả mong đợi:
- Extensions: `vector`, `uuid-ossp`, `pg_trgm`
- Tables: `bases`, `answers`, `chunks`, `crawls`, `respons`
- Function: `cosine_similarity`

### C. Tạo file .env

```powershell
# Copy template
cp .env.example .env

# Edit .env với editor yêu thích
notepad .env
# Hoặc
code .env
```

**Điền thông tin:**

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=your_actual_password_here

# ⚠️ Nếu password có @ # ? &, phải URL-encode trong DATABASE_URL
# Ví dụ: MyPass@123 → MyPass%40123
DATABASE_URL=postgresql://postgres:your_actual_password_here@localhost:5432/rag_vectors

USE_PG_VECTOR=true
SEARCH_THRESHOLD=0.7
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base
EMBEDDING_DEVICE=cpu
```

**Test connection:**

```powershell
python -c "from src.backends.database.pgConnection import PGConnection; conn = PGConnection(); print('✅ Connection OK')"
```

---

## 5. IMPORT DỮ LIỆU

### A. Từ backup SQL

Nếu có file backup từ database cũ:

```powershell
$env:PGPASSWORD = "your_password"

psql -U postgres -d rag_vectors -f backup.sql

$env:PGPASSWORD = $null
```

### B. Từ CSV files

Xem chi tiết trong [DATABASE.md](DATABASE.md)

Ví dụ import vào bảng `bases`:

```sql
COPY bases(id, category, context, vectors, vector, metadata, created_at)
FROM 'C:\path\to\bases.csv'
DELIMITER ','
CSV HEADER;
```

### C. Import tài liệu PDF/Word

Sử dụng data pipeline (xem [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md)):

```powershell
# Đặt files vào thư mục documents/
# Chạy pipeline
python -m src.data_pipeline.main
```

---

## 6. CHẠY ỨNG DỤNG

### A. Development Mode

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Chạy server
python run.py
```

Output:
```
✅ Kiểm tra services...
✅ All services ready!

🚀 Starting RAG System Server...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### B. Truy cập ứng dụng

Mở trình duyệt:
```
http://localhost:8000
```

### C. Test API

**Vector Search:**
```powershell
# PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/search/vector" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"query": "quyền của sinh viên", "top_k": 3}'
```

**Contribution:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/contribution" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"user_question": "Test", "user_contribution": "Content here"}'
```

---

## 7. PRODUCTION DEPLOYMENT

### A. Cấu hình Production

**.env cho production:**

```env
# Secure settings
DB_PASSWORD=<strong_password>
API_HOST=0.0.0.0  # hoặc specific IP
API_PORT=8000

# CORS cho production
CORS_ORIGINS=["https://yourdomain.com"]

# Logging
LOG_LEVEL=WARNING
LOG_FILE=logs/production.log

# Performance
PG_POOL_SIZE=20
PG_MAX_OVERFLOW=10
```

### B. Chạy với Gunicorn/Uvicorn

**Windows Service với NSSM:**

1. Download [NSSM](https://nssm.cc/download)
2. Cài đặt service:

```powershell
# Extract nssm.exe
# Open PowerShell as Admin

nssm install RAGService "E:\_DevResources\Personal\BOT--RAG-Agent\.venv\Scripts\python.exe" "E:\_DevResources\Personal\BOT--RAG-Agent\run.py"

# Set working directory
nssm set RAGService AppDirectory "E:\_DevResources\Personal\BOT--RAG-Agent"

# Set environment
nssm set RAGService AppEnvironmentExtra "PATH=E:\_DevResources\Personal\BOT--RAG-Agent\.venv\Scripts;%PATH%"

# Start service
nssm start RAGService

# Check status
nssm status RAGService
```

**Hoặc dùng Task Scheduler:**

1. Mở Task Scheduler
2. Create Task:
   - Name: RAG System
   - Trigger: At system startup
   - Action: Start a program
     - Program: `E:\_DevResources\Personal\BOT--RAG-Agent\.venv\Scripts\python.exe`
     - Arguments: `run.py`
     - Start in: `E:\_DevResources\Personal\BOT--RAG-Agent`

### C. Nginx Reverse Proxy (Optional)

**Install Nginx for Windows:**

1. Download từ [nginx.org](http://nginx.org/en/download.html)
2. Extract vào `C:\nginx`
3. Edit `C:\nginx\conf\nginx.conf`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

4. Start Nginx:
```powershell
cd C:\nginx
start nginx
```

### D. SSL/HTTPS với Let's Encrypt

Sử dụng [Certbot for Windows](https://certbot.eff.org/instructions?ws=nginx&os=windows):

```powershell
# Install Certbot
# Download từ https://dl.eff.org/certbot-beta-installer-win32.exe

# Run
certbot --nginx -d yourdomain.com
```

### E. Monitoring & Logs

**Logging:**

```python
# Đã có trong run.py
import logging
logging.basicConfig(
    level=logging.INFO,
    filename='logs/app.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

**Monitor với PowerShell:**

```powershell
# Theo dõi logs
Get-Content -Path logs\app.log -Wait -Tail 50

# Kiểm tra service
Get-Service -Name "postgresql*", "RAGService"

# Kiểm tra port
netstat -ano | findstr :8000
netstat -ano | findstr :5432
```

---

## 🔧 TROUBLESHOOTING

### Lỗi: Port 5432 already in use

```powershell
# Tìm process
netstat -ano | findstr :5432

# Kill process (PID ở cột cuối)
Stop-Process -Id <PID> -Force
```

### Lỗi: Cannot connect to PostgreSQL

1. Kiểm tra service:
```powershell
Get-Service postgresql*
Start-Service postgresql-x64-14
```

2. Kiểm tra firewall:
```powershell
# Add firewall rule
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
```

3. Kiểm tra `pg_hba.conf`:
```
# Thêm dòng này
host    all    all    127.0.0.1/32    md5
```

### Lỗi: Embedding model download fails

```powershell
# Set proxy nếu cần
$env:HTTP_PROXY = "http://proxy:port"
$env:HTTPS_PROXY = "http://proxy:port"

# Tải thủ công
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')"
```

---

## 📚 TÀI LIỆU LIÊN QUAN

- [QUICKSTART.md](QUICKSTART.md) - Setup nhanh
- [README.md](README.md) - Tổng quan
- [API.md](API.md) - API documentation
- [DATABASE.md](DATABASE.md) - Database schema
- [ARCHITECTURE.md](ARCHITECTURE.md) - Kiến trúc hệ thống

---

## ✅ CHECKLIST TRIỂN KHAI

- [ ] Python 3.8+ đã cài
- [ ] PostgreSQL 12+ đã cài
- [ ] pgvector extension đã cài
- [ ] Git đã cài
- [ ] Repository đã clone
- [ ] Virtual environment đã tạo
- [ ] Dependencies đã install
- [ ] Database `rag_vectors` đã tạo
- [ ] SQL scripts đã chạy (extension, schema, index)
- [ ] File `.env` đã cấu hình
- [ ] Database connection test OK
- [ ] Server chạy thành công
- [ ] Web UI accessible
- [ ] API endpoints hoạt động

---

**Chúc deployment thành công! 🚀**

Nếu cần hỗ trợ, kiểm tra logs hoặc xem các file documentation khác.
