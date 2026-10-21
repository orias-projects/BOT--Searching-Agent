"""
Upload JSON data to PostgreSQL with full embeddings.

Script để chuyển dữ liệu từ database/jsons/ lên PostgreSQL pgvector
với vector embedding đầy đủ (full vectors + subvectors).
"""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent to path để import từ scripts/
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.backends.core.services.enhancedEmbedding import create_embedding_service
from src.backends.core.services.pgConnectionService import get_connection_service
from src.backends.core.services.pgVectorInsert import VectorInsertService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class JSONDataUploader:
    """Upload JSON data to PostgreSQL with embeddings."""

    def __init__(self):
        """Initialize services."""
        self.embedding_service = create_embedding_service()
        self.conn_service = get_connection_service()
        self.insert_service = VectorInsertService(
            self.embedding_service, self.conn_service
        )
        logger.info("JSONDataUploader initialized")

    def load_json_file(self, filepath: str) -> Any:
        """Load JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def transform_answers(self, records: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """
        Transform answers.json records to (json_data, metadata).
        
        Expected structure (after refactoring):
        {
            "Article": "...",
            "Level 0": "...",
            "Content": ["..."]
        }
        """
        transformed = []
        for i, record in enumerate(records, 1):
            json_data = record.copy()
            metadata = {
                "source": "answers.json",
                "record_number": i,
            }
            transformed.append((json_data, metadata))
        return transformed

    def transform_chunks(self, records: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """
        Transform chunks.json records to (json_data, metadata).
        
        Expected structure (after refactoring):
        {
            "Level 1": "...",
            "Level 2": "...",
            "Article": "...",
            "Content": ["..."]
        }
        """
        transformed = []
        for record in records:
            json_data = record.copy()
            metadata = {
                "source": "chunks.json",
            }
            transformed.append((json_data, metadata))
        return transformed

    def transform_knowledge(self, data: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """
        Transform knowledge.json to list of (json_data, metadata).
        
        Knowledge.json is already a list of items with:
        {
            "Article": "...",
            "Content": ["..."]
        }
        """
        transformed = []
        for i, record in enumerate(data, 1):
            json_data = record.copy()
            metadata = {
                "source": "knowledge.json",
                "record_number": i,
            }
            transformed.append((json_data, metadata))
        return transformed

    def upload_file(
        self,
        filepath: str,
        table_name: str,
        transform_func,
        batch_size: int = 10,
    ) -> int:
        """Upload file to database in batches."""
        logger.info(f"Loading {filepath}...")
        data = self.load_json_file(filepath)

        logger.info(f"Transforming data for {table_name}...")
        
        # Handle different file structures
        if "knowledge.json" in filepath:
            # knowledge.json is a list of items
            transformed = transform_func(data)
        elif table_name == "bases":
            # bases uses knowledge.json which is a list
            transformed = transform_func(data)
        else:
            # Other files are already lists
            transformed = transform_func(data)

        logger.info(f"Inserting {len(transformed)} records into {table_name}...")
        inserted_ids = []

        # Process in batches
        for i in range(0, len(transformed), batch_size):
            batch = transformed[i : i + batch_size]
            try:
                batch_ids = self.insert_service.insert_batch(
                    table_name=table_name,
                    json_data_list=[j for j, m in batch],
                    metadata_list=[m for j, m in batch],
                )
                inserted_ids.extend(batch_ids)
                logger.info(
                    f"  Batch {i // batch_size + 1}: Inserted {len(batch_ids)} records"
                )
            except Exception as e:
                logger.error(f"  Batch {i // batch_size + 1} failed: {e}")
                raise

        return len(inserted_ids)

    def run(self, data_dir: str = "databases/jsons"):
        """Run the upload process."""
        logger.info("=" * 60)
        logger.info("Starting JSON to PostgreSQL upload with embeddings")
        logger.info("=" * 60)

        data_dir = Path(data_dir)
        total_inserted = 0

        # Upload answers.json → answers table
        try:
            count = self.upload_file(
                str(data_dir / "answers.json"),
                "answers",
                self.transform_answers,
            )
            total_inserted += count
            logger.info(f"✓ Uploaded answers.json: {count} records\n")
        except Exception as e:
            logger.error(f"✗ Failed to upload answers.json: {e}")

        # Upload chunks.json → chunks table
        try:
            count = self.upload_file(
                str(data_dir / "chunks.json"),
                "chunks",
                self.transform_chunks,
            )
            total_inserted += count
            logger.info(f"✓ Uploaded chunks.json: {count} records\n")
        except Exception as e:
            logger.error(f"✗ Failed to upload chunks.json: {e}")

        # Upload knowledge.json → bases table
        try:
            count = self.upload_file(
                str(data_dir / "knowledge.json"),
                "bases",
                self.transform_knowledge,
            )
            total_inserted += count
            logger.info(f"✓ Uploaded knowledge.json: {count} records\n")
        except Exception as e:
            logger.error(f"✗ Failed to upload knowledge.json: {e}")

        logger.info("=" * 60)
        logger.info(f"Upload complete! Total records inserted: {total_inserted}")
        logger.info("=" * 60)

        return total_inserted


def main():
    """Main entry point."""
    try:
        uploader = JSONDataUploader()
        total = uploader.run()

        if total > 0:
            logger.info("\n✅ All data successfully uploaded to PostgreSQL")
            return 0
        else:
            logger.warning("\n⚠️ No data was uploaded")
            return 1
    except Exception as e:
        logger.error(f"\n❌ Upload failed: {e}", exC_INF=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
