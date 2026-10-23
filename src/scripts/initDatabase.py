"""
Database schema initialization and verification utility.

Usage:
    python scripts/init_database.py --init          # Create all tables
    python scripts/init_database.py --verify        # Verify schema
    python scripts/init_database.py --health        # Generate health report
    python scripts/init_database.py --reset         # Truncate all tables
    python scripts/init_database.py --drop          # Drop all tables
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sys
from pathlib import Path

# Ensure scripts is in path
sys.path.insert(0, str(Path(__file__).parent))

from src.backends.core.services.pgConnectionService import PostgreSQLConnectionService
from src.scripts.dbTools.pgSchemaManager import PostgreSQLSchemaManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database schema."""
    logger.info("=" * 70)
    logger.info("DATABASE INITIALIZATION")
    logger.info("=" * 70)

    try:
        # Create connection service
        logger.info("\n1. Creating connection to database...")
        conn_service = PostgreSQLConnectionService()

        # Create schema manager
        schema_manager = PostgreSQLSchemaManager(conn_service)

        # Install pgvector extension
        logger.info("\n2. Installing pgvector extension...")
        if not schema_manager.install_pgvector_extension():
            logger.error("Failed to install pgvector extension")
            return False

        # Create tables
        logger.info("\n3. Creating tables...")
        results = schema_manager.create_all_tables()
        for table_name, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"{status} {table_name}")

        # Verify schema
        logger.info("\n4. Verifying schema...")
        all_valid, verification_results = schema_manager.verify_all_tables()

        for table_name, (is_valid, issues) in verification_results.items():
            status = "✅" if is_valid else "❌"
            logger.info(f"{status} {table_name}")
            if issues:
                for issue in issues:
                    logger.warning(f"   - {issue}")

        if all_valid:
            logger.info("\n✅ Database initialization completed successfully!")
            return True
        else:
            logger.error("\n❌ Some verification issues found")
            return False

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def verify_schema():
    """Verify existing schema."""
    logger.info("=" * 70)
    logger.info("SCHEMA VERIFICATION")
    logger.info("=" * 70)

    try:
        conn_service = PostgreSQLConnectionService()
        schema_manager = PostgreSQLSchemaManager(conn_service)

        logger.info("\nChecking pgvector extension...")
        has_pgvector = schema_manager.check_pgvector_extension()
        status = "✅" if has_pgvector else "❌"
        logger.info(f"{status} pgvector extension: {has_pgvector}")

        logger.info("\nVerifying tables...")
        all_valid, verification_results = schema_manager.verify_all_tables()

        for table_name, (is_valid, issues) in verification_results.items():
            status = "✅" if is_valid else "❌"
            exists = schema_manager.table_exists(table_name)
            exists_status = "exists" if exists else "MISSING"
            logger.info(f"{status} {table_name} ({exists_status})")

            if issues:
                for issue in issues:
                    logger.warning(f"   - {issue}")

            # Check indexes
            indexes = schema_manager.check_indexes(table_name)
            for index_name, exists in indexes.items():
                idx_status = "✅" if exists else "❌"
                logger.info(f"   {idx_status} {index_name}")

        logger.info("\n" + "=" * 70)
        if all_valid:
            logger.info("✅ All schemas are valid!")
        else:
            logger.warning("⚠️ Some schema issues found")

        return all_valid

    except Exception as e:
        logger.error(f"Failed to verify schema: {e}")
        return False


def health_report():
    """Generate and display health report."""
    logger.info("=" * 70)
    logger.info("DATABASE HEALTH REPORT")
    logger.info("=" * 70)

    try:
        conn_service = PostgreSQLConnectionService()
        schema_manager = PostgreSQLSchemaManager(conn_service)

        report = schema_manager.generate_health_report()

        # Display report
        logger.info(f"\nPgVector Installed: {report['pgvector_installed']}")
        logger.info(f"Tables Valid: {report['tables_valid']}")

        logger.info("\nTable Details:")
        for table_name, details in report["table_details"].items():
            logger.info(f"\n  {table_name}:")
            logger.info(f"    Exists: {details['exists']}")
            logger.info(f"    Schema Valid: {details['schema_valid']}")

            if details["issues"]:
                logger.warning("    Issues:")
                for issue in details["issues"]:
                    logger.warning(f"      - {issue}")

            if details["indexes"]:
                logger.info("    Indexes:")
                for index_name, exists in details["indexes"].items():
                    idx_status = "✅" if exists else "❌"
                    logger.info(f"      {idx_status} {index_name}")

        logger.info("\nTable Statistics:")
        for table_name, stats in report["stats"].items():
            logger.info(f"\n  {table_name}:")
            logger.info(f"    Records: {stats['row_count']:,}")
            logger.info(f"    Size: {stats['total_size']}")
            logger.info(f"    Table: {stats['table_size']}")
            logger.info(f"    Indexes: {stats['index_size']}")

        if report["issues"]:
            logger.warning("\nOverall Issues:")
            for issue in report["issues"]:
                logger.warning(f"  - {issue}")

        logger.info("\n" + "=" * 70)
        if not report["issues"]:
            logger.info("✅ Database is healthy!")
        else:
            logger.warning(f"⚠️ Found {len(report['issues'])} issue(s)")

        return len(report["issues"]) == 0

    except Exception as e:
        logger.error(f"Failed to generate health report: {e}")
        return False


def reset_data():
    """Truncate all tables (delete data, keep schema)."""
    logger.info("=" * 70)
    logger.info("TRUNCATING DATA")
    logger.warning("⚠️ This will DELETE ALL DATA from all tables!")
    logger.info("=" * 70)

    response = input("\nAre you sure? Type 'yes' to confirm: ")
    if response.lower() != "yes":
        logger.info("Cancelled.")
        return False

    try:
        conn_service = PostgreSQLConnectionService()
        schema_manager = PostgreSQLSchemaManager(conn_service)

        logger.info("\nTruncating tables...")
        results = schema_manager.reset_all_tables()

        for table_name, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"{status} {table_name}")

        logger.info("\n✅ Data truncation completed!")
        return True

    except Exception as e:
        logger.error(f"Failed to truncate tables: {e}")
        return False


def drop_schema():
    """Drop all tables (destructive operation)."""
    logger.info("=" * 70)
    logger.info("DROP ALL TABLES")
    logger.critical("⚠️⚠️⚠️ This will PERMANENTLY DELETE all tables and data!")
    logger.info("=" * 70)

    response = input("\nType 'DROP ALL TABLES' to confirm: ")
    if response != "DROP ALL TABLES":
        logger.info("Cancelled.")
        return False

    try:
        conn_service = PostgreSQLConnectionService()
        schema_manager = PostgreSQLSchemaManager(conn_service)

        logger.info("\nDropping tables...")
        results = schema_manager.drop_all_tables()

        for table_name, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"{status} {table_name}")

        logger.info("\n✅ Tables dropped!")
        return True

    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database schema management utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/init_database.py --init          # Create all tables
  python scripts/init_database.py --verify        # Verify schema  
  python scripts/init_database.py --health        # Generate health report
  python scripts/init_database.py --reset         # Truncate all tables (remove data)
  python scripts/init_database.py --drop          # Drop all tables (destructive!)
        """,
    )

    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize database (create tables and indexes)",
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing schema",
    )

    parser.add_argument(
        "--health",
        action="store_true",
        help="Generate health report",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate all tables (delete data, keep schema)",
    )

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables (destructive!)",
    )

    args = parser.parse_args()

    # Default to health check if no arguments
    if not any([args.init, args.verify, args.health, args.reset, args.drop]):
        args.health = True

    # Execute command
    success = True
    if args.init:
        success = init_database()
    elif args.verify:
        success = verify_schema()
    elif args.health:
        success = health_report()
    elif args.reset:
        success = reset_data()
    elif args.drop:
        success = drop_schema()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
