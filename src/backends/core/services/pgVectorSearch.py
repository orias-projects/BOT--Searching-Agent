"""
Priority-based vector search service.

Implements the tiered search algorithm:
1. Search bases first (threshold 0.7) → immediate return if found
2. If not found, search all other tables with priority scoring
3. Return best match or "Not found"
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.backends.core.services.enhancedEmbedding import EnhancedEmbeddingService
from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class PriorityVectorSearchService:
    """Priority-based vector search with subvectors support."""
    
    # Priority bonuses for each table
    PRIORITY_BONUSES = {
        "bases": 0.05,      # 0.05 bonus for bases
        "answers": 0.03,
        "crawls": 0.02,
        "respons": 0.01,
        "chunks": 0.00,
    }
    
    # Minimum score thresholds for each table
    MIN_SCORES = {
        "bases": 0.60,       # Bases minimum score threshold
        "answers": 0.55,     # Answers minimum score threshold
        "crawls": 0.50,      # Crawls minimum score threshold
        "respons": 0.50,     # Respons minimum score threshold
        "chunks": 0.45,      # Chunks minimum score threshold
    }
    
    # Tables to search in stage 2 (all tables, de-prioritized bases)
    STAGE2_TABLES = ["bases", "answers", "crawls", "respons", "chunks"]
    
    def __init__(
        self,
        embedding_service: EnhancedEmbeddingService,
        connection_service: PostgreSQLConnectionService,
        threshold: float = 0.7,
    ):
        """
        Initialize search service.
        
        Args:
            embedding_service: Embedding service instance
            connection_service: PostgreSQL connection service
            threshold: Minimum similarity threshold (default 0.7)
        """
        self.embedding_service = embedding_service
        self.connection_service = connection_service
        self.threshold = threshold
        logging.info(f"PriorityVectorSearchService initialized (threshold: {threshold})")
    
    def _compute_subvector_similarity(
        self,
        query_vector: np.ndarray,
        subvectors_json: Dict[str, List[float]]
    ) -> float:
        """
        Compute maximum similarity between query and all subvectors.
        
        Args:
            query_vector: Query embedding vector
            subvectors_json: Dict of field embeddings
        
        Returns:
            Maximum similarity score
        """
        if not subvectors_json:
            return 0.0
        
        max_sim = 0.0
        
        # Handle None or empty subvectors
        if not subvectors_json:
            return 0.0
            
        for field_name, field_vector in subvectors_json.items():
            if not field_vector or not isinstance(field_vector, (list, tuple)):
                continue
            
            try:
                # Convert to numpy
                field_vec = np.array(field_vector, dtype=np.float32)
                
                # Skip if empty or wrong shape
                if field_vec.size == 0:
                    continue
                
                # Cosine similarity (vectors should be normalized already)
                similarity = float(np.dot(query_vector, field_vec))
                
                if similarity > max_sim:
                    max_sim = similarity
            except (TypeError, ValueError):
                # Skip malformed vectors
                continue
        
        return max_sim
    
    def search_bases(
        self,
        query: str,
        top_k: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Search in bases table (Stage 1, new schema).
        
        Searches using context field (article + content) only.
        Bases require minimum score of 0.85.
        
        Args:
            query: Query text
            top_k: Number of candidates to retrieve
        
        Returns:
            Best match dict or None if not found
        """
        # Embed query (simple text embedding)
        query_vector = self.embedding_service.embed_text(query)
        query_list = query_vector.tolist()
        
        # Get minimum score for bases table
        min_score_bases = self.MIN_SCORES["bases"]
        
        # Search using vector column (full embedding of context)
        search_query = """
            SELECT id, context, category, vectors,
                   cosine_similarity(vector, %s::vector) as vector_similarity
            FROM bases
            WHERE cosine_similarity(vector, %s::vector) >= %s
            ORDER BY vector_similarity DESC
            LIMIT %s;
        """
        
        results = self.connection_service.execute_query(
            search_query,
            (query_list, query_list, min_score_bases, top_k),
            fetch="all",
            dict_cursor=False,
        )
        
        if not results:
            logging.info(f"Stage 1 (bases): No match found (min score: {min_score_bases})")
            return None
        
        # Process results with subvector matching
        best_match = None
        best_score = 0.0
        
        for row in results:
            record_id, context, category, subvectors_json, vector_sim = row
            
            # Compute subvector similarity
            subvec_sim = self._compute_subvector_similarity(query_vector, subvectors_json)
            
            # Final score: max of vector_sim and subvec_sim
            final_score = max(vector_sim, subvec_sim)
            
            if final_score >= self.threshold and final_score > best_score:
                best_score = final_score
                best_match = {
                    "id": str(record_id),
                    "source": "bases",
                    "context": context,
                    "category": category,
                    "vector_similarity": float(vector_sim),
                    "subvector_max_similarity": float(subvec_sim),
                    "final_score": float(final_score),
                    "priority_bonus": 0.0,
                }
        
        if best_match:
            logging.info(
                f"Stage 1 (bases): Found match with score {best_score:.3f}"
            )
        
        return best_match
    
    def search_all_tables(
        self,
        query: str,
        top_k_per_table: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """
        Search in all tables (Stage 2, new schema).
        
        Searches using context field (article + content) only.
        Priority scoring and per-table min scores applied.
        
        Args:
            query: Query text
            top_k_per_table: Number of candidates per table
        
        Returns:
            Best match dict or None if not found
        """
        # Embed query
        query_vector = self.embedding_service.embed_text(query)
        query_list = query_vector.tolist()
        
        all_candidates = []
        
        # Search each table
        for table_name in self.STAGE2_TABLES:
            search_query = f"""
                SELECT id, context, category, vectors,
                       cosine_similarity(vector, %s::vector) as vector_similarity
                FROM {table_name}
                ORDER BY vector_similarity DESC
                LIMIT %s;
            """
            
            results = self.connection_service.execute_query(
                search_query,
                (query_list, top_k_per_table),
                fetch="all",
                dict_cursor=False,
            )
            
            if not results:
                continue
            
            # Get minimum score for this table
            min_score_table = self.MIN_SCORES.get(table_name, self.threshold)
            
            # Process results
            for row in results:
                record_id, context, category, subvectors_json, vector_sim = row
                
                # Skip if no vector
                if vector_sim is None:
                    continue
                
                # Compute subvector similarity
                subvec_sim = self._compute_subvector_similarity(query_vector, subvectors_json)
                
                # Base score: max of vector_sim and subvec_sim
                base_score = max(vector_sim, subvec_sim)
                
                # Apply priority bonus
                priority_bonus = self.PRIORITY_BONUSES[table_name]
                final_score = base_score + priority_bonus
                
                # Only keep if above table-specific minimum score
                if final_score >= min_score_table:
                    all_candidates.append({
                        "id": str(record_id),
                        "source": table_name,
                        "context": context,
                        "category": category,
                        "vector_similarity": float(vector_sim),
                        "subvector_max_similarity": float(subvec_sim),
                        "base_score": float(base_score),
                        "priority_bonus": float(priority_bonus),
                        "final_score": float(final_score),
                        "min_score_required": float(min_score_table),
                    })
        
        if not all_candidates:
            logging.info(f"Stage 2: No match found across all tables (min scores by table: {self.MIN_SCORES})")
            return None
        
        # Sort by final_score and return best
        all_candidates.sort(key=lambda x: x["final_score"], reverse=True)
        best_match = all_candidates[0]
        
        logging.info(
            f"Stage 2: Found match from {best_match['source']} "
            f"with score {best_match['final_score']:.3f} "
            f"(base: {best_match['base_score']:.3f}, bonus: {best_match['priority_bonus']:.3f}, "
            f"min required: {best_match['min_score_required']:.3f})"
        )
        
        return best_match
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        return_not_found_message: bool = True,
    ) -> Dict[str, Any]:
        """
        Main search method - searches all tables with priority scoring.
        
        All tables are searched with per-table minimum score thresholds.
        Priority bonuses are applied to each match.
        Best match from all tables is returned.
        
        Args:
            query: Query text
            top_k: Number of candidates to consider per table
            return_not_found_message: If True, return message when not found
        
        Returns:
            Search result dict
        
        Example result:
            {
                "success": True,
                "result": {
                    "id": "...",
                    "source": "bases",
                    "data": {...},
                    "final_score": 0.75,
                    ...
                },
                "search_stats": {...}
            }
        """
        logging.info(f"Search query: {query[:100]}...")
        
        stats = {
            "searched_tables": self.STAGE2_TABLES,
            "total_candidates": 0,
        }
        
        # Search all tables with priority scoring
        stage_result = self.search_all_tables(query, top_k_per_table=top_k)
        
        if stage_result:
            return {
                "success": True,
                "result": stage_result,
                "search_stats": stats,
            }
        
        # Not found
        logging.info("No match found across all tables")
        
        if return_not_found_message:
            return {
                "success": False,
                "message": "Không tìm thấy câu trả lời",
                "search_stats": stats,
            }
        else:
            return {
                "success": False,
                "result": None,
                "search_stats": stats,
            }
    
    def search_in_table(
        self,
        table_name: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search in a specific table (new schema).
        
        Searches using context field only.
        Respects per-table minimum score thresholds.
        
        Args:
            table_name: Table to search
            query: Query text
            top_k: Number of results
        
        Returns:
            List of matches (only those meeting min_score for the table)
        """
        if table_name not in self.PRIORITY_BONUSES:
            raise ValueError(f"Invalid table: {table_name}")
        
        # Get minimum score for this table
        min_score_table = self.MIN_SCORES.get(table_name, self.threshold)
        
        # Embed query
        query_vector = self.embedding_service.embed_text(query)
        query_list = query_vector.tolist()
        
        search_query = f"""
            SELECT id, context, category, vectors,
                   cosine_similarity(vector, %s::vector) as vector_similarity
            FROM {table_name}
            ORDER BY vector_similarity DESC
            LIMIT %s;
        """
        
        results = self.connection_service.execute_query(
            search_query,
            (query_list, top_k),
            fetch="all",
            dict_cursor=False,
        )
        
        if not results:
            return []
        
        matches = []
        for row in results:
            record_id, context, category, subvectors_json, vector_sim = row
            
            # Compute subvector similarity
            subvec_sim = self._compute_subvector_similarity(query_vector, subvectors_json)
            
            base_score = max(vector_sim, subvec_sim)
            priority_bonus = self.PRIORITY_BONUSES[table_name]
            final_score = base_score + priority_bonus
            
            # Only include if meets minimum threshold for this table
            if final_score >= min_score_table:
                matches.append({
                    "id": str(record_id),
                    "source": table_name,
                    "context": context,
                    "category": category,
                    "vector_similarity": float(vector_sim),
                    "subvector_max_similarity": float(subvec_sim),
                    "base_score": float(base_score),
                    "priority_bonus": float(priority_bonus),
                    "final_score": float(final_score),
                    "min_score_required": float(min_score_table),
                })
        
        return matches


# Example usage
if __name__ == "__main__":
    from src.backends.core.services.enhancedEmbedding import create_embedding_service
    from src.backends.core.services.pgConnectionService import get_connection_service
    
    # Initialize services
    embed_service = create_embedding_service()
    conn_service = get_connection_service()
    search_service = PriorityVectorSearchService(embed_service, conn_service, threshold=0.7)
    
    # Example search
    query = "cách cài python"
    result = search_service.search(query)
    
    print("Search result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    conn_service.close()
