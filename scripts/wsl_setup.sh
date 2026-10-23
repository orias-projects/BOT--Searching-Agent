#!/bin/bash
# ============================================================================
# WSL SETUP - Kết nối tới Windows PostgreSQL
# ============================================================================

echo ""
echo "🚀 WSL SETUP FOR RAG SYSTEM"
echo ""

# 1. Lấy Windows IP
echo "📍 Tìm Windows IP..."
WINDOWS_IP=$(grep -m 1 nameserver /etc/resolv.conf | awk '{print $2}')
echo "   Windows IP: $WINDOWS_IP"
echo ""

# 2. Kiểm tra project
if [ ! -d "BOT--RAG-Agent" ]; then
    echo "📁 Clone project..."
    git clone <repo-url> BOT--RAG-Agent
fi

cd BOT--RAG-Agent

# 3. Tạo .env cho WSL
echo "⚙️  Tạo .env..."
cat > .env.wsl << EOF
# PostgreSQL (Windows host)
DB_HOST=$WINDOWS_IP
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=LongK@170105

DATABASE_URL=postgresql://postgres:LongK%40170105@$WINDOWS_IP:5432/rag_vectors

USE_PG_VECTOR=true
SEARCH_THRESHOLD=0.7
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base
EMBEDDING_DEVICE=cpu

# API Server (allow external)
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["*"]
EOF

echo "✅ .env.wsl created"
echo ""

# 4. Kiểm tra Python
echo "🐍 Kiểm tra Python..."
python3 --version

# 5. Tạo venv
echo "📦 Tạo virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# 6. Cài dependencies
echo "📥 Cài dependencies..."
pip install --upgrade pip
pip install -r requirements.txt -q

echo "✅ Setup complete!"
echo ""
echo "============================================================================"
echo "                    🎯 CÁCH CHẠY SERVER"
echo "============================================================================"
echo ""
echo "1. Activate venv:"
echo "   source .venv/bin/activate"
echo ""
echo "2. Chạy server (dùng .env.wsl):"
echo "   export $(cat .env.wsl | xargs)"
echo "   python run.py"
echo ""
echo "3. Expose qua internet (terminal khác):"
echo "   # Install ngrok nếu chưa có"
echo "   curl https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip -o ngrok.zip"
echo "   unzip ngrok.zip"
echo "   chmod +x ngrok"
echo ""
echo "   # Expose port 3000 (frontend)"
echo "   ./ngrok http 3000"
echo ""
echo "   # Hoặc 8000 (API)"
echo "   ./ngrok http 8000"
echo ""
echo "4. Share public URL từ ngrok output!"
echo ""
echo "============================================================================"
echo ""
