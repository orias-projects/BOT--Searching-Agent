# Cấu trúc dự án

```
PY--AI-RAG/				# gốc dự án
├── assets/				# tài nguyên tĩnh (doc, ảnh, ex.*.json)
│   ├── documents/			# tài liệu mẫu
│   ├── images/				# ảnh dùng chung
│   └── resources/			# ex.exceptions, ex.markers, ex.status
│
├── configs/				# cấu hình app (đường dẫn, model, DB)
│
├── databases/				# dữ liệu sinh ra khi chạy
│   ├── .sql/				# script / schema SQL
│   ├── jsons/				# JSON RAG: Raw, Levels, Struct, Segment
│   └── vectors/			# FAISS, PG, SQLite vector index
│
├── models/				# model ML (cache, export)
│   ├── configs/			# cấu hình từng model
│   ├── exported/			# model export (ONNX, v.v.)
│   └── resource/			# Sentence Transformer, Summarizer cache
│
├── private/				# nội bộ: data, docs, prompt, script
│   ├── data/				# data riêng dev/test
│   ├── docs/				# tài liệu nội bộ
│   ├── prompts/			# prompt mẫu LLM/RAG
│   └── scripts/			# merge_data, build_pg/sqlite_index, v.v.
│
├── public/				# nội dung phục vụ người dùng
│   ├── docs/				# tài liệu hướng dẫn
│   ├── shared/				# frontend tĩnh (index.html)
│   └── venv/				# virtualenv (nếu đặt trong project)
│
├── src/				# source code
│   ├── backends/			# API, core, data, infra
│   │   ├── api/			# HTTP API
│   │   │   ├── middlewares/		# CORS, auth, logging
│   │   │   └── v1/			# FastAPI app, route /search, /summarize
│   │   ├── core/			# logic RAG
│   │   │   ├── services/		# PDF, chunk, vector, search, summarizer
│   │   │   └── usecases/		# DocumentPipeline
│   │   ├── data/			# layer dữ liệu
│   │   │   ├── models/			# entity, DTO
│   │   │   └── repositories/		# truy cập DB/file
│   │   └── infra/			# model loader, Docker
│   │
│   ├── frontends/			# giao diện người dùng
│   │   ├── assets/			# JS, CSS, img
│   │   │   ├── app/			# JS Script
│   │   │   ├── css/			# CSS Style
│   │   │   └── img/			# ảnh, Logo, Banner, ...
│   │   └── views/			# component, helper, trang
│   │       ├── common/			# component dùng chung
│   │       ├── helpers/		# tiện ích view
│   │       └── pages/			# từng trang
│   │
│   └── scripts/			# script gắn với code src
│
├── test/				# test, notebook
│   ├── interfaces/			# test giao diện / contract API
│   ├── notebooks/			# Jupyter thử nghiệm
│
├── uploads/				# file người dùng tải lên
│   ├── images/				# Ảnh tài liệu scan
│   └── pdfs/				# PDF đầu vào pipeline
└── README.md
```

---

## Giải thích thư mục

Mục đích từng folder/subfolder — dùng để chứa logic hoặc dữ liệu liên quan đến gì.

### Gốc dự án

| Đường dẫn                | Mục đích                                                                                                                           |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **assets/**            | Tài nguyên tĩnh dùng chung (không phải source code): tài liệu mẫu, ảnh, file cấu hình ngoài code.                        |
| **assets/documents/**  | Tài liệu mẫu hoặc file đính kèm tham chiếu (PDF, Word, v.v.).                                                                 |
| **assets/images/**     | Hình ảnh dùng cho tài liệu, demo hoặc tài nguyên UI.                                                                          |
| **assets/resources/**  | File cấu hình/nguồn dữ liệu cho pipeline: ex.exceptions.json, ex.markers.json, ex.status.json (từ vựng, marker, trạng thái). |
| **configs/**           | Cấu hình ứng dụng: đường dẫn, tên model, DB (PostgreSQL/SQLite), biến dùng trong toàn dự án.                            |
| **databases/**         | Dữ liệu sinh ra khi chạy: SQL, JSON trung gian, vector index.                                                                      |
| **databases/.sql/**    | Script SQL hoặc schema/backup liên quan database.                                                                                   |
| **databases/jsons/**   | JSON trung gian RAG: Raw, Levels, Struct, Segment, Schema theo từng tên PDF (ví dụ HNMU, Categories).                             |
| **databases/vectors/** | Vector store: file FAISS (.faiss), mapping/mapData/mapChunk (.json), hoặc file SQLite (.db) khi dùng sqlite-vec.                    |
| **models/**            | Model ML đã tải hoặc export: encoder, summarizer, config.                                                                         |
| **models/configs/**    | Cấu hình riêng cho từng model (nếu có).                                                                                         |
| **models/exported/**   | Model đã export (ONNX, TorchScript, v.v.) để deploy.                                                                              |
| **models/resource/**   | Model đã cache (Sentence Transformer, Summarizer) theo đường dẫn trong config.                                                  |
| **private/**           | Nội dung nội bộ: data riêng, tài liệu, prompt, script không thuộc app chính.                                                 |
| **private/data/**      | Dữ liệu riêng cho dev/test hoặc script (Excel, CSV, v.v.).                                                                        |
| **private/docs/**      | Tài liệu nội bộ, ghi chú kỹ thuật.                                                                                             |
| **private/prompts/**   | Prompt mẫu cho LLM/rag (nếu dùng).                                                                                                 |
| **private/scripts/**   | Script one-off: merge_data, convert_excel, build_pg_index, build_sqlite_index, start_llm_server, common_db.                           |
| **public/**            | Nội dung phục vụ người dùng cuối: tài liệu public, UI shared, venv (nếu đặt ở đây).                                    |
| **public/docs/**       | Tài liệu hướng dẫn người dùng / API docs.                                                                                     |
| **public/shared/**     | Frontend tĩnh dùng chung: index.html, JS/CSS được mở khi chạy run.py.                                                          |
| **public/venv/**       | Virtualenv (nếu đặt trong project).                                                                                                |
| **src/**               | Toàn bộ source code: backends (API + core + data + infra), frontends, scripts.                                                      |
| **test/**              | Test và notebook: E2E, giao diện test, thử nghiệm.                                                                                |
| **test/interfaces/**   | Test giao diện hoặc contract API.                                                                                                   |
| **test/notebooks/**    | Jupyter notebook thử nghiệm, phân tích.                                                                                           |
| **uploads/**           | File người dùng tải lên khi chạy app.                                                                                           |
| **uploads/images/**    | Ảnh upload.                                                                                                                          |
| **uploads/pdfs/**      | PDF upload (đầu vào cho pipeline trích xuất/tóm tắt/phân loại).                                                              |

### src/backends — Logic backend

| Đường dẫn                             | Mục đích                                                                                                                                                               |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **src/backends/api/**               | HTTP API: route, middleware.                                                                                                                                              |
| **src/backends/api/middlewares/**   | Middleware: CORS, auth, logging, xử lý request/response chung.                                                                                                          |
| **src/backends/api/v1/**            | Phiên bản API v1: app FastAPI, route /, /health, /process_pdf, /search, /summarize.                                                                                     |
| **src/backends/core/**              | Logic nghiệp vụ RAG: services (trích xuất, embedding, search, tóm tắt) và usecases (pipeline).                                                                     |
| **src/backends/core/services/**     | Service từng bước: PDF quality check, extract, merge, chunk (master/under), schema, FAISS/PG/SQLite vector store, search, rerank, summarizer, utils (JSON, text, PDF). |
| **src/backends/core/usecases/**     | Use case tổng hợp: pipelines (DocumentPipeline — load config, models, index; process PDF, search, summarize).                                                          |
| **src/backends/data/**              | Layer dữ liệu: định nghĩa model dữ liệu và repository (nếu tách khỏi services).                                                                                |
| **src/backends/data/models/**       | Định nghĩa cấu trúc dữ liệu (entity, DTO).                                                                                                                         |
| **src/backends/data/repositories/** | Truy cập dữ liệu (DB, file) — có thể dùng chung với logic trong services.                                                                                         |
| **src/backends/infra/**             | Hạ tầng: load model (encoder, summarizer), Docker, các tiện ích chạy môi trường.                                                                                 |

### src/frontends — Giao diện người dùng

| Đường dẫn                          | Mục đích                                          |
| -------------------------------------- | ---------------------------------------------------- |
| **src/frontends/assets/**        | Tài nguyên frontend: app, CSS, hình.              |
| **src/frontends/assets/app/**    | JS/TS hoặc bundle của ứng dụng frontend.         |
| **src/frontends/assets/css/**    | Stylesheet dùng chung.                              |
| **src/frontends/assets/img/**    | Hình ảnh dùng trong giao diện.                   |
| **src/frontends/views/**         | View/template: component chung, helper, từng trang. |
| **src/frontends/views/common/**  | Component hoặc layout dùng chung nhiều trang.     |
| **src/frontends/views/helpers/** | Hàm tiện ích cho view (format, validation, v.v.). |
| **src/frontends/views/pages/**   | View theo từng trang/màn hình.                    |

### src/scripts

| Đường dẫn          | Mục đích                                                                                              |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| **src/scripts/** | Script chạy trong dự án (CLI, cron, build) — khác private/scripts ở chỗ gắn với code trong src. |
