# ============================================================================
# RAG System - Complete Setup Script for Windows (Native PostgreSQL)
# ============================================================================
# Script này tự động setup toàn bộ hệ thống từ đầu cho máy mới
# Yêu cầu: Python 3.8+, PostgreSQL 12+
# ============================================================================

param(
    [string]$DBPassword = "",
    [string]$DBUser = "postgres",
    [string]$DBName = "rag_vectors",
    [int]$DBPort = 5432,
    [string]$DBHost = "localhost"
)

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "          RAG SYSTEM - COMPLETE SETUP SCRIPT" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host "`n[STEP] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  $Message" -ForegroundColor Cyan
}

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# ============================================================================
# STEP 1: CHECK PREREQUISITES
# ============================================================================

Write-Step "Kiểm tra các yêu cầu hệ thống..."

# Check Python
if (Test-Command "python") {
    $pythonVersion = python --version 2>&1
    Write-Success "Python đã cài đặt: $pythonVersion"
    
    # Check Python version
    $versionMatch = [regex]::Match($pythonVersion, "(\d+)\.(\d+)")
    $majorVersion = [int]$versionMatch.Groups[1].Value
    $minorVersion = [int]$versionMatch.Groups[2].Value
    
    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
        Write-Error-Custom "Python version quá thấp. Cần Python 3.8 trở lên."
        exit 1
    }
} else {
    Write-Error-Custom "Python chưa được cài đặt hoặc chưa có trong PATH"
    Write-Info "Tải Python từ: https://www.python.org/downloads/"
    exit 1
}

# Check PostgreSQL
if (Test-Command "psql") {
    $pgVersion = psql --version
    Write-Success "PostgreSQL đã cài đặt: $pgVersion"
} else {
    Write-Error-Custom "PostgreSQL chưa được cài đặt hoặc chưa có trong PATH"
    Write-Info "Tải PostgreSQL từ: https://www.postgresql.org/download/windows/"
    Write-Info "Hoặc: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads"
    exit 1
}

# Check pg_ctl (để start/stop service)
if (Test-Command "pg_ctl") {
    Write-Success "pg_ctl có sẵn"
} else {
    Write-Info "pg_ctl không tìm thấy (optional, có thể dùng Windows Services)"
}

# ============================================================================
# STEP 2: GET DATABASE PASSWORD
# ============================================================================

if ([string]::IsNullOrWhiteSpace($DBPassword)) {
    Write-Step "Nhập thông tin database..."
    Write-Host "  Nhập mật khẩu PostgreSQL user '$DBUser': " -NoNewline -ForegroundColor White
    $securePassword = Read-Host -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $DBPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}

# ============================================================================
# STEP 3: CREATE VIRTUAL ENVIRONMENT
# ============================================================================

Write-Step "Tạo môi trường ảo Python (.venv)..."

if (Test-Path ".venv") {
    Write-Info "Thư mục .venv đã tồn tại. Xóa và tạo lại? (Y/N): " -NoNewline
    $response = Read-Host
    if ($response -eq "Y" -or $response -eq "y") {
        Remove-Item -Recurse -Force .venv
        Write-Success "Đã xóa .venv cũ"
    } else {
        Write-Info "Giữ nguyên .venv hiện tại"
    }
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Đã tạo virtual environment"
    } else {
        Write-Error-Custom "Không thể tạo virtual environment"
        exit 1
    }
}

# Activate virtual environment
Write-Info "Kích hoạt virtual environment..."
& ".venv\Scripts\Activate.ps1"
Write-Success "Virtual environment đã được kích hoạt"

# ============================================================================
# STEP 4: INSTALL PYTHON DEPENDENCIES
# ============================================================================

Write-Step "Cài đặt Python dependencies từ requirements.txt..."

if (Test-Path "requirements.txt") {
    Write-Info "Đang cài đặt packages... (có thể mất vài phút)"
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Đã cài đặt tất cả dependencies"
    } else {
        Write-Error-Custom "Có lỗi khi cài đặt dependencies"
        exit 1
    }
} else {
    Write-Error-Custom "File requirements.txt không tìm thấy"
    exit 1
}

# ============================================================================
# STEP 5: CHECK POSTGRESQL SERVICE
# ============================================================================

Write-Step "Kiểm tra PostgreSQL service..."

# Try to find PostgreSQL service
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($pgService) {
    Write-Success "Tìm thấy service: $($pgService.Name)"
    
    if ($pgService.Status -ne "Running") {
        Write-Info "Service đang dừng. Khởi động service..."
        Start-Service $pgService.Name
        Start-Sleep -Seconds 3
        
        $pgService.Refresh()
        if ($pgService.Status -eq "Running") {
            Write-Success "Service đã khởi động"
        } else {
            Write-Error-Custom "Không thể khởi động service"
            exit 1
        }
    } else {
        Write-Success "Service đang chạy"
    }
} else {
    Write-Info "Không tìm thấy PostgreSQL service tự động"
    Write-Info "Đảm bảo PostgreSQL đang chạy trước khi tiếp tục"
}

# ============================================================================
# STEP 6: CREATE DATABASE
# ============================================================================

Write-Step "Tạo database '$DBName'..."

# Set PGPASSWORD environment variable for psql
$env:PGPASSWORD = $DBPassword

# Check if database exists
$dbExists = psql -h $DBHost -p $DBPort -U $DBUser -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$DBName';" 2>$null

if ($dbExists -match "1") {
    Write-Info "Database '$DBName' đã tồn tại"
    Write-Host "  Xóa và tạo lại? (Y/N): " -NoNewline -ForegroundColor Cyan
    $response = Read-Host
    
    if ($response -eq "Y" -or $response -eq "y") {
        # Terminate connections first
        psql -h $DBHost -p $DBPort -U $DBUser -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DBName';" 2>&1 | Out-Null
        
        # Drop database
        psql -h $DBHost -p $DBPort -U $DBUser -d postgres -c "DROP DATABASE IF EXISTS $DBName;" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Đã xóa database cũ"
        } else {
            Write-Error-Custom "Không thể xóa database"
        }
    }
}

# Create database if not exists
$dbExists = psql -h $DBHost -p $DBPort -U $DBUser -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='$DBName';" 2>$null

if (-not ($dbExists -match "1")) {
    psql -h $DBHost -p $DBPort -U $DBUser -d postgres -c "CREATE DATABASE $DBName;" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Đã tạo database '$DBName'"
    } else {
        Write-Error-Custom "Không thể tạo database"
        $env:PGPASSWORD = $null
        exit 1
    }
} else {
    Write-Info "Sử dụng database hiện có"
}

# ============================================================================
# STEP 7: RUN SQL SCRIPTS
# ============================================================================

Write-Step "Chạy SQL scripts..."

$sqlScripts = @(
    @{Path="databases\.sql\extension.sql"; Name="Extensions & Functions"},
    @{Path="databases\.sql\schema.sql"; Name="Database Schema"},
    @{Path="databases\.sql\index.sql"; Name="Vector Indexes"}
)

foreach ($script in $sqlScripts) {
    if (Test-Path $script.Path) {
        Write-Info "Chạy $($script.Name)..."
        
        $output = psql -h $DBHost -p $DBPort -U $DBUser -d $DBName -f $script.Path 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$($script.Name) - OK"
        } else {
            Write-Error-Custom "$($script.Name) - FAILED"
            Write-Host "  Output: $output" -ForegroundColor Red
            Write-Info "Tiếp tục với script tiếp theo..."
        }
    } else {
        Write-Error-Custom "Không tìm thấy: $($script.Path)"
    }
}

# Clear password
$env:PGPASSWORD = $null

# ============================================================================
# STEP 8: VERIFY DATABASE SETUP
# ============================================================================

Write-Step "Kiểm tra cấu trúc database..."

$env:PGPASSWORD = $DBPassword

# Check extensions
Write-Info "Kiểm tra extensions..."
$extensions = psql -h $DBHost -p $DBPort -U $DBUser -d $DBName -t -c "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp');" 2>$null

if ($extensions -match "vector") {
    Write-Success "Extension 'vector' đã cài đặt"
} else {
    Write-Error-Custom "Extension 'vector' chưa được cài đặt"
}

if ($extensions -match "uuid-ossp") {
    Write-Success "Extension 'uuid-ossp' đã cài đặt"
} else {
    Write-Error-Custom "Extension 'uuid-ossp' chưa được cài đặt"
}

# Check tables
Write-Info "Kiểm tra tables..."
$tables = psql -h $DBHost -p $DBPort -U $DBUser -d $DBName -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public';" 2>$null

$expectedTables = @("bases", "answers", "chunks", "crawls", "respons")
foreach ($table in $expectedTables) {
    if ($tables -match $table) {
        Write-Success "Table '$table' ✓"
    } else {
        Write-Error-Custom "Table '$table' không tìm thấy"
    }
}

# Check cosine_similarity function
Write-Info "Kiểm tra custom functions..."
$funcExists = psql -h $DBHost -p $DBPort -U $DBUser -d $DBName -t -c "SELECT proname FROM pg_proc WHERE proname='cosine_similarity';" 2>$null

if ($funcExists -match "cosine_similarity") {
    Write-Success "Function 'cosine_similarity' đã tồn tại"
} else {
    Write-Error-Custom "Function 'cosine_similarity' chưa được tạo"
}

$env:PGPASSWORD = $null

# ============================================================================
# STEP 9: CREATE .ENV FILE
# ============================================================================

Write-Step "Tạo file .env..."

$skipEnv = $false
if (Test-Path ".env") {
    Write-Host "  File .env đã tồn tại. Ghi đè? (Y/N): " -NoNewline -ForegroundColor Cyan
    $response = Read-Host
    
    if ($response -ne "Y" -and $response -ne "y") {
        Write-Info "Giữ nguyên file .env hiện tại"
        $skipEnv = $true
    }
}

if (-not $skipEnv) {
    # URL encode password (handle special characters like @)
    Add-Type -AssemblyName System.Web
    $encodedPassword = [System.Web.HttpUtility]::UrlEncode($DBPassword)
    
    $envContent = @"
# Database Configuration
DB_HOST=$DBHost
DB_PORT=$DBPort
DB_NAME=$DBName
DB_USER=$DBUser
DB_PASSWORD=$DBPassword
DATABASE_URL=postgresql://${DBUser}:${encodedPassword}@${DBHost}:${DBPort}/${DBName}

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
"@

    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Success "Đã tạo file .env"
}

# ============================================================================
# STEP 10: DOWNLOAD EMBEDDING MODEL (OPTIONAL)
# ============================================================================

Write-Step "Tải embedding model (optional)..."
Write-Host "  Tải model ngay bây giờ? (Y/N) - Model ~400MB: " -NoNewline -ForegroundColor Cyan
$response = Read-Host

if ($response -eq "Y" -or $response -eq "y") {
    Write-Info "Đang tải model... (có thể mất vài phút)"
    
    $modelScript = @"
from sentence_transformers import SentenceTransformer
print('Downloading model...')
model = SentenceTransformer('VoVanPhuc/sup-SimCSE-VietNamese-phobert-base')
print('Model downloaded successfully!')
print(f'Model dimension: {model.get_sentence_embedding_dimension()}')
"@
    
    python -c $modelScript
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Model đã được tải về và cache"
    } else {
        Write-Info "Model sẽ tự động tải khi khởi động server lần đầu"
    }
} else {
    Write-Info "Model sẽ tự động tải khi khởi động server lần đầu"
}

# ============================================================================
# FINAL SUMMARY
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Green
Write-Host "                    ✅ SETUP HOÀN TẤT!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "📋 THÔNG TIN HỆ THỐNG:" -ForegroundColor Cyan
Write-Host "  • Database: $DBName @ $DBHost:$DBPort" -ForegroundColor White
Write-Host "  • Virtual Environment: .venv" -ForegroundColor White
Write-Host "  • Environment File: .env" -ForegroundColor White
Write-Host ""

Write-Host "🚀 CÁCH KHỞI ĐỘNG:" -ForegroundColor Cyan
Write-Host "  1. Kích hoạt virtual environment:" -ForegroundColor White
Write-Host "     " -NoNewline
Write-Host ".\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Khởi động server:" -ForegroundColor White
Write-Host "     " -NoNewline
Write-Host "python run.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Mở trình duyệt:" -ForegroundColor White
Write-Host "     " -NoNewline
Write-Host "http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

Write-Host "📚 IMPORT DỮ LIỆU (nếu cần):" -ForegroundColor Cyan
Write-Host "  • Export từ database khác:" -ForegroundColor White
Write-Host "    pg_dump -h old_host -U postgres -d old_db -t bases -t answers -t chunks --data-only > data.sql" -ForegroundColor Yellow
Write-Host ""
Write-Host "  • Import vào database mới:" -ForegroundColor White
Write-Host "    psql -h $DBHost -U $DBUser -d $DBName -f data.sql" -ForegroundColor Yellow
Write-Host ""

Write-Host "📖 TÀI LIỆU:" -ForegroundColor Cyan
Write-Host "  • README.md - Tổng quan dự án" -ForegroundColor White
Write-Host "  • SETUP.md - Hướng dẫn setup chi tiết" -ForegroundColor White
Write-Host "  • API.md - API documentation" -ForegroundColor White
Write-Host "  • DATABASE.md - Database schema & queries" -ForegroundColor White
Write-Host ""

Write-Host "⚠️  LƯU Ý:" -ForegroundColor Yellow
Write-Host "  • Mật khẩu database đã được lưu trong .env" -ForegroundColor White
Write-Host "  • Không commit file .env lên git" -ForegroundColor White
Write-Host "  • Virtual environment cần được activate mỗi lần mở terminal mới" -ForegroundColor White
Write-Host ""

Write-Host "============================================================================" -ForegroundColor Green
Write-Host ""
