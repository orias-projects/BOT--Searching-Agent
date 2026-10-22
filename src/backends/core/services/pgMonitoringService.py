"""
PostgreSQL Monitoring and Health Check Service.

Provides:
- Real-time health checks
- Performance metrics
- Query statistics
- System alerts
- Health reports
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import sys
from pathlib import Path

# Add scripts to path for setup-time imports
if str(Path(__file__).parent.parent.parent.parent / "scripts") not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService
from src.scripts.dbTools.pgSchemaManager import PostgreSQLSchemaManager
from src.backends.core.services.pgIndexManager import PostgreSQLIndexManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class PostgreSQLMonitoringService:
    """Monitor PostgreSQL database health and performance."""

    def __init__(
        self,
        connection_service: PostgreSQLConnectionService,
        schema_manager: PostgreSQLSchemaManager = None,
        index_manager: PostgreSQLIndexManager = None,
    ):
        """
        Initialize monitoring service.

        Args:
            connection_service: PostgreSQL connection service
            schema_manager: Schema manager (optional)
            index_manager: Index manager (optional)
        """
        self.connection_service = connection_service
        self.schema_manager = schema_manager
        self.index_manager = index_manager
        
        # Cache for performance metrics
        self._cache = {}
        self._last_check = {}
        
        logging.info("PostgreSQLMonitoringService initialized")

    def check_connection(self) -> Tuple[bool, str]:
        """
        Check database connection.

        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            result = self.connection_service.execute_query("SELECT 1;", fetch="one")
            if result:
                return True, "✅ Connection OK"
            return False, "❌ Connection failed"
        except Exception as e:
            return False, f"❌ Connection error: {str(e)}"

    def check_pgvector_extension(self) -> Tuple[bool, str]:
        """
        Check if pgvector extension is installed.

        Returns:
            Tuple of (is_installed, message)
        """
        try:
            result = self.connection_service.execute_query(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector';",
                fetch="one",
            )
            if result:
                return True, "✅ pgvector installed"
            return False, "❌ pgvector NOT installed"
        except Exception as e:
            return False, f"❌ pgvector check error: {str(e)}"

    def get_database_size(self) -> Optional[Dict[str, str]]:
        """
        Get database size information.

        Returns:
            Dict with size information or None if failed
        """
        try:
            result = self.connection_service.execute_query(
                """
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as total_size,
                    (SELECT COUNT(*) FROM pg_tables WHERE schemaname='public') as table_count;
                """,
                fetch="one",
                dict_cursor=False,
            )
            
            if result:
                total_size, table_count = result
                return {
                    "total_size": total_size,
                    "table_count": table_count,
                }
            return None
        except Exception as e:
            logging.error(f"Failed to get database size: {e}")
            return None

    def get_connection_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get connection pool statistics.

        Returns:
            Dict with connection stats or None
        """
        try:
            result = self.connection_service.execute_query(
                """
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_transaction,
                    max(EXTRACT(EPOCH FROM (NOW() - query_start))) as longest_query_seconds
                FROM pg_stat_activity
                WHERE datname = current_database();
                """,
                fetch="one",
                dict_cursor=False,
            )
            
            if result:
                total, active, idle, idle_tx, longest = result
                return {
                    "total_connections": total,
                    "active": active,
                    "idle": idle,
                    "idle_in_transaction": idle_tx,
                    "longest_query_seconds": float(longest) if longest else 0,
                }
            return None
        except Exception as e:
            logging.error(f"Failed to get connection stats: {e}")
            return None

    def get_table_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all vector tables.

        Returns:
            Dict mapping table names to their stats
        """
        table_names = ["bases", "answers", "crawls", "respons", "chunks"]
        stats = {}

        for table_name in table_names:
            try:
                result = self.connection_service.execute_query(
                    f"""
                    SELECT 
                        COUNT(*) as row_count,
                        pg_size_pretty(pg_total_relation_size('{table_name}'::regclass)) as total_size,
                        pg_size_pretty(pg_relation_size('{table_name}'::regclass)) as table_size,
                        pg_size_pretty(pg_total_relation_size('{table_name}'::regclass) - 
                            pg_relation_size('{table_name}'::regclass)) as index_size,
                        (SELECT last_vacuum FROM pg_stat_user_tables WHERE relname = '{table_name}') as last_vacuum,
                        (SELECT last_analyze FROM pg_stat_user_tables WHERE relname = '{table_name}') as last_analyze
                    FROM {table_name};
                    """,
                    fetch="one",
                    dict_cursor=False,
                )

                if result:
                    row_count, total_size, table_size, index_size, last_vacuum, last_analyze = result
                    stats[table_name] = {
                        "row_count": row_count,
                        "total_size": total_size,
                        "table_size": table_size,
                        "index_size": index_size,
                        "last_vacuum": last_vacuum.isoformat() if last_vacuum else None,
                        "last_analyze": last_analyze.isoformat() if last_analyze else None,
                    }
            except Exception as e:
                logging.error(f"Failed to get stats for {table_name}: {e}")
                stats[table_name] = None

        return stats

    def get_slow_queries(self, min_duration_ms: float = 100) -> List[Dict[str, Any]]:
        """
        Get recent slow queries.

        Args:
            min_duration_ms: Minimum duration in milliseconds

        Returns:
            List of slow query information
        """
        try:
            results = self.connection_service.execute_query(
                f"""
                SELECT 
                    query,
                    calls,
                    mean_exec_time,
                    max_exec_time,
                    stddev_exec_time
                FROM pg_stat_statements
                WHERE mean_exec_time > {min_duration_ms}
                ORDER BY mean_exec_time DESC
                LIMIT 10;
                """,
                fetch="all",
                dict_cursor=False,
            )

            if not results:
                return []

            queries = []
            for query, calls, mean_time, max_time, stddev_time in results:
                queries.append({
                    "query": query[:100] + "..." if len(query) > 100 else query,
                    "calls": calls,
                    "mean_time_ms": round(mean_time, 2),
                    "max_time_ms": round(max_time, 2),
                    "stddev_time_ms": round(stddev_time, 2) if stddev_time else 0,
                })

            return queries

        except Exception as e:
            logging.error(f"Failed to get slow queries: {e}")
            return []

    def get_index_usage_stats(self, min_scans: int = 0) -> Dict[str, Dict[str, Any]]:
        """
        Get index usage statistics.

        Args:
            min_scans: Minimum number of scans to include

        Returns:
            Dict mapping table names to their index stats
        """
        table_names = ["bases", "answers", "crawls", "respons", "chunks"]
        stats = {}

        for table_name in table_names:
            try:
                results = self.connection_service.execute_query(
                    f"""
                    SELECT 
                        indexrelname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch,
                        pg_size_pretty(pg_relation_size(indexrelid)) as size
                    FROM pg_stat_user_indexes
                    WHERE relname = '{table_name}'
                    ORDER BY idx_scan DESC;
                    """,
                    fetch="all",
                    dict_cursor=False,
                )

                table_stats = []
                if results:
                    for idx_name, scans, tup_read, tup_fetch, size in results:
                        if scans >= min_scans:
                            table_stats.append({
                                "index": idx_name,
                                "scans": scans,
                                "tuples_read": tup_read,
                                "tuples_fetched": tup_fetch,
                                "size": size,
                            })

                stats[table_name] = table_stats

            except Exception as e:
                logging.error(f"Failed to get index stats for {table_name}: {e}")
                stats[table_name] = []

        return stats

    def check_table_health(self, table_name: str) -> Dict[str, Any]:
        """
        Check health of a specific table.

        Args:
            table_name: Table to check

        Returns:
            Health check results
        """
        health = {
            "table": table_name,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "issues": [],
            "status": "✅ Healthy",
        }

        # Check if table exists
        if self.schema_manager:
            exists = self.schema_manager.table_exists(table_name)
            health["checks"]["exists"] = exists
            if not exists:
                health["issues"].append(f"Table {table_name} does not exist")
                health["status"] = "❌ Table missing"
                return health

            # Verify schema
            is_valid, schema_issues = self.schema_manager.verify_table_schema(table_name)
            health["checks"]["schema_valid"] = is_valid
            if not is_valid:
                health["issues"].extend(schema_issues)

            # Check indexes
            indexes = self.schema_manager.check_indexes(table_name)
            health["checks"]["indexes_exist"] = all(indexes.values())
            for index_name, exists in indexes.items():
                if not exists:
                    health["issues"].append(f"Missing index: {index_name}")

        # Get stats
        stats = self.get_table_stats()
        if table_name in stats and stats[table_name]:
            health["stats"] = stats[table_name]

        # Get index usage
        index_stats = self.get_index_usage_stats()
        if table_name in index_stats:
            health["index_usage"] = index_stats[table_name]

        # Determine overall status
        if health["issues"]:
            health["status"] = f"⚠️ {len(health['issues'])} issue(s) found"

        return health

    def check_all_tables_health(self) -> Dict[str, Any]:
        """
        Check health of all vector tables.

        Returns:
            Health report for all tables
        """
        table_names = ["bases", "answers", "crawls", "respons", "chunks"]
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "✅ All Healthy",
            "tables": {},
            "summary": {
                "total_tables": len(table_names),
                "healthy": 0,
                "issues": 0,
            },
        }

        issues_found = False

        for table_name in table_names:
            table_health = self.check_table_health(table_name)
            report["tables"][table_name] = table_health

            if "✅" in table_health["status"]:
                report["summary"]["healthy"] += 1
            else:
                report["summary"]["issues"] += 1
                issues_found = True

        if issues_found:
            report["overall_status"] = "⚠️ Issues found"

        return report

    def generate_full_health_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health report.

        Returns:
            Full health report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "⏳ Checking...",
            "basic_checks": {},
            "database": {},
            "connections": {},
            "tables": {},
            "performance": {},
            "issues": [],
            "recommendations": [],
        }

        # Basic checks
        conn_ok, conn_msg = self.check_connection()
        report["basic_checks"]["connection"] = {"ok": conn_ok, "message": conn_msg}

        pgvec_ok, pgvec_msg = self.check_pgvector_extension()
        report["basic_checks"]["pgvector"] = {"ok": pgvec_ok, "message": pgvec_msg}

        if not conn_ok:
            report["status"] = "❌ Database unreachable"
            return report

        if not pgvec_ok:
            report["issues"].append("pgvector extension not installed")
            report["recommendations"].append("Run: pip install pgvector")

        # Database info
        db_size = self.get_database_size()
        if db_size:
            report["database"] = db_size

        # Connection stats
        conn_stats = self.get_connection_stats()
        if conn_stats:
            report["connections"] = conn_stats

        # Table health
        tables_health = self.check_all_tables_health()
        report["tables"] = tables_health

        # Performance metrics
        report["performance"]["slow_queries"] = self.get_slow_queries()
        report["performance"]["index_usage"] = self.get_index_usage_stats()

        # Determine overall status
        if report["issues"]:
            report["status"] = f"⚠️ {len(report['issues'])} issue(s)"
        elif tables_health["summary"]["issues"] > 0:
            report["status"] = "⚠️ Table issues detected"
        else:
            report["status"] = "✅ All systems healthy"

        return report

    def get_resource_usage(self) -> Optional[Dict[str, Any]]:
        """
        Get system resource usage by PostgreSQL.

        Returns:
            Resource usage dict or None
        """
        try:
            result = self.connection_service.execute_query(
                """
                SELECT 
                    pg_size_pretty(SUM(heap_blks_read) * 8192) as total_heap_read,
                    pg_size_pretty(SUM(heap_blks_hit * 8192)) as total_heap_hit,
                    ROUND(100.0 * SUM(heap_blks_hit) / (SUM(heap_blks_hit) + SUM(heap_blks_read)), 2) as cache_hit_ratio
                FROM pg_statio_user_tables;
                """,
                fetch="one",
                dict_cursor=False,
            )

            if result:
                heap_read, heap_hit, cache_ratio = result
                return {
                    "heap_read": heap_read,
                    "heap_hit": heap_hit,
                    "cache_hit_ratio": f"{cache_ratio}%" if cache_ratio else "N/A",
                }
            return None
        except Exception as e:
            logging.error(f"Failed to get resource usage: {e}")
            return None

    def format_health_report(self, report: Dict[str, Any]) -> str:
        """
        Format health report for console display.

        Args:
            report: Health report dict

        Returns:
            Formatted string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("DATABASE HEALTH REPORT")
        lines.append("=" * 70)
        lines.append(f"\nStatus: {report['status']}")
        lines.append(f"Timestamp: {report['timestamp']}")

        # Basic checks
        lines.append("\n📋 BASIC CHECKS")
        lines.append("-" * 70)
        for check_name, check_result in report.get("basic_checks", {}).items():
            status = "✅" if check_result["ok"] else "❌"
            lines.append(f"{status} {check_name}: {check_result['message']}")

        # Database info
        if report.get("database"):
            lines.append("\n💾 DATABASE INFO")
            lines.append("-" * 70)
            for key, value in report["database"].items():
                lines.append(f"  {key}: {value}")

        # Connections
        if report.get("connections"):
            lines.append("\n🔌 CONNECTIONS")
            lines.append("-" * 70)
            conn = report["connections"]
            lines.append(f"  Total: {conn['total_connections']}")
            lines.append(f"  Active: {conn['active']}")
            lines.append(f"  Idle: {conn['idle']}")
            lines.append(f"  Idle in transaction: {conn.get('idle_in_transaction', 0)}")

        # Tables
        if report.get("tables"):
            lines.append("\n📊 TABLES")
            lines.append("-" * 70)
            tables_report = report["tables"]
            lines.append(f"  Summary: {tables_report['summary']['healthy']}/{tables_report['summary']['total_tables']} healthy")
            
            for table_name, table_info in tables_report.get("tables", {}).items():
                lines.append(f"\n  {table_name}: {table_info['status']}")
                if table_info.get("stats"):
                    stats = table_info["stats"]
                    lines.append(f"    Records: {stats['row_count']:,}")
                    lines.append(f"    Size: {stats['total_size']}")
                if table_info.get("issues"):
                    for issue in table_info["issues"]:
                        lines.append(f"    ⚠️ {issue}")

        # Issues and recommendations
        if report.get("issues"):
            lines.append("\n⚠️ ISSUES")
            lines.append("-" * 70)
            for issue in report["issues"]:
                lines.append(f"  - {issue}")

        if report.get("recommendations"):
            lines.append("\n💡 RECOMMENDATIONS")
            lines.append("-" * 70)
            for rec in report["recommendations"]:
                lines.append(f"  - {rec}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)
