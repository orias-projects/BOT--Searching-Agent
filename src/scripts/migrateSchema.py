"""
Migration script: Apply vector search schema to PostgreSQL database.

Usage:
    python -m scripts.migrate_schema up      # Apply migration
    python -m scripts.migrate_schema down    # Rollback migration
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv


load_dotenv()
def get_connection_string() -> str:
    """Get PostgreSQL connection string from environment."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url.strip()
    
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "rag_vectors")
    user = os.environ.get("DB_USER", "postgres")
    password = os.environ.get("DB_PASSWORD", "")
    
    if not password:
        raise ValueError("Database password not set. Set DB_PASSWORD or DATABASE_URL.")
    
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def read_schema_file() -> str:
    """Read the SQL schema file."""
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "databases", ".sql", "schema_vector_search.sql"
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return f.read()


def apply_migration():
    """Apply the vector search schema migration."""
    print("🚀 Starting migration: Vector Search Schema")
    print("=" * 60)
    
    try:
        conn_string = get_connection_string()
        print(f"✓ Connection string loaded")
        
        # Connect to database
        conn = psycopg2.connect(conn_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print(f"✓ Connected to database")
        
        # Check if pgvector extension exists
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector';")
        if not cursor.fetchone():
            print("⚠️  pgvector extension not found. Installing...")
            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print("✓ pgvector extension installed")
            except Exception as e:
                print(f"❌ Failed to install pgvector: {e}")
                print("   Please install pgvector manually:")
                print("   https://github.com/pgvector/pgvector#installation")
                sys.exit(1)
        else:
            print("✓ pgvector extension already installed")
        
        # Read and execute schema
        schema_sql = read_schema_file()
        print("✓ Schema file loaded")
        
        # Execute schema
        print("\n📝 Applying schema...")
        cursor.execute(schema_sql)
        print("✓ Schema applied successfully")
        
        # Verify tables created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('bases', 'answers', 'crawls', 'respons', 'chunks')
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\n✓ Tables created: {', '.join([t[0] for t in tables])}")
        
        # Verify indexes
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public'
              AND tablename IN ('bases', 'answers', 'crawls', 'respons', 'chunks')
              AND indexname LIKE 'idx_%'
            ORDER BY indexname;
        """)
        indexes = cursor.fetchall()
        print(f"✓ Indexes created: {len(indexes)} indexes")
        
        # Verify functions
        cursor.execute("""
            SELECT proname 
            FROM pg_proc 
            WHERE proname IN ('cosine_similarity', 'search_bases', 'search_all_with_priority', 'update_updated_at_column')
            ORDER BY proname;
        """)
        functions = cursor.fetchall()
        print(f"✓ Functions created: {', '.join([f[0] for f in functions])}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def rollback_migration():
    """Rollback the migration (drop all tables and objects)."""
    print("🔄 Rolling back migration: Vector Search Schema")
    print("=" * 60)
    print("⚠️  WARNING: This will drop all tables and data!")
    
    # Confirm in interactive mode
    if sys.stdin.isatty():
        confirm = input("Type 'yes' to confirm rollback: ")
        if confirm.lower() != 'yes':
            print("❌ Rollback cancelled")
            return False
    
    try:
        conn_string = get_connection_string()
        conn = psycopg2.connect(conn_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print(f"✓ Connected to database")
        
        # Drop tables
        print("\n📝 Dropping tables...")
        tables = ['bases', 'answers', 'crawls', 'respons', 'chunks']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"  ✓ Dropped table: {table}")
        
        # Drop views
        print("\n📝 Dropping views...")
        cursor.execute("DROP VIEW IF EXISTS v_table_stats CASCADE;")
        print(f"  ✓ Dropped view: v_table_stats")
        
        # Drop functions
        print("\n📝 Dropping functions...")
        functions = [
            'cosine_similarity(vector, vector)',
            'search_bases(vector, float, int)',
            'search_all_with_priority(vector, float, int)',
            'update_updated_at_column()'
        ]
        for func in functions:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func} CASCADE;")
            print(f"  ✓ Dropped function: {func.split('(')[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Rollback completed successfully!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Rollback failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m scripts.migrate_schema up    # Apply migration")
        print("  python -m scripts.migrate_schema down  # Rollback migration")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "up":
        success = apply_migration()
    elif command == "down":
        success = rollback_migration()
    else:
        print(f"Unknown command: {command}")
        print("Use 'up' or 'down'")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
