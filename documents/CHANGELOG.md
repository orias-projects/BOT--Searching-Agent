# Changelog

Tất cả các thay đổi quan trọng của dự án sẽ được ghi lại ở đây.

Format dựa theo [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
và dự án tuân theo [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Authentication & authorization system
- Rate limiting for API endpoints
- Admin panel for data management
- Comprehensive test suite
- Docker deployment option
- Monitoring & metrics (Prometheus/Grafana)

---

## [0.2.0] - 2024-01-XX (Current)

### Added
- 🤝 **User Contribution Feature**
  - Modal UI for user contributions
  - POST `/api/v1/contribution` endpoint
  - Auto-generate embeddings for contributions
  - Store in `respons` table with UUID v5 IDs
  - Character counter (10-500 chars)
  - Toast notifications
  - "✅ Đã đóng góp" status indicator

- 📚 **Comprehensive Documentation**
  - `QUICKSTART.md` - Quick setup guide
  - `DEPLOYMENT.md` - Full deployment instructions
  - `CONTRIBUTING.md` - Developer contribution guide
  - `.env.example` - Environment template with detailed comments
  - `docs/CONTRIBUTION_IMPLEMENTATION.md` - Technical implementation
  - `docs/FRONTEND_CONTRIBUTION_GUIDE.md` - Frontend integration guide

- 🔧 **Automated Setup**
  - `setup_native.ps1` - PowerShell setup script
  - Automatic PostgreSQL configuration
  - Virtual environment creation
  - Dependency installation
  - Database initialization
  - .env file generation

- 🔍 **Database Functions**
  - `cosine_similarity(a, b)` SQL function
  - Converts pgvector cosine distance to similarity
  - Added to `databases/.sql/extension.sql`

- 🎨 **UI Improvements**
  - Dark mode contribution modal
  - Better search result formatting
  - Removed automatic numbering from results
  - Improved error messages

### Changed
- 🔄 **ID Generation**
  - Changed from SHA-256 (64 chars) to UUID v5 (36 chars)
  - Deterministic IDs for deduplication
  - Compatible with database UUID column type

- 🗄️ **Database Migration**
  - Migrated from Docker PostgreSQL to native Windows PostgreSQL
  - Updated connection strings
  - Improved connection pool configuration

- 📝 **Documentation Updates**
  - Enhanced README.md with better structure
  - Added troubleshooting sections
  - Improved API documentation in API.md
  - Updated DATABASE.md with schema details

### Fixed
- 🐛 **500 Error on Vector Search**
  - Fixed missing `cosine_similarity()` function
  - Updated all SQL queries to use custom function
  
- 🐛 **Import Errors**
  - Fixed undefined `index` variable in logging
  - Updated import paths after restructuring

- 🐛 **UI Display Issues**
  - Removed hardcoded "1." from search results
  - Fixed Article field numbering issue
  - Improved result formatting

- 🐛 **Database Connection**
  - Fixed password encoding for special characters
  - Added URL encoding for DATABASE_URL
  - Improved error messages

### Security
- 🔐 Added `.env` to `.gitignore`
- 🔐 Documented password URL encoding requirements
- 🔐 Added security notes to documentation

---

## [0.1.0] - 2024-XX-XX

### Added
- ✨ Initial release
- 🔍 Vector search with PostgreSQL pgvector
- 🇻🇳 Vietnamese language support (PhoBERT)
- 💬 Basic chat interface
- 📊 Priority system for search results
- 🗄️ 5-table database schema (bases, answers, chunks, crawls, respons)
- 🌐 FastAPI backend
- 🎨 HTML/CSS/JavaScript frontend

### Tech Stack
- Python 3.8+
- FastAPI
- PostgreSQL 12+ with pgvector
- PhoBERT embedding model (768-dim)
- HNSW indexing for fast vector search

---

## Version History

| Version | Date | Key Features |
|---------|------|--------------|
| 0.2.0 | 2024-01-XX | User contributions, comprehensive docs, automated setup |
| 0.1.0 | 2024-XX-XX | Initial release with vector search |

---

## Migration Guides

### Upgrading to 0.2.0

**Database:**
```sql
-- Add cosine_similarity function
CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector)
RETURNS float
AS $$
    SELECT 1 - (a <=> b);
$$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE;
```

**Environment:**
- Update `.env` with new format (see `.env.example`)
- Ensure password is URL-encoded in DATABASE_URL

**Code:**
- No breaking changes
- Existing APIs remain compatible

---

## Notes

### Version Numbering
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Process
1. Update CHANGELOG.md
2. Update version in `__init__.py` or `setup.py`
3. Create git tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
4. Push tag: `git push origin v0.2.0`
5. Create GitHub release with notes from CHANGELOG

---

## Links

- [GitHub Repository](https://github.com/yourrepo)
- [Documentation](./README.md)
- [Issues](https://github.com/yourrepo/issues)
- [Pull Requests](https://github.com/yourrepo/pulls)

---

**For detailed commit history, see [GitHub Commits](https://github.com/yourrepo/commits)**
