# 📚 Documentation Index

Hệ thống tài liệu đầy đủ cho dự án RAG System.

---

## 🚀 Bắt đầu nhanh (Start Here)

Nếu bạn là người mới, bắt đầu theo thứ tự:

1. **[README.md](README.md)** - Tổng quan dự án và tính năng
2. **[QUICKSTART.md](QUICKSTART.md)** - Setup nhanh trong 5 phút
3. **[FAQ.md](FAQ.md)** - Câu hỏi thường gặp

---

## 📖 Tài liệu theo vai trò

### 👨‍💼 Cho người dùng cuối (End Users)

| Tài liệu | Mô tả | Khi nào đọc |
|----------|-------|-------------|
| [README.md](README.md) | Tổng quan dự án | Muốn hiểu dự án làm gì |
| [FAQ.md](FAQ.md) | Câu hỏi thường gặp | Gặp vấn đề cần giải đáp nhanh |

### 🔧 Cho người triển khai (DevOps / System Admin)

| Tài liệu | Mô tả | Khi nào đọc |
|----------|-------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Setup nhanh với script tự động | Setup lần đầu (khuyến nghị) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Hướng dẫn deploy từ con số 0 | Setup thủ công hoặc production |
| [SETUP.md](SETUP.md) | Setup chi tiết từng bước | Troubleshooting setup issues |
| [DATABASE.md](DATABASE.md) | Cấu trúc database, backup/restore | Quản lý database |
| [REPORT.md](REPORT.md) | Migration report Docker → Native | Hiểu lý do migrate |

### 👨‍💻 Cho developers

| Tài liệu | Mô tả | Khi nào đọc |
|----------|-------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc hệ thống | Hiểu cấu trúc code |
| [API.md](API.md) | API endpoints documentation | Integrate với API |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Hướng dẫn contribute code | Muốn đóng góp code |
| [CHANGELOG.md](CHANGELOG.md) | Lịch sử thay đổi | Theo dõi updates |
| [docs/CONTRIBUTION_IMPLEMENTATION.md](docs/CONTRIBUTION_IMPLEMENTATION.md) | Tính năng đóng góp của user | Hiểu contribution feature |
| [docs/FRONTEND_CONTRIBUTION_GUIDE.md](docs/FRONTEND_CONTRIBUTION_GUIDE.md) | Frontend integration guide | Làm việc với frontend |

---

## 📂 Tài liệu theo chủ đề

### 🏗️ Setup & Installation

| Tài liệu | Level | Time | Mô tả |
|----------|-------|------|-------|
| [QUICKSTART.md](QUICKSTART.md) | Beginner | 10 min | Setup tự động, nhanh nhất |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Intermediate | 30 min | Deploy từ đầu, production-ready |
| [SETUP.md](SETUP.md) | Advanced | 45 min | Setup thủ công chi tiết |

**Khuyến nghị:** Bắt đầu với QUICKSTART.md

---

### 🗄️ Database

| Tài liệu | Nội dung |
|----------|----------|
| [DATABASE.md](DATABASE.md) | Schema, tables, indexes, queries, backup/restore |
| [databases/.sql/](databases/.sql/) | SQL scripts (extension, schema, index) |

**Key files:**
- `databases/.sql/extension.sql` - Extensions & functions
- `databases/.sql/schema.sql` - Table definitions
- `databases/.sql/index.sql` - HNSW indexes

---

### 🌐 API & Integration

| Tài liệu | Nội dung |
|----------|----------|
| [API.md](API.md) | REST API endpoints, request/response format |
| [docs/FRONTEND_CONTRIBUTION_GUIDE.md](docs/FRONTEND_CONTRIBUTION_GUIDE.md) | Frontend integration examples |

**Key endpoints:**
- `POST /api/v1/search/vector` - Vector search
- `POST /api/v1/contribution` - User contribution

---

### 🏛️ Architecture & Design

| Tài liệu | Nội dung |
|----------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, components, data flow |
| [REPORT.md](REPORT.md) | Migration decisions, technical rationale |

**Key concepts:**
- Modular structure
- Vector search pipeline
- Priority system

---

### 🤝 Contributing

| Tài liệu | Nội dung |
|----------|----------|
| [CONTRIBUTING.md](CONTRIBUTING.md) | Code style, PR process, testing |
| [CHANGELOG.md](CHANGELOG.md) | Version history, breaking changes |
| [LICENSE](LICENSE) | MIT License terms |

---

### ❓ Help & Troubleshooting

| Tài liệu | Nội dung |
|----------|----------|
| [FAQ.md](FAQ.md) | Common questions & answers |
| [QUICKSTART.md#troubleshooting](QUICKSTART.md#troubleshooting) | Setup issues |

---

## 📋 Checklist sử dụng tài liệu

### Lần đầu setup

- [ ] Đọc [README.md](README.md) để hiểu tổng quan
- [ ] Làm theo [QUICKSTART.md](QUICKSTART.md) để setup
- [ ] Chạy thử nghiệm và test API
- [ ] Đọc [FAQ.md](FAQ.md) nếu gặp lỗi

### Triển khai production

- [ ] Đọc [DEPLOYMENT.md](DEPLOYMENT.md) đầy đủ
- [ ] Setup PostgreSQL production
- [ ] Cấu hình .env cho production
- [ ] Setup backup database ([DATABASE.md](DATABASE.md))
- [ ] Configure monitoring & logging

### Development

- [ ] Đọc [ARCHITECTURE.md](ARCHITECTURE.md)
- [ ] Đọc [CONTRIBUTING.md](CONTRIBUTING.md)
- [ ] Setup development environment
- [ ] Đọc [API.md](API.md) để hiểu endpoints
- [ ] Write tests

---

## 🔍 Tìm kiếm nhanh

### "Tôi muốn..."

| Mục đích | Đọc tài liệu |
|----------|--------------|
| Setup dự án trong 5 phút | [QUICKSTART.md](QUICKSTART.md) |
| Hiểu dự án làm gì | [README.md](README.md) |
| Cài đặt từ đầu trên máy mới | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Fix lỗi setup | [FAQ.md](FAQ.md) |
| Backup database | [DATABASE.md](DATABASE.md) |
| Gọi API từ code | [API.md](API.md) |
| Contribute code | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Thêm feature mới | [CONTRIBUTING.md](CONTRIBUTING.md), [ARCHITECTURE.md](ARCHITECTURE.md) |
| Deploy lên server | [DEPLOYMENT.md](DEPLOYMENT.md) |

---

## 📊 Tổng quan tài liệu

### Documentation map

```
BOT--RAG-Agent/
│
├── 📄 README.md              ← START HERE (Tổng quan)
├── 🚀 QUICKSTART.md          ← Quick setup (5 min)
├── 📖 DEPLOYMENT.md          ← Full deployment guide
├── 🔧 SETUP.md               ← Detailed setup steps
│
├── 🏗️ ARCHITECTURE.md        ← System design
├── 🗄️ DATABASE.md            ← Database schema & operations
├── 🌐 API.md                 ← API documentation
│
├── 🤝 CONTRIBUTING.md        ← How to contribute
├── ❓ FAQ.md                 ← Frequently asked questions
├── 📝 CHANGELOG.md           ← Version history
│
├── 📊 REPORT.md              ← Migration report
├── ⚖️ LICENSE                ← MIT License
│
└── docs/                     ← Additional documentation
    ├── CONTRIBUTION_IMPLEMENTATION.md
    └── FRONTEND_CONTRIBUTION_GUIDE.md
```

---

## 📈 Difficulty levels

| Level | Documents |
|-------|-----------|
| 🟢 **Beginner** | README, QUICKSTART, FAQ |
| 🟡 **Intermediate** | DEPLOYMENT, DATABASE, API |
| 🔴 **Advanced** | ARCHITECTURE, CONTRIBUTING, source code |

---

## 📦 Files & Scripts

### Configuration files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (create from `.env.example`) |
| `.env.example` | Template with detailed comments |
| `.gitignore` | Git ignore rules |
| `requirements.txt` | Python dependencies |

### Setup scripts

| Script | Purpose |
|--------|---------|
| `setup_native.ps1` | Automated setup for Windows + PostgreSQL |
| `run.py` | Application entry point |
| `test_contribution_api.py` | Test contribution endpoint |

### SQL scripts

| File | Purpose |
|------|---------|
| `databases/.sql/extension.sql` | PostgreSQL extensions & functions |
| `databases/.sql/schema.sql` | Table definitions |
| `databases/.sql/index.sql` | HNSW vector indexes |

---

## 🔗 External resources

- **PostgreSQL:** https://www.postgresql.org/docs/
- **pgvector:** https://github.com/pgvector/pgvector
- **FastAPI:** https://fastapi.tiangolo.com/
- **PhoBERT:** https://huggingface.co/VoVanPhuc/sup-SimCSE-VietNamese-phobert-base

---

## ✅ Documentation quality checklist

Tất cả tài liệu tuân thủ:

- [x] Có mục lục rõ ràng
- [x] Code examples có syntax highlighting
- [x] Screenshots/diagrams khi cần (TODO: thêm diagrams)
- [x] Links giữa các documents
- [x] Troubleshooting sections
- [x] Cập nhật với code hiện tại
- [x] Kiểm tra spelling & grammar (TODO: automated check)

---

## 📞 Support

Nếu không tìm thấy thông tin cần thiết:

1. 🔍 Search trong [FAQ.md](FAQ.md)
2. 📖 Đọc document liên quan trong index này
3. 🐛 [Open an issue](../../issues)
4. 💬 [Start a discussion](../../discussions)

---

## 🔄 Document updates

**Last updated:** 2024-01-XX

**Version:** 0.2.0

Tài liệu được cập nhật cùng với mỗi release. Xem [CHANGELOG.md](CHANGELOG.md) để biết thay đổi.

---

**Happy coding! 🚀**
