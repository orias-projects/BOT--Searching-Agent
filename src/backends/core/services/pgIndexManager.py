"""
PostgreSQL Vector Index Management Service.

Handles:
- Index creation and verification
- Index optimization (REINDEX)
- Index statistics and monitoring
- Index tuning recommendations
- HNSW and IVFFlat index strategies
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class PostgreSQLIndexManager:
    """Manage vector and other indexes for search performance."""

    # Vector index configurations
    VECTOR_INDEXES = {
        "ivfflat": {
            "description": "IVFFlat - Good for medium datasets (<1M)",
            "lists": 100,  # Can be tuned: √(rows/1000) for medium datasets
            "probes": None,  # Set at query time
        },
        "hnsw": {
            "description": "HNSW - Better for large datasets (>1M)",
            "m": 16,  # Number of bi-directional links created for every new element
            "ef_construction": 64,  # Size of dynamic candidate list
        },
    }

    def __init__(
        self,
        connection_service: PostgreSQLConnectionService,
    ):
        """
        Initialize index manager.

        Args:
            connection_service: PostgreSQL connection service
        """
        self.connection_service = connection_service
        logging.info("PostgreSQLIndexManager initialized")

    def create_ivfflat_index(
        self,
        table_name: str,
        column_name: str = "vectors",
        lists: int = 100,
    ) -> bool:
        """
        Create IVFFlat index for vector search.

        Args:
            table_name: Table name
            column_name: Column name (default: vectors)
            lists: Number of lists (tune based on dataset size)

        Returns:
            True if successful
        """
        index_name = f"idx_{table_name}_{column_name}_ivfflat"

        try:
            with self.connection_service.get_cursor() as cursor:
                # Drop existing index if exists
                cursor.execute(f"DROP INDEX IF EXISTS {index_name} CASCADE;")

                # Create new index
                cursor.execute(f"""
                    CREATE INDEX {index_name} ON {table_name}
                        USING ivfflat ({column_name} vector_cosine_ops)
                        WITH (lists = {lists});
                """)

            logging.info(f"✅ Created IVFFlat index: {index_name} (lists={lists})")
            return True

        except Exception as e:
            logging.error(f"Failed to create IVFFlat index: {e}")
            return False

    def create_hnsw_index(
        self,
        table_name: str,
        column_name: str = "vectors",
        m: int = 16,
        ef_construction: int = 64,
    ) -> bool:
        """
        Create HNSW index for vector search (better for large datasets).

        Args:
            table_name: Table name
            column_name: Column name (default: vectors)
            m: Number of bidirectional links created for new elements
            ef_construction: Size of dynamic candidate list

        Returns:
            True if successful
        """
        index_name = f"idx_{table_name}_{column_name}_hnsw"

        try:
            with self.connection_service.get_cursor() as cursor:
                # Drop existing index if exists
                cursor.execute(f"DROP INDEX IF EXISTS {index_name} CASCADE;")

                # Create new index
                cursor.execute(f"""
                    CREATE INDEX {index_name} ON {table_name}
                        USING hnsw ({column_name} vector_cosine_ops)
                        WITH (m = {m}, ef_construction = {ef_construction});
                """)

            logging.info(
                f"✅ Created HNSW index: {index_name} (m={m}, ef_construction={ef_construction})"
            )
            return True

        except Exception as e:
            logging.error(f"Failed to create HNSW index: {e}")
            return False

    def get_row_count(self, table_name: str) -> Optional[int]:
        """
        Get row count for a table.

        Args:
            table_name: Table name

        Returns:
            Row count or None if failed
        """
        try:
            result = self.connection_service.execute_query(
                f"SELECT COUNT(*) FROM {table_name};",
                fetch="one",
                dict_cursor=False,
            )
            return result[0] if result else None
        except Exception as e:
            logging.error(f"Failed to get row count for {table_name}: {e}")
            return None

    def recommend_index_type(self, table_name: str) -> str:
        """
        Recommend index type based on table size.

        Args:
            table_name: Table name

        Returns:
            Recommended index type: 'ivfflat' or 'hnsw'
        """
        row_count = self.get_row_count(table_name)
        if row_count is None:
            return "ivfflat"  # Default

        if row_count < 100_000:
            return "ivfflat"  # IVFFlat for small-medium datasets
        elif row_count < 1_000_000:
            return "ivfflat"  # Still IVFFlat for medium
        else:
            return "hnsw"  # HNSW for large datasets

    def recommend_lists_parameter(self, row_count: Optional[int] = None, table_name: Optional[str] = None) -> int:
        """
        Recommend lists parameter for IVFFlat based on dataset size.

        Formula: lists = √(rows / 1000), clamped to [10, 1000]

        Args:
            row_count: Row count (if None, table_name must be provided)
            table_name: Table name (if row_count is None)

        Returns:
            Recommended lists parameter
        """
        if row_count is None:
            if table_name is None:
                return self.VECTOR_INDEXES["ivfflat"]["lists"]
            row_count = self.get_row_count(table_name)
            if row_count is None:
                return self.VECTOR_INDEXES["ivfflat"]["lists"]

        # Formula: √(rows / 1000)
        import math

        recommended = max(10, min(1000, int(math.sqrt(row_count / 1000))))
        return recommended

    def get_index_info(self, index_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific index.

        Args:
            index_name: Index name

        Returns:
            Index information dict or None
        """
        try:
            result = self.connection_service.execute_query(
                """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE indexname = %s;
                """,
                (index_name,),
                fetch="one",
                dict_cursor=False,
            )

            if not result:
                return None

            schemaname, tablename, indexname, indexdef = result
            return {
                "schema": schemaname,
                "table": tablename,
                "name": indexname,
                "definition": indexdef,
            }

        except Exception as e:
            logging.error(f"Failed to get index info: {e}")
            return None

    def get_table_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get all indexes for a table.

        Args:
            table_name: Table name

        Returns:
            List of index information dicts
        """
        try:
            results = self.connection_service.execute_query(
                """
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = %s
                ORDER BY indexname;
                """,
                (table_name,),
                fetch="all",
                dict_cursor=False,
            )

            indexes = []
            for schemaname, tablename, indexname, indexdef in results:
                indexes.append({
                    "schema": schemaname,
                    "table": tablename,
                    "name": indexname,
                    "definition": indexdef,
                })

            return indexes

        except Exception as e:
            logging.error(f"Failed to get indexes for {table_name}: {e}")
            return []

    def get_index_stats(self, index_name: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for an index.

        Args:
            index_name: Index name

        Returns:
            Statistics dict or None
        """
        try:
            result = self.connection_service.execute_query(
                """
                SELECT 
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    pg_size_pretty(pg_relation_size(indexrelid)) as size
                FROM pg_stat_user_indexes
                WHERE indexrelname = %s;
                """,
                (index_name,),
                fetch="one",
                dict_cursor=False,
            )

            if not result:
                return None

            idx_scan, idx_tup_read, idx_tup_fetch, size = result
            return {
                "scans": idx_scan,
                "tuples_read": idx_tup_read,
                "tuples_fetched": idx_tup_fetch,
                "size": size,
            }

        except Exception as e:
            logging.error(f"Failed to get index stats: {e}")
            return None

    def reindex_index(self, index_name: str) -> bool:
        """
        Rebuild an index.

        Args:
            index_name: Index name

        Returns:
            True if successful
        """
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"REINDEX INDEX CONCURRENTLY {index_name};")

            logging.info(f"✅ Reindexed: {index_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to reindex {index_name}: {e}")
            return False

    def reindex_table(self, table_name: str) -> bool:
        """
        Rebuild all indexes for a table.

        Args:
            table_name: Table name

        Returns:
            True if successful
        """
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"REINDEX TABLE CONCURRENTLY {table_name};")

            logging.info(f"✅ Reindexed table: {table_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to reindex table {table_name}: {e}")
            return False

    def analyze_table(self, table_name: str) -> bool:
        """
        Analyze table statistics (helps query planner).

        Args:
            table_name: Table name

        Returns:
            True if successful
        """
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"ANALYZE {table_name};")

            logging.info(f"✅ Analyzed table: {table_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to analyze table {table_name}: {e}")
            return False

    def vacuum_table(self, table_name: str, analyze: bool = True) -> bool:
        """
        Vacuum table (reclaim space and optimize).

        Args:
            table_name: Table name
            analyze: If True, also analyze after vacuuming

        Returns:
            True if successful
        """
        try:
            analyze_str = "ANALYZE" if analyze else ""
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"VACUUM {analyze_str} {table_name};")

            action = "Vacuumed and analyzed" if analyze else "Vacuumed"
            logging.info(f"✅ {action}: {table_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to vacuum table {table_name}: {e}")
            return False

    def get_all_index_stats(self, table_names: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get statistics for all indexes in specified tables.

        Args:
            table_names: List of table names (if None, gets stats for common tables)

        Returns:
            Dict mapping table names to their index stats
        """
        if table_names is None:
            table_names = ["bases", "answers", "crawls", "respons", "chunks"]

        all_stats = {}
        for table_name in table_names:
            indexes = self.get_table_indexes(table_name)
            table_stats = []

            for index_info in indexes:
                index_name = index_info["name"]
                stats = self.get_index_stats(index_name)

                table_stats.append({
                    "name": index_name,
                    "info": index_info,
                    "stats": stats,
                })

            all_stats[table_name] = table_stats

        return all_stats

    def generate_optimization_report(self, table_names: List[str] = None) -> Dict[str, Any]:
        """
        Generate index optimization report with recommendations.

        Args:
            table_names: List of table names

        Returns:
            Optimization report
        """
        if table_names is None:
            table_names = ["bases", "answers", "crawls", "respons", "chunks"]

        report = {
            "timestamp": None,
            "tables": {},
            "recommendations": [],
        }

        for table_name in table_names:
            row_count = self.get_row_count(table_name)
            if row_count is None:
                continue

            recommended_type = self.recommend_index_type(table_name)
            recommended_lists = self.recommend_lists_parameter(row_count)

            table_report = {
                "row_count": row_count,
                "recommended_index_type": recommended_type,
                "recommended_lists": recommended_lists,
                "indexes": [],
            }

            # Get current indexes
            indexes = self.get_table_indexes(table_name)
            for index_info in indexes:
                index_name = index_info["name"]
                stats = self.get_index_stats(index_name)

                table_report["indexes"].append({
                    "name": index_name,
                    "definition": index_info["definition"],
                    "stats": stats,
                })

            table_report["recommendations"] = []
            if recommended_type == "hnsw" and row_count > 1_000_000:
                table_report["recommendations"].append(
                    f"Consider switching to HNSW index for {table_name} (>1M rows)"
                )
            if recommended_type == "ivfflat" and recommended_lists != 100:
                table_report["recommendations"].append(
                    f"Tune IVFFlat lists to {recommended_lists} (currently ~100)"
                )

            report["tables"][table_name] = table_report

        return report
