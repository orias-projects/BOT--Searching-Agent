"""
Vector insert service: Insert records with full vectors and subvectors.

Handles data insertion into the 5 priority-based tables.
"""
import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from psycopg2.extras import Json

from src.backends.core.services.enhancedEmbedding import EnhancedEmbeddingService
from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class VectorInsertService:
    """Service for inserting records with vectors and subvectors."""
    
    # Valid table names
    VALID_TABLES = {"bases", "answers", "crawls", "respons", "chunks"}
    
    def __init__(
        self,
        embedding_service: EnhancedEmbeddingService,
        connection_service: PostgreSQLConnectionService,
    ):
        """
        Initialize insert service.
        
        Args:
            embedding_service: Embedding service instance
            connection_service: PostgreSQL connection service
        """
        self.embedding_service = embedding_service
        self.connection_service = connection_service
        logging.info("VectorInsertService initialized")
    
    def _validate_table_name(self, table_name: str):
        """Validate table name."""
        if table_name not in self.VALID_TABLES:
            raise ValueError(
                f"Invalid table name: {table_name}. "
                f"Valid tables: {', '.join(sorted(self.VALID_TABLES))}"
            )
    
    def _compute_content_hash(self, context: Dict[str, Any]) -> str:
        """
        Generate UUID v5 based on context for deterministic deduplication.
        
        Uses namespace UUID and SHA-1 hash of content (UUID v5 standard).
        Same content will always generate the same UUID.
        
        Args:
            context: Context dict with article and content
        
        Returns:
            UUID string (36 chars with hyphens)
        """
        # Use a fixed namespace for the RAG system
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
        
        # Create deterministic string from context
        context_str = json.dumps(context, ensure_ascii=False, sort_keys=True)
        
        # Generate UUID v5 (deterministic, based on SHA-1)
        return str(uuid.uuid5(namespace, context_str))
    
    def insert_record(
        self,
        table_name: str,
        json_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        max_depth: int = 3,
    ) -> Optional[str]:
        """
        Insert a single record with context-only embedding (new schema).
        
        Only embeds context (article + content) fields.
        Category fields are stored separately in JSONB.
        
        Args:
            table_name: Target table
            json_data: Full JSON data with context and category
            metadata: Optional metadata
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            UUID of inserted record, or None if duplicate
        """
        self._validate_table_name(table_name)
        
        # Generate embeddings (context-only)
        full_vector, subvectors, category = self.embedding_service.prepare_record_context(
            json_data, max_depth=max_depth
        )
        
        # Extract context for hash
        context = {k: v for k, v in json_data.items() if k in ["article", "content"]}
        
        # Compute content hash (becomes record ID)
        record_id = self._compute_content_hash(context)
        # Prepare metadata
        if metadata is None:
            metadata = {}
        
        # Convert vector to list for pgvector
        vector_list = full_vector.tolist()
        
        # Insert query (new schema: category, context, vectors, vector)
        query = f"""
            INSERT INTO {table_name} (id, category, context, vectors, vector, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        
        params = (
            record_id,
            Json(category) if category else None,
            Json(context),
            Json(subvectors),
            vector_list,
            Json(metadata),
        )
        
        # Execute
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                inserted_id = result[0]
                logging.info(f"Inserted record into {table_name}: {inserted_id}")
                return inserted_id
        
        except Exception as e:
            logging.error(f"Failed to insert record into {table_name}: {e}")
            raise
    
    def insert_batch(
        self,
        table_name: str,
        json_data_list: List[Dict[str, Any]],
        metadata_list: Optional[List[Dict[str, Any]]] = None,
        max_depth: int = 3,
    ) -> List[Optional[str]]:
        """
        Insert multiple records in batch (context-only embedding, new schema).
        
        Args:
            table_name: Target table
            json_data_list: List of full JSON data (with context and category)
            metadata_list: Optional list of metadata
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            List of UUIDs (None for duplicates)
        """
        self._validate_table_name(table_name)
        
        if not json_data_list:
            return []
        
        # Prepare metadata list
        if metadata_list is None:
            metadata_list = [{}] * len(json_data_list)
        elif len(metadata_list) != len(json_data_list):
            raise ValueError("metadata_list length must match json_data_list length")
        
        # Generate embeddings for all records (context-only)
        logging.info(f"Generating context-only embeddings for {len(json_data_list)} records...")
        embeddings_list = self.embedding_service.prepare_batch_context(
            json_data_list, max_depth=max_depth
        )
        
        # Prepare insert data
        insert_data = []
        record_ids = []
        skipped = 0
        
        for json_data, (full_vector, subvectors, category), metadata in zip(
            json_data_list, embeddings_list, metadata_list
        ):
            # Extract context for hash
            context = {k: v for k, v in json_data.items() if k in ["article", "content"]}
            
            # Compute content hash (becomes record ID)
            record_id = self._compute_content_hash(context)
            
            # Prepare metadata
            if metadata is None:
                metadata = {}
            
            record_ids.append(record_id)
            
            insert_data.append((
                record_id,
                Json(category) if category else None,
                Json(context),
                Json(subvectors),
                full_vector.tolist(),
                Json(metadata),
            ))
        
        # Batch insert query (new schema)
        query = f"""
            INSERT INTO {table_name} (id, category, context, vectors, vector, metadata)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        
        # Execute batch insert
        try:
            row_count = self.connection_service.execute_many(query, insert_data)
            logging.info(f"Batch inserted {row_count} records into {table_name} (skipped: {skipped})")
            return record_ids
        
        except Exception as e:
            logging.error(f"Failed to batch insert into {table_name}: {e}")
            raise
    
    def update_record(
        self,
        table_name: str,
        record_id: str,
        json_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        regenerate_vectors: bool = True,
        max_depth: int = 3,
    ) -> bool:
        """
        Update an existing record.
        
        Args:
            table_name: Target table
            record_id: UUID of record to update
            json_data: New JSON data (if None, keep existing)
            metadata: New metadata (if None, keep existing)
            regenerate_vectors: If True, regenerate vectors from new json_data
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            True if updated, False if not found
        """
        self._validate_table_name(table_name)
        
        # Build update query dynamically
        update_parts = []
        params = []
        
        if json_data is not None:
            update_parts.append("jsons = %s")
            params.append(Json(json_data))
            
            if regenerate_vectors:
                # Generate new vectors
                full_vector, subvectors = self.embedding_service.prepare_record(
                    json_data, max_depth=max_depth
                )
                update_parts.append("vectors = %s")
                params.append(full_vector.tolist())
                update_parts.append("subvectors = %s")
                params.append(Json(subvectors))
        
        if metadata is not None:
            update_parts.append("metadata = %s")
            params.append(Json(metadata))
        
        if not update_parts:
            logging.warning("No fields to update")
            return False
        
        # Add record_id to params
        params.append(record_id)
        
        # Update query
        query = f"""
            UPDATE {table_name}
            SET {', '.join(update_parts)}
            WHERE id = %s;
        """
        
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(query, params)
                updated = cursor.rowcount > 0
                if updated:
                    logging.info(f"Updated record in {table_name}: {record_id}")
                else:
                    logging.warning(f"Record not found in {table_name}: {record_id}")
                return updated
        
        except Exception as e:
            logging.error(f"Failed to update record in {table_name}: {e}")
            raise
    
    def delete_record(self, table_name: str, record_id: str) -> bool:
        """
        Delete a record.
        
        Args:
            table_name: Target table
            record_id: UUID of record to delete
        
        Returns:
            True if deleted, False if not found
        """
        self._validate_table_name(table_name)
        
        query = f"DELETE FROM {table_name} WHERE id = %s;"
        
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(query, (record_id,))
                deleted = cursor.rowcount > 0
                if deleted:
                    logging.info(f"Deleted record from {table_name}: {record_id}")
                else:
                    logging.warning(f"Record not found in {table_name}: {record_id}")
                return deleted
        
        except Exception as e:
            logging.error(f"Failed to delete record from {table_name}: {e}")
            raise
    
    def get_record(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.
        
        Args:
            table_name: Target table
            record_id: UUID of record
        
        Returns:
            Record dict or None if not found
        """
        self._validate_table_name(table_name)
        
        query = f"""
            SELECT id, jsons, metadata, created_at, updated_at
            FROM {table_name}
            WHERE id = %s;
        """
        
        result = self.connection_service.execute_query(
            query, (record_id,), fetch="one", dict_cursor=True
        )
        
        if result:
            return dict(result)
        return None


# Example usage
if __name__ == "__main__":
    from src.backends.core.services.enhancedEmbedding import create_embedding_service
    from src.backends.core.services.pgConnectionService import get_connection_service
    
    # Initialize services
    embed_service = create_embedding_service()
    conn_service = get_connection_service()
    insert_service = VectorInsertService(embed_service, conn_service)
    
    # Example: Insert into answers table
    data = {
        "question": "Làm thế nào để cài đặt Python?",
        "answer": "Tải Python từ python.org và chạy installer.",
        "topic": "Installation"
    }
    
    try:
        record_id = insert_service.insert_record("answers", data, metadata={"author": "dev"})
        print(f"Inserted: {record_id}")
        
        # Get record
        record = insert_service.get_record("answers", record_id)
        print(f"Retrieved: {record}")
    
    finally:
        conn_service.close()
