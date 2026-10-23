"""
FastAPI gateway: /, /health, /process_pdf, /search, /summarize.
"""
import os
import time
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

API_SECRET = os.getenv("API_SECRET", "").strip()

try:
    print("Đang tải pipelines (models, indexes...). Vui lòng chờ...")
    from src.backends.core.usecases.pipelines import (
        get_document_pipeline,
        processPdfPipeline,
        searchPipeline,
        summarizeText,
    )
    print("✅ Đã load pipelines.")
except Exception as e:
    get_document_pipeline = None
    processPdfPipeline = None
    searchPipeline = None
    summarizeText = None
    print(f"⚠️ CRITICAL: Không thể import pipelines: {e}")
    raise e


def requireBearer(authorization: Optional[str] = Header(None)):
    if not API_SECRET:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token != API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")


app = FastAPI(
    title="Document AI API (FastAPI)",
    version="2.0.0",
    description="API xử lý PDF: trích xuất, tóm tắt, tìm kiếm, phân loại.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include vector search API router (new PostgreSQL-based endpoints)
try:
    from src.backends.api.v1.vector_api import router as vector_router
    app.include_router(vector_router)
    print("✅ Vector search API endpoints loaded")
except Exception as e:
    print(f"⚠️ Could not load vector search API (PostgreSQL may not be configured): {e}")


@app.get("/")
def root():
    pipeline = get_document_pipeline() if get_document_pipeline else None
    return {
        "message": "📘 Document AI API đang chạy.",
        "status": "ok",
        "docs": "/docs",
        "pipeline_loaded": pipeline is not None,
    }


@app.get("/health")
def health(_=Depends(requireBearer)):
    pipeline = get_document_pipeline() if get_document_pipeline else None
    app_ok = pipeline is not None
    return {
        "status": "ok",
        "time": time.time(),
        "pipeline_loaded": app_ok,
        "main_index_loaded": pipeline.main_index_loaded if app_ok else False,
    }


@app.post("/process_pdf")
async def processPdf(file: UploadFile = File(...), _=Depends(requireBearer)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF.")
    pdfBytes = await file.read()
    if not processPdfPipeline:
        raise HTTPException(status_code=500, detail="Không tìm thấy processPdfPipeline().")
    try:
        result = processPdfPipeline(pdfBytes)
        return {
            "status": "success",
            "checkstatus": result.get("checkstatus"),
            "summary": result.get("summary"),
            "category": result.get("category"),
        }
    except Exception as e:
        print(f"Lỗi /process_pdf: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý PDF: {str(e)}")


class SearchIn(BaseModel):
    query: str
    k: int = 1


@app.post("/search", response_model=List[dict])
def search(body: SearchIn, _=Depends(requireBearer)):
    q = (body.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="query không được để trống")
    if not searchPipeline:
        raise HTTPException(status_code=500, detail="Không tìm thấy searchPipeline().")
    try:
        results = searchPipeline(q, k=body.k)
        return results
    except Exception as e:
        print(f"Lỗi /search: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tìm kiếm: {str(e)}")


class SummIn(BaseModel):
    text: str
    minInput: int = 256
    maxInput: int = 1024
    minLength: int = 100
    maxLength: int = 200


@app.post("/summarize")
def summarizeText(body: SummIn, _=Depends(requireBearer)):
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text không được để trống")
    if not summarizeText:
        raise HTTPException(status_code=500, detail="Không tìm thấy summarizeText().")
    try:
        summarized = summarizeText(text)
        return {"status": "success", "summary": summarized.get("summaryText", "")}
    except Exception as e:
        print(f"Lỗi /summarize: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tóm tắt: {str(e)}")
