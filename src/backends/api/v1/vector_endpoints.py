"""
FastAPI endpoints for PostgreSQL Vector Search API.

Endpoints:
- POST /api/v1/vector/search - Search semantic
- POST /api/v1/vector/insert - Insert records
- PUT /api/v1/vector/{id} - Update record
- DELETE /api/v1/vector/{id} - Delete record
- GET /api/v1/vector/{id} - Get record by ID
- GET /api/v1/health - Health check
- GET /api/v1/stats - Statistics
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService
from src.backends.core.services.enhancedEmbedding import EnhancedEmbeddingService
from src.backends.core.services.pgVectorInsert import VectorInsertService
from src.backends.core.services.pgVectorSearch import PriorityVectorSearchService
from src.scripts.dbTools.pgSchemaManager import PostgreSQLSchemaManager
from src.backends.core.services.pgIndexManager import PostgreSQLIndexManager
from src.backends.core.services.pgMonitoringService import PostgreSQLMonitoringService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== Request/Response Models ====================


class VectorInsertRequest(BaseModel):
    """Insert record request."""
    table_name: str = Field(..., description="Target table: bases, answers, crawls, respons, chunks")
    data: Dict[str, Any] = Field(..., description="JSON data to insert")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")

    class Config:
        example = {
            "table_name": "answers",
            "data": {
                "question": "How to learn Python?",
                "answer": "Start with basics and practice...",
                "topic": "Learning"
            },
            "metadata": {"author": "dev_team", "verified": True}
        }


class VectorBatchInsertRequest(BaseModel):
    """Batch insert records request."""
    table_name: str = Field(..., description="Target table")
    records: List[Dict[str, Any]] = Field(..., description="List of records to insert")

    class Config:
        example = {
            "table_name": "answers",
            "records": [
                {"question": "Q1", "answer": "A1"},
                {"question": "Q2", "answer": "A2"},
            ]
        }


class VectorInsertResponse(BaseModel):
    """Insert record response."""
    success: bool
    id: Optional[str] = None
    message: str


class VectorBatchInsertResponse(BaseModel):
    """Batch insert response."""
    success: bool
    inserted_count: int
    ids: List[str]
    message: str


class VectorSearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., description="Search query text")
    top_k: int = Field(5, description="Number of results to return")
    table: Optional[str] = Field(None, description="Specific table to search (optional)")

    class Config:
        example = {
            "query": "How do I install Python?",
            "top_k": 5
        }


class VectorSearchResult(BaseModel):
    """Single search result."""
    id: str
    source: str
    score: float
    data: Dict[str, Any]
    priority_bonus: float
    matched_fields: Optional[List[str]] = None


class VectorSearchResponse(BaseModel):
    """Search response."""
    success: bool
    results: List[VectorSearchResult]
    total_results: int
    search_time_ms: Optional[float] = None
    message: Optional[str] = None


class VectorUpdateRequest(BaseModel):
    """Update record request."""
    data: Optional[Dict[str, Any]] = Field(None, description="New data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="New metadata")
    regenerate_vectors: bool = Field(True, description="Regenerate embeddings from new data")


class VectorUpdateResponse(BaseModel):
    """Update response."""
    success: bool
    message: str


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    database_connection: bool
    pgvector_installed: bool
    tables_count: int
    tables_status: Dict[str, str]


class StatsResponse(BaseModel):
    """Statistics response."""
    total_records: int
    table_stats: Dict[str, Dict[str, Any]]
    database_size: Optional[str] = None


# ==================== Initialize Router ====================

router = APIRouter(prefix="/api/v1", tags=["vector"])

# Global service instances
_connection_service: Optional[PostgreSQLConnectionService] = None
_embedding_service: Optional[EnhancedEmbeddingService] = None
_insert_service: Optional[VectorInsertService] = None
_search_service: Optional[PriorityVectorSearchService] = None
_schema_manager: Optional[PostgreSQLSchemaManager] = None
_index_manager: Optional[PostgreSQLIndexManager] = None
_monitoring_service: Optional[PostgreSQLMonitoringService] = None


def get_services():
    """Initialize or get existing services."""
    global (
        _connection_service,
        _embedding_service,
        _insert_service,
        _search_service,
        _schema_manager,
        _index_manager,
        _monitoring_service,
    )

    if _connection_service is None:
        logger.info("Initializing services...")
        _connection_service = PostgreSQLConnectionService()
        _embedding_service = EnhancedEmbeddingService()
        _insert_service = VectorInsertService(_embedding_service, _connection_service)
        _search_service = PriorityVectorSearchService(_embedding_service, _connection_service)
        _schema_manager = PostgreSQLSchemaManager(_connection_service)
        _index_manager = PostgreSQLIndexManager(_connection_service)
        _monitoring_service = PostgreSQLMonitoringService(
            _connection_service, _schema_manager, _index_manager
        )
        logger.info("✅ Services initialized")

    return {
        "connection": _connection_service,
        "embedding": _embedding_service,
        "insert": _insert_service,
        "search": _search_service,
        "schema": _schema_manager,
        "index": _index_manager,
        "monitoring": _monitoring_service,
    }


# ==================== Search Endpoints ====================


@router.post(
    "/search",
    response_model=VectorSearchResponse,
    summary="Search vectors",
    description="Perform semantic search across vector database"
)
def search(request: VectorSearchRequest):
    """
    Search the vector database.
    
    - **query**: Search query text
    - **top_k**: Number of results to return
    - **table**: Optional specific table to search
    """
    try:
        services = get_services()
        search_service = services["search"]

        import time
        start_time = time.time()

        if request.table:
            # Search specific table
            results = search_service.search_in_table(
                table_name=request.table,
                query=request.query,
                top_k=request.top_k,
            )
            results_list = []
            for result in results:
                results_list.append(
                    VectorSearchResult(
                        id=result["id"],
                        source=result["source"],
                        score=result["final_score"],
                        data=result["data"],
                        priority_bonus=result.get("priority_bonus", 0),
                    )
                )
        else:
            # Full 3-stage search
            response = search_service.search(
                query=request.query,
                top_k=request.top_k,
            )

            if response["success"]:
                result = response["result"]
                results_list = [
                    VectorSearchResult(
                        id=result["id"],
                        source=result["source"],
                        score=result["final_score"],
                        data=result["data"],
                        priority_bonus=result.get("priority_bonus", 0),
                    )
                ]
            else:
                results_list = []

        elapsed_ms = (time.time() - start_time) * 1000

        return VectorSearchResponse(
            success=len(results_list) > 0,
            results=results_list,
            total_results=len(results_list),
            search_time_ms=elapsed_ms,
            message="Search completed" if results_list else "No results found",
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Insert Endpoints ====================


@router.post(
    "/insert",
    response_model=VectorInsertResponse,
    summary="Insert vector record",
    description="Insert a single record with vectors"
)
def insert(request: VectorInsertRequest):
    """
    Insert a single record.
    
    - **table_name**: Target table (bases, answers, crawls, respons, chunks)
    - **data**: JSON data to insert
    - **metadata**: Optional metadata tags
    """
    try:
        services = get_services()
        insert_service = services["insert"]

        record_id = insert_service.insert_record(
            table_name=request.table_name,
            json_data=request.data,
            metadata=request.metadata,
        )

        return VectorInsertResponse(
            success=True,
            id=record_id,
            message=f"Record inserted successfully: {record_id}",
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Insert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/batch-insert",
    response_model=VectorBatchInsertResponse,
    summary="Batch insert records",
    description="Insert multiple records in batch (more efficient)"
)
def batch_insert(request: VectorBatchInsertRequest):
    """
    Insert multiple records in batch.
    
    - **table_name**: Target table
    - **records**: List of records to insert
    """
    try:
        services = get_services()
        insert_service = services["insert"]

        record_ids = insert_service.insert_batch(
            table_name=request.table_name,
            json_data_list=request.records,
        )

        return VectorBatchInsertResponse(
            success=True,
            inserted_count=len(record_ids),
            ids=record_ids,
            message=f"Batch inserted {len(record_ids)} records successfully",
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Batch insert error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Record Management Endpoints ====================


@router.get(
    "/record/{table}/{record_id}",
    summary="Get record by ID",
    description="Retrieve a specific record"
)
def get_record(table: str, record_id: str):
    """
    Get a record by ID.
    
    - **table**: Table name
    - **record_id**: Record UUID
    """
    try:
        services = get_services()
        insert_service = services["insert"]

        record = insert_service.get_record(table, record_id)

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        return {"success": True, "record": record}

    except Exception as e:
        logger.error(f"Get record error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/record/{table}/{record_id}",
    response_model=VectorUpdateResponse,
    summary="Update record",
    description="Update an existing record"
)
def update_record(table: str, record_id: str, request: VectorUpdateRequest):
    """
    Update a record.
    
    - **table**: Table name
    - **record_id**: Record UUID
    - **data**: New JSON data (optional)
    - **metadata**: New metadata (optional)
    - **regenerate_vectors**: Regenerate embeddings if data changed
    """
    try:
        services = get_services()
        insert_service = services["insert"]

        success = insert_service.update_record(
            table_name=table,
            record_id=record_id,
            json_data=request.data,
            metadata=request.metadata,
            regenerate_vectors=request.regenerate_vectors,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Record not found")

        return VectorUpdateResponse(
            success=True,
            message=f"Record {record_id} updated successfully",
        )

    except Exception as e:
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/record/{table}/{record_id}",
    response_model=VectorUpdateResponse,
    summary="Delete record",
    description="Delete a record"
)
def delete_record(table: str, record_id: str):
    """
    Delete a record.
    
    - **table**: Table name
    - **record_id**: Record UUID
    """
    try:
        services = get_services()
        insert_service = services["insert"]

        success = insert_service.delete_record(table, record_id)

        if not success:
            raise HTTPException(status_code=404, detail="Record not found")

        return VectorUpdateResponse(
            success=True,
            message=f"Record {record_id} deleted successfully",
        )

    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health & Stats Endpoints ====================


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check database and service health"
)
def health_check():
    """
    Check the health of the database and services.
    """
    try:
        services = get_services()
        monitoring_service = services["monitoring"]
        schema_manager = services["schema"]

        conn_ok, _ = monitoring_service.check_connection()
        pgvec_ok, _ = monitoring_service.check_pgvector_extension()

        # Get table statuses
        table_statuses = {}
        for table in ["bases", "answers", "crawls", "respons", "chunks"]:
            exists = schema_manager.table_exists(table)
            table_statuses[table] = "✅ OK" if exists else "❌ Missing"

        return HealthCheckResponse(
            status="✅ Healthy" if (conn_ok and pgvec_ok) else "⚠️ Issues",
            database_connection=conn_ok,
            pgvector_installed=pgvec_ok,
            tables_count=sum(1 for status in table_statuses.values() if "✅" in status),
            tables_status=table_statuses,
        )

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="❌ Error",
            database_connection=False,
            pgvector_installed=False,
            tables_count=0,
            tables_status={},
        )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get statistics",
    description="Get database statistics"
)
def get_stats():
    """
    Get database statistics.
    """
    try:
        services = get_services()
        monitoring_service = services["monitoring"]
        schema_manager = services["schema"]

        table_stats = schema_manager.get_all_table_stats()
        db_size_info = monitoring_service.get_database_size()

        total_records = sum(
            stat["row_count"] for stat in table_stats.values()
            if stat and stat.get("row_count")
        )

        return StatsResponse(
            total_records=total_records,
            table_stats=table_stats,
            database_size=db_size_info.get("total_size") if db_size_info else None,
        )

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/detailed-health",
    summary="Detailed health report",
    description="Get comprehensive health and performance report"
)
def detailed_health():
    """
    Get a detailed health report including performance metrics.
    """
    try:
        services = get_services()
        monitoring_service = services["monitoring"]
        report = monitoring_service.generate_full_health_report()
        return {"success": True, "report": report}

    except Exception as e:
        logger.error(f"Detailed health error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
