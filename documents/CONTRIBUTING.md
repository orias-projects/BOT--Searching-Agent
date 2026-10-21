# 🤝 Contributing Guide

Cảm ơn bạn đã quan tâm đến việc đóng góp cho dự án RAG System!

## 📋 Mục lục

1. [Code of Conduct](#code-of-conduct)
2. [Cách đóng góp](#cách-đóng-góp)
3. [Development Setup](#development-setup)
4. [Coding Guidelines](#coding-guidelines)
5. [Pull Request Process](#pull-request-process)
6. [Testing](#testing)

---

## Code of Conduct

Dự án này tuân thủ các nguyên tắc:
- ✅ Tôn trọng lẫn nhau
- ✅ Xây dựng, không phá hoại
- ✅ Chấp nhận phản hồi mang tính xây dựng
- ✅ Tập trung vào lợi ích cộng đồng

---

## Cách đóng góp

### Báo cáo Bug

1. Kiểm tra [Issues](../../issues) xem bug đã được báo cáo chưa
2. Nếu chưa, tạo issue mới với:
   - **Mô tả rõ ràng**: Bug là gì?
   - **Cách tái hiện**: Các bước để reproduce
   - **Kết quả mong đợi**: Nên ra sao
   - **Kết quả thực tế**: Đang ra sao
   - **Môi trường**: OS, Python version, PostgreSQL version
   - **Logs**: Error messages, stack traces

**Template:**
```markdown
**Bug Description:**
[Mô tả ngắn gọn bug]

**Steps to Reproduce:**
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior:**
[Nên hoạt động như thế nào]

**Actual Behavior:**
[Đang hoạt động như thế nào]

**Environment:**
- OS: Windows 11
- Python: 3.11.5
- PostgreSQL: 14.9
- pgvector: 0.5.0

**Logs:**
```
[Paste error logs here]
```
```

### Đề xuất tính năng

1. Kiểm tra [Issues](../../issues) xem feature đã được đề xuất chưa
2. Tạo issue với label `enhancement`:
   - **Use case**: Tại sao cần feature này?
   - **Đề xuất giải pháp**: Nên implement như thế nào?
   - **Alternatives**: Các cách khác đã xem xét?

**Template:**
```markdown
**Feature Request:**
[Tóm tắt tính năng]

**Problem to Solve:**
[Vấn đề hiện tại là gì]

**Proposed Solution:**
[Đề xuất giải pháp]

**Alternatives Considered:**
[Các phương án khác]

**Additional Context:**
[Thêm thông tin nếu có]
```

### Submit Pull Request

Xem [Pull Request Process](#pull-request-process) bên dưới.

---

## Development Setup

### 1. Fork & Clone

```bash
# Fork repository trên GitHub (click "Fork" button)

# Clone fork của bạn
git clone https://github.com/YOUR_USERNAME/BOT--RAG-Agent.git
cd BOT--RAG-Agent

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/BOT--RAG-Agent.git
```

### 2. Setup Development Environment

```powershell
# Tạo virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (nếu có)
pip install -r requirements-dev.txt

# Setup pre-commit hooks (nếu có)
pre-commit install
```

### 3. Setup Database

```powershell
# Chạy setup script
.\setup_native.ps1

# Hoặc manual setup
psql -U postgres -c "CREATE DATABASE rag_vectors;"
psql -U postgres -d rag_vectors -f databases\.sql\extension.sql
psql -U postgres -d rag_vectors -f databases\.sql\schema.sql
psql -U postgres -d rag_vectors -f databases\.sql\index.sql
```

### 4. Create .env

```powershell
cp .env.example .env
# Edit .env with your settings
```

### 5. Verify Setup

```powershell
# Test database connection
python -c "from src.backends.database.pgConnection import PGConnection; PGConnection()"

# Run tests (if available)
pytest

# Start server
python run.py
```

---

## Coding Guidelines

### Python Style

Tuân thủ [PEP 8](https://pep8.org/):

```python
# Good
def calculate_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors.
    
    Args:
        vector_a: First vector
        vector_b: Second vector
        
    Returns:
        Cosine similarity score (0.0 - 1.0)
    """
    return np.dot(vector_a, vector_b) / (
        np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    )

# Bad
def calc_sim(a,b):
    return np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))
```

### Docstrings

Sử dụng Google style docstrings:

```python
def search_vector(query: str, top_k: int = 5) -> List[Dict]:
    """Search for similar vectors in the database.
    
    Args:
        query: Search query text
        top_k: Number of results to return (default: 5)
        
    Returns:
        List of search results with scores and metadata
        
    Raises:
        ValueError: If query is empty
        DatabaseError: If database connection fails
        
    Examples:
        >>> results = search_vector("sinh viên", top_k=3)
        >>> print(results[0]['score'])
        0.95
    """
    if not query:
        raise ValueError("Query cannot be empty")
    # ... implementation
```

### Type Hints

Luôn sử dụng type hints:

```python
from typing import List, Dict, Optional, Union

def process_results(
    results: List[Dict[str, any]],
    threshold: float = 0.7,
    max_results: Optional[int] = None
) -> List[Dict[str, any]]:
    """Process search results."""
    # ... implementation
```

### Imports

Sắp xếp imports theo thứ tự:

```python
# 1. Standard library
import os
import sys
from typing import List, Dict

# 2. Third-party packages
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 3. Local imports
from src.backends.database.pgConnection import PGConnection
from src.backends.core.services.embedding import EmbeddingService
```

### Error Handling

Luôn handle exceptions cụ thể:

```python
# Good
try:
    connection = PGConnection()
except psycopg2.OperationalError as e:
    logger.error(f"Database connection failed: {e}")
    raise DatabaseConnectionError("Cannot connect to PostgreSQL") from e
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# Bad
try:
    connection = PGConnection()
except:
    pass
```

### Logging

Sử dụng logging thay vì print:

```python
import logging

logger = logging.getLogger(__name__)

# Good
logger.info("Starting vector search")
logger.debug(f"Query: {query}, Top K: {top_k}")
logger.error(f"Search failed: {error}")

# Bad
print("Starting vector search")
print(f"Query: {query}")
```

### SQL Queries

Luôn dùng parameterized queries:

```python
# Good
cursor.execute(
    "SELECT * FROM bases WHERE id = %s",
    (record_id,)
)

# Bad - SQL injection risk!
cursor.execute(
    f"SELECT * FROM bases WHERE id = '{record_id}'"
)
```

### File Organization

```
src/backends/api/v1/
├── __init__.py          # Package initialization
├── vector_api.py        # Vector search endpoints
├── models.py            # Pydantic models
└── dependencies.py      # FastAPI dependencies
```

Mỗi file nên có single responsibility.

---

## Pull Request Process

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name

# Naming conventions:
# - feature/add-authentication
# - bugfix/fix-search-timeout
# - refactor/optimize-embedding
# - docs/update-readme
```

### 2. Make Changes

```bash
# Make your changes
# Test thoroughly
# Commit with clear messages

git add .
git commit -m "feat: add user authentication"

# Commit message format:
# - feat: new feature
# - fix: bug fix
# - docs: documentation
# - refactor: code restructuring
# - test: adding tests
# - chore: maintenance
```

### 3. Keep Branch Updated

```bash
# Regularly sync with upstream
git fetch upstream
git rebase upstream/main

# Resolve conflicts if any
git add .
git rebase --continue
```

### 4. Push Changes

```bash
git push origin feature/your-feature-name
```

### 5. Create Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your branch
4. Fill in PR template:

```markdown
## Description
[Describe what this PR does]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- Changed X to Y
- Added Z functionality
- Fixed bug in W

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added/updated
- [ ] All tests pass

## Screenshots (if applicable)
[Add screenshots here]

## Related Issues
Closes #123
```

### 6. Code Review

- Respond to reviewer comments
- Make requested changes
- Push updates to same branch (PR auto-updates)
- Request re-review after changes

### 7. Merge

Once approved:
- Maintainer will merge PR
- Delete feature branch
- Update local main:

```bash
git checkout main
git pull upstream main
git branch -d feature/your-feature-name
```

---

## Testing

### Unit Tests

```python
# tests/test_vector_search.py
import pytest
from src.backends.core.services.vectorSearch import VectorSearch

def test_search_returns_results():
    """Test that search returns results."""
    service = VectorSearch()
    results = service.search("test query", top_k=5)
    
    assert len(results) <= 5
    assert all('score' in r for r in results)
    assert all('context' in r for r in results)

def test_search_empty_query():
    """Test that empty query raises error."""
    service = VectorSearch()
    
    with pytest.raises(ValueError):
        service.search("", top_k=5)
```

### Integration Tests

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from src.backends.api.v1.vector_api import app

client = TestClient(app)

def test_vector_search_endpoint():
    """Test vector search API endpoint."""
    response = client.post(
        "/api/v1/search/vector",
        json={"query": "test", "top_k": 3}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) <= 3
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_vector_search.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v
```

---

## Areas to Contribute

### 🔴 High Priority

- [ ] Add authentication & authorization
- [ ] Implement rate limiting
- [ ] Add comprehensive tests
- [ ] Performance optimization

### 🟡 Medium Priority

- [ ] Admin panel for data management
- [ ] Data pipeline for document import
- [ ] Monitoring & metrics
- [ ] Docker deployment

### 🟢 Low Priority / Nice to Have

- [ ] Multi-language support
- [ ] Advanced search filters
- [ ] Export/import functionality
- [ ] Search analytics

---

## Questions?

- 📖 Check [QUICKSTART.md](QUICKSTART.md) and [DEPLOYMENT.md](DEPLOYMENT.md)
- 💬 Open a [Discussion](../../discussions)
- 🐛 Report [Issues](../../issues)
- 📧 Contact maintainers

---

**Cảm ơn bạn đã đóng góp! 🙏**
