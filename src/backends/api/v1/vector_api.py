"""
Extended API endpoints for PostgreSQL vector search.

New endpoints:
- POST /api/v1/data/{table} - Insert data
- POST /api/v1/search/vector - Priority-based vector search
- GET /api/v1/health/db - Database health check
"""
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

# Import services (lazy load to avoid circular imports)
_embedding_service = None
_connection_service = None
_insert_service = None
_search_service = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def get_services():
    """Lazy initialization of services."""
    global _embedding_service, _connection_service, _insert_service, _search_service
    
    if _connection_service is None:
        # Check if PostgreSQL is enabled
        use_pg_vector = os.getenv("USE_PG_VECTOR", "false").lower() in ("true", "1", "yes")
        if not use_pg_vector:
            raise HTTPException(
                status_code=503,
                detail="PostgreSQL vector search is not enabled. Set USE_PG_VECTOR=true"
            )
        
        try:
            from src.backends.core.services.enhancedEmbedding import create_embedding_service
            from src.backends.core.services.pgConnectionService import get_connection_service
            from src.backends.core.services.pgVectorInsert import VectorInsertService
            from src.backends.core.services.pgVectorSearch import PriorityVectorSearchService
            
            _embedding_service = create_embedding_service()
            _connection_service = get_connection_service()
            _insert_service = VectorInsertService(_embedding_service, _connection_service)
            
            threshold = float(os.getenv("SEARCH_THRESHOLD", "0.7"))
            _search_service = PriorityVectorSearchService(
                _embedding_service,
                _connection_service,
                threshold=threshold
            )
            
            logging.info("✅ Vector search services initialized")
        
        except Exception as e:
            logging.error(f"Failed to initialize vector search services: {e}")
            raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")
    
    return _embedding_service, _connection_service, _insert_service, _search_service


# Router for new endpoints
router = APIRouter(prefix="/api/v1", tags=["Vector Search"])


# ============================================================================
# Request/Response Models
# ============================================================================

class InsertDataRequest(BaseModel):
    """Request model for inserting data."""
    data: Dict[str, Any] = Field(..., description="JSON data to insert")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": {
                    "question": "Làm thế nào để cài đặt Python?",
                    "answer": "Tải Python từ python.org và chạy installer.",
                    "topic": "Installation"
                },
                "metadata": {
                    "author": "dev_team",
                    "tags": ["python", "installation"]
                }
            }
        }


class InsertBatchRequest(BaseModel):
    """Request model for batch insert."""
    data_list: List[Dict[str, Any]] = Field(..., description="List of JSON data to insert")
    metadata_list: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional metadata list")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data_list": [
                    {"question": "Q1", "answer": "A1"},
                    {"question": "Q2", "answer": "A2"}
                ]
            }
        }


class VectorSearchRequest(BaseModel):
    """Request model for vector search."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum score threshold")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "cách cài python",
                "top_k": 5,
                "min_score": 0.7
            }
        }


class SearchInTableRequest(BaseModel):
    """Request model for searching in specific table."""
    query: str = Field(..., description="Search query text")
    table: str = Field(..., description="Table name (bases, answers, crawls, respons, chunks)")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "python installation",
                "table": "answers",
                "top_k": 5
            }
        }


class ContributionRequest(BaseModel):
    """Request model for user contribution (feedback)."""
    user_question: str = Field(..., description="User's original question")
    user_contribution: str = Field(..., description="User's contribution/feedback content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata (e.g., user_id, timestamp)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_question": "Cách cài đặt Python trên Windows?",
                "user_contribution": "Có thể tải từ Microsoft Store hoặc python.org. Nhớ chọn 'Add to PATH' khi cài đặt.",
                "metadata": {
                    "user_id": "user123",
                    "source": "web_chat"
                }
            }
        }


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/data/{table_name}")
async def insert_data(
    table_name: str,
    request: InsertDataRequest,
):
    """
    Insert a record into specified table.
    
    Tables: bases, answers, crawls, respons, chunks
    """
    _, _, insert_service, _ = get_services()
    
    try:
        record_id = insert_service.insert_record(
            table_name=table_name,
            json_data=request.data,
            metadata=request.metadata,
        )
        
        return {
            "success": True,
            "id": record_id,
            "table": table_name,
            "message": "Record inserted successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Insert failed: {e}")
        raise HTTPException(status_code=500, detail=f"Insert failed: {str(e)}")


@router.post("/data/{table_name}/batch")
async def insert_batch(
    table_name: str,
    request: InsertBatchRequest,
):
    """
    Insert multiple records in batch (more efficient).
    
    Tables: bases, answers, crawls, respons, chunks
    """
    _, _, insert_service, _ = get_services()
    
    try:
        record_ids = insert_service.insert_batch(
            table_name=table_name,
            json_data_list=request.data_list,
            metadata_list=request.metadata_list,
        )
        
        return {
            "success": True,
            "count": len(record_ids),
            "ids": record_ids,
            "table": table_name,
            "message": f"{len(record_ids)} records inserted successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Batch insert failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch insert failed: {str(e)}")


@router.post("/search/vector")
async def vector_search(request: VectorSearchRequest):
    """
    Priority-based vector search across all tables.
    
    Algorithm:
    1. Search bases first (threshold check) → return if found
    2. Search all other tables with priority scoring
    3. Return best match or "Not found"
    """
    _, _, _, search_service = get_services()
    
    try:
        # Override threshold if specified
        if request.min_score is not None:
            search_service.threshold = request.min_score
        
        result = search_service.search(
            query=request.query,
            top_k=request.top_k,
            return_not_found_message=True,
        )
        
        return result
    
    except Exception as e:
        logging.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/table")
async def search_in_table(request: SearchInTableRequest):
    """
    Search in a specific table only (for testing or specific use cases).
    """
    _, _, _, search_service = get_services()
    
    try:
        results = search_service.search_in_table(
            table_name=request.table,
            query=request.query,
            top_k=request.top_k,
        )
        
        return {
            "success": True,
            "count": len(results),
            "results": results,
            "table": request.table,
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Table search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/health/db")
async def db_health():
    """
    Check database health and table statistics.
    """
    _, connection_service, _, _ = get_services()
    
    try:
        health = connection_service.check_health()
        return health
    
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/data/{table_name}/{record_id}")
async def get_record(table_name: str, record_id: str):
    """
    Get a record by ID from specified table.
    """
    _, _, insert_service, _ = get_services()
    
    try:
        record = insert_service.get_record(table_name, record_id)
        
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return {
            "success": True,
            "record": record,
            "table": table_name,
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Get record failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get record: {str(e)}")


@router.delete("/data/{table_name}/{record_id}")
async def delete_record(table_name: str, record_id: str):
    """
    Delete a record by ID from specified table.
    """
    _, _, insert_service, _ = get_services()
    
    try:
        deleted = insert_service.delete_record(table_name, record_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Record not found")
        
        return {
            "success": True,
            "message": "Record deleted successfully",
            "table": table_name,
            "id": record_id,
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Delete record failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete record: {str(e)}")


@router.post("/contribution")
async def add_contribution(request: ContributionRequest):
    """
    Add user contribution to 'respons' table.
    
    This endpoint is called when users click "Contribute" button below bot messages.
    Stores the user's original question (Article) and their contribution (Content).
    Automatically generates vector embeddings for semantic search.
    
    Request body:
    - user_question: The question user asked (becomes Article field)
    - user_contribution: User's contribution text (becomes Content field)
    - metadata: Optional metadata (e.g., user_id, timestamp, source)
    
    Response:
    - success: True if inserted
    - id: Record ID (SHA-256 hash of content)
    - table: Always "respons"
    - message: Success message
    """
    _, _, insert_service, _ = get_services()
    
    try:
        # Prepare data for respons table
        # Article = user's question, Content = user's contribution
        json_data = {
            "article": request.user_question.strip(),
            "content": request.user_contribution.strip(),
        }
        
        # Category is empty as requested
        # (embedding service will handle this)
        
        # Add metadata
        metadata = request.metadata or {}
        if "contributed_at" not in metadata:
            from datetime import datetime
            metadata["contributed_at"] = datetime.utcnow().isoformat()
        
        # Insert into respons table
        record_id = insert_service.insert_record(
            table_name="respons",
            json_data=json_data,
            metadata=metadata,
        )
        
        return {
            "success": True,
            "id": record_id,
            "table": "respons",
            "message": "Contribution added successfully. Thank you for improving our knowledge base!"
        }
    
    except Exception as e:
        logging.error(f"Failed to add contribution: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to add contribution: {str(e)}"
        )


# Example: How to include this router in main app.py:
# from src.backends.api.v1.vector_api import router as vector_router
# app.include_router(vector_router)
