Bạn nói đúng, lạm dụng emoji trong tài liệu kỹ thuật đôi khi khiến tổng thể trông khá rối mắt và thiếu đi sự nghiêm túc cần thiết của một dự án phần mềm. Một file README tốt chỉ cần cấu trúc Markdown rõ ràng là đủ để truyền tải thông tin.

Dưới đây là bản README đã được tôi dọn sạch toàn bộ các biểu tượng cảm xúc, được tinh chỉnh lại định dạng để đảm bảo sự chuyên nghiệp, gọn gàng và dễ đọc nhất.

-----

# BOT--RAG-Agent

Hệ thống RAG (Retrieval-Augmented Generation) với PostgreSQL pgvector cho tìm kiếm ngữ nghĩa tiếng Việt.

## Tính năng chính

  - **Vector Search:** Tìm kiếm ngữ nghĩa với pgvector.
  - **Vietnamese Support:** Tối ưu cho tiếng Việt (PhoBERT).
  - **Chat Interface:** Web UI thân thiện.
  - **User Contribution:** Người dùng đóng góp kiến thức.
  - **Priority System:** Điều chỉnh thứ tự kết quả theo bảng.
  - **Fast Setup:** Script tự động setup toàn bộ.

## Quick Start

### Phương pháp 1: Setup tự động (Khuyến nghị)

```powershell
# Clone repository
git clone <repo-url>
cd BOT--RAG-Agent

# Chạy setup script (PowerShell as Admin)
.\setup_native.ps1
```

Script sẽ tự động:

  - Tạo virtual environment.
  - Cài đặt dependencies.
  - Setup PostgreSQL database.
  - Tạo file .env.
  - Tải embedding model (tùy chọn).

Sau khi setup xong:

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Start server
python run.py
```

Mở trình duyệt: `http://localhost:8000`

### Phương pháp 2: Setup thủ công

Xem hướng dẫn chi tiết trong [QUICKSTART.md](QUICKSTART.md).

## Cấu trúc dự án

```text
BOT--RAG-Agent/
├── src/                      # Source code chính
│   ├── backends/             
│   │   ├── api/              # FastAPI routes (vector_api.py)
│   │   ├── core/             # Business logic & services
│   │   │   ├── services/     # Vector search, embedding
│   │   │   └── utils/        # Utilities
│   │   └── database/         # PostgreSQL connection
│   └── data_pipeline/        # (Future) Data ingestion
│
├── databases/                
│   └── .sql/                 # SQL scripts (schema, index, extension)
│
├── public/                   # Frontend assets
│   └── shared/               
│       ├── index.html        # Main UI
│       └── Assets/           # CSS, JS, images
│
├── configs/                  # Configuration files
├── models/                   # ML model cache (auto-created)
├── logs/                     # Application logs
├── docs/                     # Documentation
│
├── .env                      # Environment config (create from .env.example)
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── run.py                    # Application entry point
└── setup_native.ps1          # Automated setup script
```

## Tài liệu

### Bắt đầu

  - [QUICKSTART.md](QUICKSTART.md) - Hướng dẫn setup nhanh.
  - [DEPLOYMENT.md](https://www.google.com/search?q=DEPLOYMENT.md) - Triển khai từ con số 0.
  - [SETUP.md](SETUP.md) - Setup chi tiết từng bước.

### Kỹ thuật

  - [ARCHITECTURE.md](ARCHITECTURE.md) - Kiến trúc hệ thống.
  - [DATABASE.md](DATABASE.md) - Cấu trúc database & schema.
  - [API.md](API.md) - API endpoints documentation.
  - [REPORT.md](REPORT.md) - Migration report (Docker sang Native).

### Tính năng

  - [docs/CONTRIBUTION\_IMPLEMENTATION.md](https://www.google.com/search?q=docs/CONTRIBUTION_IMPLEMENTATION.md) - Hệ thống đóng góp.
  - [docs/FRONTEND\_CONTRIBUTION\_GUIDE.md](https://www.google.com/search?q=docs/FRONTEND_CONTRIBUTION_GUIDE.md) - Frontend integration.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.8+ |
| **Web Framework** | FastAPI |
| **Database** | PostgreSQL 12+ |
| **Vector Extension** | pgvector |
| **Embedding Model** | PhoBERT (VoVanPhuc/sup-SimCSE-VietNamese-phobert-base) |
| **Vector Dimension** | 768 |
| **Search Method** | Cosine similarity + HNSW index |
| **Frontend** | HTML/CSS/JavaScript (Vanilla) |

## Database Schema

Hệ thống sử dụng 5 bảng chính với cấu trúc giống nhau:

| Table | Mục đích | Priority Bonus |
|-------|----------|----------------|
| `bases` | Kiến thức cơ bản | +0.0 |
| `answers` | Câu trả lời FAQ | +0.03 |
| `crawls` | Dữ liệu crawl từ web | +0.02 |
| `respons` | Đóng góp từ người dùng | +0.01 |
| `chunks` | Text chunks từ documents | +0.0 |

Cấu trúc các trường trong mỗi bảng:

  - `id`: UUID (Primary Key).
  - `category`: JSONB (Metadata).
  - `context`: JSONB (Article + Content).
  - `vectors`: JSONB (Subvectors).
  - `vector`: VECTOR(768) (PhoBERT embedding).
  - `metadata`: JSONB.
  - `created_at`: TIMESTAMP.

## API Endpoints

### Search

```http
POST /api/v1/search/vector
Content-Type: application/json

{
  "query": "quyền của sinh viên",
  "top_k": 5
}
```

### Contribution

```http
POST /api/v1/contribution
Content-Type: application/json

{
  "user_question": "Câu hỏi gốc",
  "user_contribution": "Nội dung đóng góp",
  "metadata": {}
}
```

Xem chi tiết tại: [API.md](API.md).

## Cấu hình

Nội dung file `.env` chính:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=rag_vectors
DB_USER=postgres
DB_PASSWORD=your_password_here

# Lưu ý: Password có ký tự đặc biệt phải được URL-encode
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rag_vectors

# Vector Search
USE_PG_VECTOR=true
SEARCH_THRESHOLD=0.7

# Embedding
EMBEDDING_MODEL=VoVanPhuc/sup-SimCSE-VietNamese-phobert-base
EMBEDDING_DEVICE=cpu

# API
API_HOST=0.0.0.0
API_PORT=8000
```

Copy từ template:

```powershell
cp .env.example .env
```

## Testing

### Test database connection

```powershell
python -c "from src.backends.database.pgConnection import PGConnection; conn = PGConnection(); print('OK')"
```

### Test API

```powershell
# Start server
python run.py

# In another terminal
curl -X POST http://localhost:8000/api/v1/search/vector `
  -H "Content-Type: application/json" `
  -d '{"query": "test", "top_k": 1}'
```

### Test contribution endpoint

```powershell
python test_contribution_api.py
```

## Troubleshooting

Tham khảo [QUICKSTART.md](https://www.google.com/search?q=QUICKSTART.md%23troubleshooting) để xử lý các lỗi thường gặp:

  - `psql: command not found`
  - `could not translate host name`
  - `Extension "vector" does not exist`
  - `function cosine_similarity does not exist`
  - Xung đột Port.
  - Lỗi tải Embedding model.

## Contributing

### Đóng góp kiến thức (User)

1.  Mở web UI tại `http://localhost:8000`.
2.  Hỏi chatbot một câu hỏi.
3.  Nhận câu trả lời.
4.  Click nút **"Đóng góp"** bên dưới câu trả lời.
5.  Nhập nội dung đóng góp (10-500 ký tự).
6.  Submit. Dữ liệu sẽ tự động được thêm vào database cùng với embedding.

### Đóng góp code (Developer)

1.  Fork repository.
2.  Create feature branch.
3.  Make changes.
4.  Test thoroughly.
5.  Submit pull request.

## Performance

  - **Vector dimension:** 768 (PhoBERT).
  - **Index type:** HNSW (Hierarchical Navigable Small World).
  - **Search latency:** \~50-200ms (Phụ thuộc vào kích thước dataset).
  - **Connection pool:** 10 connections, 5 overflow.

## Security Notes

  - Không commit file `.env` lên hệ thống quản lý mã nguồn (Git).
  - Sử dụng mật khẩu mạnh cho PostgreSQL.
  - Cấu hình CORS chặt chẽ khi đưa lên môi trường Production.
  - Đảm bảo URL-encode đối với mật khẩu chứa các ký tự đặc biệt.

## TODO

  - [ ] Authentication & Authorization.
  - [ ] Rate limiting cho contribution endpoint.
  - [ ] Admin panel để quản lý dữ liệu.
  - [ ] Data pipeline cho import documents.
  - [ ] Monitoring & metrics (Prometheus/Grafana).
  - [ ] Docker deployment option.
  - [ ] Unit tests & integration tests.

## License

MIT License

-----


## Repository workflow
- `orias` — feature development branch
- `dev` — integration branch for medium-sized features
- `main` — stable releases for large features
