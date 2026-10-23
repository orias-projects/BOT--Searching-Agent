# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Hiện tại API không yêu cầu authentication. Trong production, nên thêm API key hoặc JWT.

---

## Endpoints

### Health Check

#### `GET /health`

Kiểm tra trạng thái hệ thống.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "tables": ["bases", "answers", "crawls", "respons", "chunks"],
  "record_counts": {
    "bases": 81,
    "answers": 6,
    "chunks": 156,
    "crawls": 0,
    "respons": 0
  }
}
```

---

### Vector Search

#### `POST /api/v1/search`

Tìm kiếm semantic trong database.

**Request Body:**
```json
{
  "query": "Làm thế nào để đăng ký học phần?",
  "top_k": 5,
  "threshold": 0.5,
  "tables": ["bases", "answers"],
  "include_metadata": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | ✅ | - | Câu hỏi tìm kiếm |
| `top_k` | int | ❌ | 5 | Số kết quả trả về |
| `threshold` | float | ❌ | 0.5 | Ngưỡng similarity (0-1) |
| `tables` | array | ❌ | all | Tables cần search |
| `include_metadata` | bool | ❌ | false | Có trả về metadata không |

**Response:**
```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "table": "bases",
      "score": 0.87,
      "adjusted_score": 0.87,
      "context": {
        "question": "Cách đăng ký học phần",
        "answer": "Sinh viên đăng ký qua portal..."
      },
      "metadata": {
        "source": "handbook",
        "updated_at": "2024-01-15"
      }
    }
  ],
  "total": 1,
  "query_time_ms": 45
}
```

---

### Vector Insert

#### `POST /api/v1/insert`

Thêm vector mới vào database.

**Request Body:**
```json
{
  "table": "answers",
  "data": {
    "question": "Làm thế nào để xin nghỉ học?",
    "answer": "Sinh viên cần nộp đơn xin nghỉ..."
  },
  "category": {
    "topic": "academic",
    "subtopic": "leave"
  },
  "metadata": {
    "author": "admin",
    "verified": true
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `table` | string | ✅ | Table đích (bases/answers/crawls/respons/chunks) |
| `data` | object | ✅ | Nội dung cần embed |
| `category` | object | ❌ | Phân loại |
| `metadata` | object | ❌ | Metadata bổ sung |

**Response:**
```json
{
  "success": true,
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "table": "answers",
  "embedded_fields": ["question", "answer"],
  "vector_dimension": 768
}
```

---

### Batch Insert

#### `POST /api/v1/insert/batch`

Thêm nhiều records cùng lúc.

**Request Body:**
```json
{
  "table": "chunks",
  "items": [
    {
      "data": {"text": "Nội dung chunk 1..."},
      "metadata": {"page": 1}
    },
    {
      "data": {"text": "Nội dung chunk 2..."},
      "metadata": {"page": 2}
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "inserted": 2,
  "failed": 0,
  "ids": [
    "550e8400-e29b-41d4-a716-446655440002",
    "550e8400-e29b-41d4-a716-446655440003"
  ]
}
```

---

### Table Info

#### `GET /api/v1/tables`

Lấy danh sách tables và số lượng records.

**Response:**
```json
{
  "tables": [
    {"name": "bases", "count": 81, "priority": 0.0},
    {"name": "answers", "count": 6, "priority": 0.03},
    {"name": "crawls", "count": 0, "priority": 0.02},
    {"name": "respons", "count": 0, "priority": 0.01},
    {"name": "chunks", "count": 156, "priority": 0.0}
  ]
}
```

#### `GET /api/v1/tables/{table_name}/count`

Lấy số lượng records của một table.

**Response:**
```json
{
  "table": "bases",
  "count": 81
}
```

---

### User Contribution (Feedback)

#### `POST /api/v1/contribution`

Thêm đóng góp của người dùng vào bảng `respons`. Endpoint này được gọi khi người dùng nhấn nút "Đóng góp" dưới mỗi câu trả lời của bot.

**Request Body:**
```json
{
  "user_question": "Làm thế nào để học Python hiệu quả?",
  "user_contribution": "Nên bắt đầu từ cơ bản, thực hành thường xuyên trên các platform như LeetCode, HackerRank. Đọc tài liệu chính thức của Python và xây dựng các dự án nhỏ.",
  "metadata": {
    "user_id": "user123",
    "source": "web_chat",
    "rating": 5
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_question` | string | ✅ | Câu hỏi gốc của người dùng (lưu vào `Article`) |
| `user_contribution` | string | ✅ | Nội dung đóng góp (lưu vào `Content`) |
| `metadata` | object | ❌ | Metadata bổ sung (user_id, source, rating, etc.) |

**Response:**
```json
{
  "success": true,
  "id": "773ab0e7-3a71-58de-96e4-705e79cc3233",
  "table": "respons",
  "message": "Contribution added successfully. Thank you for improving our knowledge base!"
}
```

**Đặc điểm:**
- Tự động tạo vector embeddings từ `user_question` và `user_contribution`
- Deduplication: Nếu nội dung giống nhau (cả question và contribution), trả về cùng ID
- Category để trống (theo yêu cầu)
- Tự động thêm timestamp `contributed_at` vào metadata nếu chưa có
- Vector dimension: 768 (PhoBERT model)

**Example Usage:**

```python
import requests

# User clicked "Contribute" button
contribution = {
    "user_question": "Cách cài đặt Python trên Windows?",
    "user_contribution": "Có thể tải từ Microsoft Store hoặc python.org. Nhớ chọn 'Add to PATH' khi cài đặt.",
    "metadata": {
        "user_id": "user_abc123",
        "source": "web_interface"
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/contribution",
    json=contribution
)

if response.status_code == 200:
    result = response.json()
    print(f"✅ Contribution saved: {result['id']}")
```

---

### Delete

#### `DELETE /api/v1/records/{table}/{id}`

Xóa một record theo ID.

**Response:**
```json
{
  "success": true,
  "deleted_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "error": "Bad Request",
  "message": "Field 'query' is required",
  "code": "MISSING_FIELD"
}
```

### 404 Not Found

```json
{
  "error": "Not Found",
  "message": "Record with ID xxx not found",
  "code": "RECORD_NOT_FOUND"
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal Server Error",
  "message": "Database connection failed",
  "code": "DB_CONNECTION_ERROR"
}
```

---

## Rate Limiting

Hiện tại không có rate limiting. Khuyến nghị cho production:
- 100 requests/minute cho search
- 50 requests/minute cho insert

---

## Examples

### Python

```python
import requests

# Search
response = requests.post(
    "http://localhost:8000/api/v1/search",
    json={
        "query": "Cách đăng ký học phần",
        "top_k": 3
    }
)
results = response.json()

# Insert
response = requests.post(
    "http://localhost:8000/api/v1/insert",
    json={
        "table": "answers",
        "data": {
            "question": "Câu hỏi mới",
            "answer": "Câu trả lời"
        }
    }
)
```

### cURL

```bash
# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Cách đăng ký học phần", "top_k": 3}'

# Insert
curl -X POST http://localhost:8000/api/v1/insert \
  -H "Content-Type: application/json" \
  -d '{"table": "answers", "data": {"question": "Q", "answer": "A"}}'
```

### JavaScript

```javascript
// Search
const response = await fetch('http://localhost:8000/api/v1/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'Cách đăng ký học phần',
    top_k: 3
  })
});
const results = await response.json();
```
