"""
PostgreSQL connection pool service for vector search.

Provides connection management, health checks, and utilities.
"""
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json, RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class PostgreSQLConnectionService:
    """PostgreSQL connection pool manager."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        min_connections: int = 1,
        max_connections: int = 10,
    ):
        """
        Initialize connection pool.
        
        Args:
            connection_string: PostgreSQL connection string
            min_connections: Minimum number of connections in pool
            max_connections: Maximum number of connections in pool
        """
        self.connection_string = connection_string or self._get_connection_string_from_env()
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool = None
        
        logging.info("Initializing PostgreSQL connection pool")
        self._initialize_pool()
    
    def _get_connection_string_from_env(self) -> str:
        """Get connection string from environment variables."""
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            return db_url.strip()
        
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "rag_vectors")
        user = os.environ.get("DB_USER", "postgres")
        password = os.environ.get("DB_PASSWORD", "")
        
        if not password:
            raise ValueError(
                "Database password not set. Set DB_PASSWORD or DATABASE_URL environment variable."
            )
        
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    
    def _initialize_pool(self):
        """Initialize connection pool."""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_connections,
                self.max_connections,
                self.connection_string
            )
            logging.info(
                f"Connection pool created: {self.min_connections}-{self.max_connections} connections"
            )
        except Exception as e:
            logging.error(f"Failed to create connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self, dict_cursor: bool = False):
        """
        Get a connection from the pool (context manager).
        
        Args:
            dict_cursor: If True, use RealDictCursor for dict results
        
        Yields:
            Connection object
        
        Example:
            with service.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bases")
        """
        conn = self._pool.getconn()
        try:
            if dict_cursor:
                conn.cursor_factory = RealDictCursor
            yield conn
        finally:
            self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = False, commit: bool = True):
        """
        Get a cursor (context manager with auto-commit).
        
        Args:
            dict_cursor: If True, use RealDictCursor
            commit: If True, commit after execution
        
        Yields:
            Cursor object
        
        Example:
            with service.get_cursor() as cursor:
                cursor.execute("INSERT INTO bases (...) VALUES (%s)", (data,))
        """
        with self.get_connection(dict_cursor=dict_cursor) as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logging.error(f"Transaction failed, rolled back: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: str = "all",
        dict_cursor: bool = False,
    ) -> Optional[List]:
        """
        Execute a query and fetch results.
        
        Args:
            query: SQL query
            params: Query parameters
            fetch: 'all', 'one', or 'none'
            dict_cursor: Use dict cursor
        
        Returns:
            Query results or None
        """
        with self.get_cursor(dict_cursor=dict_cursor, commit=(fetch == "none")) as cursor:
            cursor.execute(query, params)
            
            if fetch == "all":
                return cursor.fetchall()
            elif fetch == "one":
                return cursor.fetchone()
            else:
                return None
    
    def execute_many(
        self,
        query: str,
        params_list: List[Tuple],
    ) -> int:
        """
        Execute query with many parameter sets (batch insert).
        
        Args:
            query: SQL query
            params_list: List of parameter tuples
        
        Returns:
            Number of affected rows
        """
        with self.get_cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check database health.
        
        Returns:
            Health status dict
        """
        try:
            with self.get_cursor() as cursor:
                # Check connection
                cursor.execute("SELECT 1;")
                cursor.fetchone()
                
                # Check pgvector extension
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
                has_pgvector = cursor.fetchone() is not None
                
                # Check tables exist
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND table_name IN ('bases', 'answers', 'crawls', 'respons', 'chunks')
                    ORDER BY table_name;
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                # Get table counts
                counts = {}
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    counts[table] = cursor.fetchone()[0]
                
                return {
                    "status": "healthy",
                    "connection": "ok",
                    "pgvector_installed": has_pgvector,
                    "tables": tables,
                    "record_counts": counts,
                }
        
        except Exception as e:
            logging.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    def close(self):
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            logging.info("Connection pool closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance (optional, for convenience)
_service_instance: Optional[PostgreSQLConnectionService] = None


def get_connection_service(
    connection_string: Optional[str] = None,
    force_new: bool = False,
) -> PostgreSQLConnectionService:
    """
    Get singleton connection service instance.
    
    Args:
        connection_string: Connection string (if creating new)
        force_new: Force create new instance
    
    Returns:
        PostgreSQLConnectionService instance
    """
    global _service_instance
    
    if force_new or _service_instance is None:
        _service_instance = PostgreSQLConnectionService(connection_string=connection_string)
    
    return _service_instance


# Example usage
if __name__ == "__main__":
    # Create service
    service = PostgreSQLConnectionService()
    
    # Health check
    health = service.check_health()
    print("Health check:")
    print(health)
    
    # Close
    service.close()
