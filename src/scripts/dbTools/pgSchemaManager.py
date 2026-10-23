"""
PostgreSQL Schema Management Service for Vector Search System.

Handles:
- pgvector extension installation
- Table creation and verification
- Index management
- Schema drift detection
- Migration utilities
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class PostgreSQLSchemaManager:
    """Manage PostgreSQL schema for vector search system."""

    # Table definitions
    TABLES = {
        "bases": {
            "description": "Knowledge cơ bản (system) - Priority cao nhất, threshold 0.7",
            "priority": 0.0,
            "priority_bonus": 0.0,
        },
        "answers": {
            "description": "Q&A do team dev tạo",
            "priority": 2,
            "priority_bonus": 0.03,
        },
        "crawls": {
            "description": "Q&A từ diễn đàn",
            "priority": 3,
            "priority_bonus": 0.02,
        },
        "respons": {
            "description": "Q&A từ users/testers",
            "priority": 4,
            "priority_bonus": 0.01,
        },
        "chunks": {
            "description": "Chunks từ documents",
            "priority": 5,
            "priority_bonus": 0.00,
        },
    }

    def __init__(
        self,
        connection_service: PostgreSQLConnectionService,
        vector_dimension: int = 768,
    ):
        """
        Initialize schema manager.

        Args:
            connection_service: PostgreSQL connection service
            vector_dimension: Vector dimension (default 768)
        """
        self.connection_service = connection_service
        self.vector_dimension = vector_dimension
        logging.info(
            f"PostgreSQLSchemaManager initialized (dimension: {vector_dimension})"
        )

    def check_pgvector_extension(self) -> bool:
        """
        Check if pgvector extension is installed.

        Returns:
            True if installed, False otherwise
        """
        try:
            result = self.connection_service.execute_query(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector';",
                fetch="one",
            )
            installed = result is not None
            if installed:
                logging.info("✅ pgvector extension is installed")
            else:
                logging.warning("⚠️ pgvector extension NOT installed")
            return installed
        except Exception as e:
            logging.error(f"Failed to check pgvector extension: {e}")
            return False

    def install_pgvector_extension(self) -> bool:
        """
        Install pgvector extension.

        Returns:
            True if installed successfully, False if failed or already installed
        """
        try:
            # Check if already installed
            if self.check_pgvector_extension():
                logging.info("pgvector extension already installed")
                return True

            # Install
            with self.connection_service.get_cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            
            logging.info("✅ Installed pgvector and uuid-ossp extensions")
            return True
        except Exception as e:
            logging.error(f"Failed to install pgvector extension: {e}")
            return False

    def create_table(self, table_name: str) -> bool:
        """
        Create a single table.

        Args:
            table_name: Name of table ('bases', 'answers', 'crawls', 'respons', 'chunks')

        Returns:
            True if created, False if failed
        """
        if table_name not in self.TABLES:
            raise ValueError(f"Unknown table: {table_name}")

        table_description = self.TABLES[table_name]["description"]

        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        vectors VECTOR({self.vector_dimension}) NOT NULL,
                        jsons JSONB NOT NULL,
                        subvectors JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        metadata JSONB DEFAULT '{{}}'::jsonb,
                        
                        CONSTRAINT {table_name}_jsons_not_empty 
                            CHECK (jsonb_typeof(jsons) = 'object'),
                        CONSTRAINT {table_name}_subvectors_not_empty 
                            CHECK (jsonb_typeof(subvectors) = 'object')
                    );
                """)

                # Create indexes
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_vectors_cosine ON {table_name}
                        USING ivfflat (vectors vector_cosine_ops)
                        WITH (lists = 100);
                """)

                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_jsons ON {table_name}
                        USING GIN (jsons);
                """)

                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_metadata ON {table_name}
                        USING GIN (metadata);
                """)

                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_created_at ON {table_name}
                        (created_at DESC);
                """)

                # Add table comment
                cursor.execute(f"""
                    COMMENT ON TABLE {table_name} IS %s;
                """, (table_description,))

            logging.info(f"✅ Created table: {table_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to create table {table_name}: {e}")
            return False

    def create_all_tables(self) -> Dict[str, bool]:
        """
        Create all tables.

        Returns:
            Dict mapping table names to success status
        """
        results = {}
        for table_name in self.TABLES.keys():
            results[table_name] = self.create_table(table_name)
        return results

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists.

        Args:
            table_name: Table name

        Returns:
            True if exists, False otherwise
        """
        try:
            result = self.connection_service.execute_query(
                """
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s;
                """,
                (table_name,),
                fetch="one",
            )
            exists = result is not None
            status = "✅" if exists else "❌"
            logging.debug(f"{status} Table {table_name}: {exists}")
            return exists
        except Exception as e:
            logging.error(f"Failed to check if table {table_name} exists: {e}")
            return False

    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get table schema information.

        Args:
            table_name: Table name

        Returns:
            Dict with column information, or None if table doesn't exist
        """
        try:
            results = self.connection_service.execute_query(
                """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
                """,
                (table_name,),
                fetch="all",
                dict_cursor=False,
            )

            if not results:
                return None

            columns = {}
            for col_name, data_type, is_nullable, col_default in results:
                columns[col_name] = {
                    "type": data_type,
                    "nullable": is_nullable == "YES",
                    "default": col_default,
                }

            return columns

        except Exception as e:
            logging.error(f"Failed to get schema for {table_name}: {e}")
            return None

    def verify_table_schema(self, table_name: str) -> Tuple[bool, List[str]]:
        """
        Verify table has required columns.

        Args:
            table_name: Table name

        Returns:
            Tuple of (is_valid, list of issues)
        """
        if not self.table_exists(table_name):
            return False, [f"Table {table_name} does not exist"]

        schema = self.get_table_schema(table_name)
        if not schema:
            return False, ["Could not retrieve schema"]

        required_columns = {
            "id": "uuid",
            "vectors": f"vector({self.vector_dimension})",
            "jsons": "jsonb",
            "subvectors": "jsonb",
            "created_at": "timestamp",
            "updated_at": "timestamp",
            "metadata": "jsonb",
        }

        issues = []
        for col_name, expected_type in required_columns.items():
            if col_name not in schema:
                issues.append(f"Missing column: {col_name}")
            else:
                actual_type = schema[col_name]["type"]
                # For vectors, check if it contains the dimension
                if "vector" in expected_type.lower():
                    if "vector" not in actual_type.lower():
                        issues.append(
                            f"Column {col_name} has wrong type: "
                            f"expected {expected_type}, got {actual_type}"
                        )
                # For timestamp, accept both timestamp and timestamptz
                elif expected_type.lower() == "timestamp":
                    if "timestamp" not in actual_type.lower():
                        issues.append(
                            f"Column {col_name} has wrong type: "
                            f"expected {expected_type}, got {actual_type}"
                        )
                elif actual_type.lower() != expected_type.lower():
                    issues.append(
                        f"Column {col_name} has wrong type: "
                        f"expected {expected_type}, got {actual_type}"
                    )

        is_valid = len(issues) == 0
        return is_valid, issues

    def get_table_stats(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Get table statistics (row count, size, etc.).

        Args:
            table_name: Table name

        Returns:
            Dict with statistics, or None if table doesn't exist
        """
        try:
            result = self.connection_service.execute_query(
                f"""
                SELECT 
                    COUNT(*) as row_count,
                    pg_size_pretty(pg_total_relation_size('{table_name}'::regclass)) as total_size,
                    pg_size_pretty(pg_relation_size('{table_name}'::regclass)) as table_size,
                    pg_size_pretty(pg_total_relation_size('{table_name}'::regclass) - 
                        pg_relation_size('{table_name}'::regclass)) as index_size,
                    pg_size_pretty(pg_total_relation_size('{table_name}'::regclass) - 
                        pg_relation_size('{table_name}'::regclass)) as index_size
                FROM {table_name};
                """,
                fetch="one",
                dict_cursor=False,
            )

            if not result:
                return None

            row_count, total_size, table_size, index_size, _ = result
            return {
                "row_count": row_count,
                "total_size": total_size,
                "table_size": table_size,
                "index_size": index_size,
            }

        except Exception as e:
            logging.error(f"Failed to get stats for {table_name}: {e}")
            return None

    def get_all_table_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all tables.

        Returns:
            Dict mapping table names to their statistics
        """
        stats = {}
        for table_name in self.TABLES.keys():
            table_stats = self.get_table_stats(table_name)
            if table_stats:
                stats[table_name] = table_stats
        return stats

    def verify_all_tables(self) -> Tuple[bool, Dict[str, Tuple[bool, List[str]]]]:
        """
        Verify all tables.

        Returns:
            Tuple of (all_valid, dict mapping table names to (is_valid, issues))
        """
        results = {}
        for table_name in self.TABLES.keys():
            is_valid, issues = self.verify_table_schema(table_name)
            results[table_name] = (is_valid, issues)

        all_valid = all(is_valid for is_valid, _ in results.values())
        return all_valid, results

    def check_indexes(self, table_name: str) -> Dict[str, bool]:
        """
        Check if required indexes exist.

        Args:
            table_name: Table name

        Returns:
            Dict mapping index names to existence status
        """
        required_indexes = [
            f"idx_{table_name}_vectors_cosine",
            f"idx_{table_name}_jsons",
            f"idx_{table_name}_metadata",
            f"idx_{table_name}_created_at",
        ]

        try:
            results = self.connection_service.execute_query(
                """
                SELECT indexname FROM pg_indexes
                WHERE tablename = %s;
                """,
                (table_name,),
                fetch="all",
                dict_cursor=False,
            )

            existing_indexes = {row[0] for row in results} if results else set()

            index_status = {}
            for index_name in required_indexes:
                index_status[index_name] = index_name in existing_indexes

            return index_status

        except Exception as e:
            logging.error(f"Failed to check indexes for {table_name}: {e}")
            return {}

    def generate_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report.

        Returns:
            Health report dict
        """
        report = {
            "timestamp": None,
            "pgvector_installed": False,
            "tables_valid": False,
            "table_details": {},
            "stats": {},
            "issues": [],
        }

        # Check pgvector
        report["pgvector_installed"] = self.check_pgvector_extension()
        if not report["pgvector_installed"]:
            report["issues"].append("pgvector extension not installed")

        # Verify tables
        all_valid, results = self.verify_all_tables()
        report["tables_valid"] = all_valid

        for table_name, (is_valid, issues) in results.items():
            report["table_details"][table_name] = {
                "exists": self.table_exists(table_name),
                "schema_valid": is_valid,
                "issues": issues,
                "indexes": self.check_indexes(table_name),
            }

            if not is_valid:
                report["issues"].extend([f"{table_name}: {issue}" for issue in issues])

        # Get stats
        report["stats"] = self.get_all_table_stats()

        return report

    def drop_table(self, table_name: str, cascade: bool = False) -> bool:
        """
        Drop a table (use with caution!).

        Args:
            table_name: Table name
            cascade: If True, drop dependent objects

        Returns:
            True if successful
        """
        try:
            cascade_str = "CASCADE" if cascade else "RESTRICT"
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} {cascade_str};")

            logging.warning(f"⚠️ Dropped table: {table_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to drop table {table_name}: {e}")
            return False

    def drop_all_tables(self) -> Dict[str, bool]:
        """
        Drop all vector tables (use with caution!).

        Returns:
            Dict mapping table names to success status
        """
        results = {}
        for table_name in self.TABLES.keys():
            results[table_name] = self.drop_table(table_name, cascade=True)
        return results

    def truncate_table(self, table_name: str) -> bool:
        """
        Truncate table (delete all rows, reset sequences).

        Args:
            table_name: Table name

        Returns:
            True if successful
        """
        try:
            with self.connection_service.get_cursor() as cursor:
                cursor.execute(f"TRUNCATE {table_name} RESTART IDENTITY;")

            logging.info(f"Truncated table: {table_name}")
            return True

        except Exception as e:
            logging.error(f"Failed to truncate table {table_name}: {e}")
            return False

    def reset_all_tables(self) -> Dict[str, bool]:
        """
        Truncate all tables (delete all rows).

        Returns:
            Dict mapping table names to success status
        """
        results = {}
        for table_name in self.TABLES.keys():
            results[table_name] = self.truncate_table(table_name)
        return results
