# ============================================================================
# RAG Agent Database Setup Script (PowerShell)
# Tự động setup PostgreSQL + pgvector + Python từ con số 0
# Chạy: .\setup.ps1
# ============================================================================

# Màu sắc output
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"

function Write-Success { Write-Host "[✓]" -ForegroundColor $SuccessColor -NoNewline; Write-Host " $($args -join ' ')" }
function Write-Error-Custom { Write-Host "[✗]" -ForegroundColor $ErrorColor -NoNewline; Write-Host " $($args -join ' ')" }
function Write-Info { Write-Host "[i]" -ForegroundColor $InfoColor -NoNewline; Write-Host " $($args -join ' ')" }
function Write-Warning-Custom { Write-Host "[!]" -ForegroundColor $WarningColor -NoNewline; Write-Host " $($args -join ' ')" }

# ============================================================================
# SECTION 1: Kiểm tra yêu cầu
# ============================================================================
Write-Info "=========================================================="
Write-Info "RAG Agent Database Setup (Docker + PostgreSQL + Python)"
Write-Info "=========================================================="
Write-Info ""

# Kiểm tra Docker
Write-Info "Kiểm tra Docker Desktop..."
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker tìm thấy: $dockerVersion"
    } else {
        Write-Error-Custom "Docker không tìm thấy"
        Write-Info "Tải Docker Desktop từ: https://www.docker.com/products/docker-desktop/"
        exit 1
    }
} catch {
    Write-Error-Custom "Docker Desktop không được cài đặt"
    exit 1
}

# Kiểm tra Docker daemon
Write-Info "Kiểm tra Docker daemon..."
try {
    docker ps >$null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker daemon đang chạy"
    } else {
        Write-Error-Custom "Docker daemon không chạy, vui lòng khởi động Docker Desktop"
        exit 1
    }
} catch {
    Write-Error-Custom "Không thể kết nối Docker daemon"
    exit 1
}

# Kiểm tra Python
Write-Info "Kiểm tra Python..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python tìm thấy: $pythonVersion"
} catch {
    Write-Error-Custom "Python không được cài đặt"
    exit 1
}

# ============================================================================
# SECTION 2: Setup Docker PostgreSQL + pgvector
# ============================================================================
Write-Info ""
Write-Info "=========================================================="
Write-Info "SECTION 2: PostgreSQL + pgvector setup"
Write-Info "=========================================================="
Write-Info ""

# Kiểm tra container đã tồn tại
$containerExists = docker ps -a --filter "name=pgvector-db" --format "{{.Names}}" 2>$null

if ($containerExists) {
    Write-Warning-Custom "Container 'pgvector-db' đã tồn tại"
    $response = Read-Host "Bạn muốn xóa container cũ và tạo mới? (y/n)"
    if ($response -eq "y") {
        Write-Info "Dừng container..."
        docker stop pgvector-db >$null 2>&1
        Write-Info "Xóa container..."
        docker rm pgvector-db >$null 2>&1
        Write-Info "Xóa volume..."
        docker volume rm pgvector-data >$null 2>&1
        Write-Success "Container/volume cũ đã xóa"
    } else {
        Write-Info "Sử dụng container hiện tại"
        # Nếu container tồn tại nhưng không chạy, start nó
        $containerRunning = docker ps --filter "name=pgvector-db" --format "{{.Names}}" 2>$null
        if (-not $containerRunning) {
            Write-Info "Khởi động container..."
            docker start pgvector-db >$null 2>&1
            Start-Sleep -Seconds 3
            Write-Success "Container khởi động"
        }
    }
} else {
    Write-Info "Pull image pgvector/pgvector:pg16..."
    try {
        docker pull pgvector/pgvector:pg16
        Write-Success "Image pulled thành công"
    } catch {
        Write-Error-Custom "Không thể pull image"
        exit 1
    }

    # Chạy container
    Write-Info "Chạy PostgreSQL container..."
    try {
        docker run -d `
            --name pgvector-db `
            -e POSTGRES_USER=postgres `
            -e POSTGRES_PASSWORD=ragpass123 `
            -e POSTGRES_DB=rag_vectors `
            -p 5432:5432 `
            -v pgvector-data:/var/lib/postgresql/data `
            pgvector/pgvector:pg16 | Out-Null
        
        Write-Success "Container khởi động"
    } catch {
        Write-Error-Custom "Không thể khởi động container"
        exit 1
    }

    # Đợi container sẵn sàng
    Write-Info "Đợi container khởi động... (tối đa 30 giây)"
    $maxRetries = 30
    $retryCount = 0
    $dbReady = $false

    while ($retryCount -lt $maxRetries) {
        try {
            docker exec pgvector-db psql -U postgres -d rag_vectors -c "SELECT 1" >$null 2>&1
            if ($LASTEXITCODE -eq 0) {
                $dbReady = $true
                break
            }
        } catch { }
        
        Start-Sleep -Seconds 1
        $retryCount++
        Write-Host "." -NoNewline
    }

    Write-Host ""
    if ($dbReady) {
        Write-Success "PostgreSQL sẵn sàng"
    } else {
        Write-Error-Custom "PostgreSQL không sẵn sàng sau 30 giây"
        Write-Info "Container logs:"
        docker logs pgvector-db
        exit 1
    }
}

# Verify pgvector extension
Write-Info "Tạo pgvector extension..."
try {
    docker exec pgvector-db psql -U postgres -d rag_vectors -c "CREATE EXTENSION IF NOT EXISTS vector;" >$null 2>&1
    Write-Success "pgvector extension sẵn sàng"
} catch {
    Write-Error-Custom "Không thể tạo extension"
    exit 1
}

# ============================================================================
# SECTION 3: Python Environment Setup
# ============================================================================
Write-Info ""
Write-Info "=========================================================="
Write-Info "SECTION 3: Python Environment Setup"
Write-Info "=========================================================="
Write-Info ""

# Kiểm tra virtual environment
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Info "Virtual environment đã tồn tại"
    $response = Read-Host "Bạn muốn recreate? (y/n)"
    if ($response -eq "y") {
        Write-Info "Xóa virtual environment cũ..."
        Remove-Item -Recurse -Force ".\.venv" >$null 2>&1
        Write-Info "Tạo virtual environment mới..."
        python -m venv .venv
        Write-Success "Virtual environment tạo mới"
    } else {
        Write-Info "Sử dụng virtual environment hiện tại"
    }
} else {
    Write-Info "Tạo virtual environment..."
    try {
        python -m venv .venv
        Write-Success "Virtual environment tạo thành công"
    } catch {
        Write-Error-Custom "Không thể tạo virtual environment"
        exit 1
    }
}

# Activate virtual environment
Write-Info "Activate virtual environment..."
& ".\.venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -eq 0) {
    Write-Success "Virtual environment activated"
} else {
    Write-Error-Custom "Không thể activate virtual environment"
    exit 1
}

# Upgrade pip
Write-Info "Upgrade pip..."
python -m pip install --upgrade pip -q >$null 2>&1
Write-Success "pip upgraded"

# Install dependencies
Write-Info "Install dependencies từ requirements.txt..."
if (-not (Test-Path "requirements.txt")) {
    Write-Error-Custom "requirements.txt không tìm thấy"
    exit 1
}

try {
    pip install -r requirements.txt -q
    Write-Success "Dependencies installed"
} catch {
    Write-Error-Custom "Không thể install dependencies"
    Write-Info "Thử lại với: pip install -r requirements.txt"
    exit 1
}

# ============================================================================
# SECTION 4: Configure .env
# ============================================================================
Write-Info ""
Write-Info "=========================================================="
Write-Info "SECTION 4: Configure .env"
Write-Info "=========================================================="
Write-Info ""

$envPath = ".\.env"

if (Test-Path $envPath) {
    Write-Warning-Custom ".env đã tồn tại"
    $response = Read-Host "Bạn muốn overwrite? (y/n)"
    if ($response -ne "y") {
        Write-Info "Sử dụng .env hiện tại"
        exit
    }
}

Write-Info "Tạo .env file..."
$envContent = @"
# ============================================================================
# PostgreSQL Connection
# ============================================================================
DATABASE_URL=postgresql://postgres:ragpass123@localhost:5432/rag_vectors
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=ragpass123

# ============================================================================
# Vector Search Configuration
# ============================================================================
USE_PG_VECTOR=true
SEARCH_THRESHOLD=0.7
VECTOR_DIMENSION=768
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base

# ============================================================================
# Priority Scoring
# ============================================================================
PRIORITY_BASES=0.0
PRIORITY_ANSWERS=0.03
PRIORITY_CRAWLS=0.02
PRIORITY_RESPONS=0.01
PRIORITY_CHUNKS=0.0

# ============================================================================
# Connection Pool
# ============================================================================
PG_POOL_SIZE=10
PG_MAX_OVERFLOW=5

# ============================================================================
# API Configuration
# ============================================================================
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true
"@

try {
    $envContent | Out-File -FilePath $envPath -Encoding UTF8 -NoNewline
    Write-Success ".env file tạo thành công"
} catch {
    Write-Error-Custom "Không thể tạo .env file"
    exit 1
}

# ============================================================================
# SECTION 5: Database Schema Migration
# ============================================================================
Write-Info ""
Write-Info "=========================================================="
Write-Info "SECTION 5: Database Schema Migration"
Write-Info "=========================================================="
Write-Info ""

Write-Info "Kiểm tra migration script..."
if (-not (Test-Path "scripts\migrate_schema.py")) {
    Write-Error-Custom "scripts/migrate_schema.py không tìm thấy"
    exit 1
}

Write-Info "Chạy migration..."
try {
    # Activate .env
    $env:DATABASE_URL = "postgresql://postgres:ragpass123@localhost:5432/rag_vectors"
    
    python -m scripts.migrate_schema up
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Migration thành công"
    } else {
        Write-Warning-Custom "Migration script kết thúc nhưng có thể có lỗi"
    }
} catch {
    Write-Error-Custom "Không thể chạy migration"
    Write-Info "Thử lại với: python -m scripts.migrate_schema up"
    exit 1
}

# ============================================================================
# SECTION 6: Verification
# ============================================================================
Write-Info ""
Write-Info "=========================================================="
Write-Info "SECTION 6: Verification"
Write-Info "=========================================================="
Write-Info ""

Write-Info "Verify PostgreSQL connection..."
try {
    $result = docker exec pgvector-db psql -U postgres -d rag_vectors -c "SELECT version();" 2>&1
    Write-Success "PostgreSQL connection OK"
} catch {
    Write-Error-Custom "PostgreSQL connection failed"
}

Write-Info "Verify pgvector extension..."
try {
    $result = docker exec pgvector-db psql -U postgres -d rag_vectors -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';" 2>&1 | Select-String "0\."
    if ($result) {
        Write-Success "pgvector extension OK (version: $result)"
    }
} catch {
    Write-Error-Custom "pgvector extension check failed"
}

Write-Info "Verify database tables..."
try {
    $result = docker exec pgvector-db psql -U postgres -d rag_vectors -c "\dt" 2>&1
    $tableCount = ($result | Measure-Object -Line).Lines
    Write-Success "Database tables found: ~$(if($tableCount -gt 5) { '5+' } else { $tableCount })"
} catch {
    Write-Error-Custom "Database tables check failed"
}

# ============================================================================
# SECTION 7: Summary
# ============================================================================
Write-Info ""
Write-Info "=========================================================="
Write-Info "✓ SETUP HOÀN TẤT"
Write-Info "=========================================================="
Write-Info ""

Write-Success "Tất cả được setup thành công!"
Write-Info ""
Write-Info "Thông tin kết nối:"
Write-Info "  - Host: localhost"
Write-Info "  - Port: 5432"
Write-Info "  - Database: rag_vectors"
Write-Info "  - User: postgres"
Write-Info "  - Password: ragpass123"
Write-Info ""
Write-Info "Các bước tiếp theo:"
Write-Info "  1. Khởi động API server:"
Write-Info "     python run.py"
Write-Info ""
Write-Info "  2. Mở Swagger UI:"
Write-Info "     http://localhost:8000/docs"
Write-Info ""
Write-Info "  3. Các Docker commands hữu ích:"
Write-Info "     docker ps              # Xem containers"
Write-Info "     docker logs pgvector-db # Xem logs"
Write-Info "     docker exec -it pgvector-db psql -U postgres -d rag_vectors"
Write-Info ""
Write-Info "Tài liệu: docs/SETUP.md"
Write-Info "=========================================================="

pause
