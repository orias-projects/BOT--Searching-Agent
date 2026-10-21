"""
Migration tool: Migrate data from FAISS/JSON to PostgreSQL.

Reads existing FAISS indexes and JSON files, converts to new format,
and inserts into PostgreSQL tables.
"""
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class FAISSToPostgreSQLMigration:
    """Migrate FAISS data to PostgreSQL."""
    
    def __init__(self):
        """Initialize migration tool."""
        self.project_root = Path(__file__).parent.parent
        self.databases_json_path = self.project_root / "databases" / "jsons"
        self.databases_vector_path = self.project_root / "databases" / "vectors"
        
        # Services (lazy load)
        self._embedding_service = None
        self._connection_service = None
        self._insert_service = None
    
    def _init_services(self):
        """Initialize services."""
        if self._embedding_service is None:
            from src.backends.core.services.enhancedEmbedding import create_embedding_service
            from src.backends.core.services.pgConnectionService import get_connection_service
            from src.backends.core.services.pgVectorInsert import VectorInsertService
            
            logging.info("Initializing services...")
            self._embedding_service = create_embedding_service()
            self._connection_service = get_connection_service()
            self._insert_service = VectorInsertService(
                self._embedding_service,
                self._connection_service
            )
            logging.info("✅ Services initialized")
    
    def find_faiss_indexes(self) -> List[Dict[str, Path]]:
        """
        Find all FAISS index files in databases/ directory.
        
        Returns:
            List of dicts with 'name', 'faiss_path', 'mapping_path', etc.
        """
        indexes = []
        
        # Search in databases/jsons/
        if self.databases_json_path.exists():
            for item in self.databases_json_path.rglob("*.faiss"):
                base_name = item.stem.replace("_Embedding_Index", "")
                parent_dir = item.parent
                
                index_info = {
                    "name": base_name,
                    "source_dir": parent_dir,
                    "faiss_path": item,
                    "mapping_path": parent_dir / f"{base_name}_Embedding_Mapping.json",
                    "mapdata_path": parent_dir / f"{base_name}_Embedding_MapData.json",
                    "mapchunk_path": parent_dir / f"{base_name}_Embedding_MapChunk.json",
                }
                indexes.append(index_info)
        
        # Search in databases/vectors/
        if self.databases_vector_path.exists():
            for item in self.databases_vector_path.rglob("*.faiss"):
                base_name = item.stem.replace("_Embedding_Index", "")
                parent_dir = item.parent
                
                index_info = {
                    "name": base_name,
                    "source_dir": parent_dir,
                    "faiss_path": item,
                    "mapping_path": parent_dir / f"{base_name}_Embedding_Mapping.json",
                    "mapdata_path": parent_dir / f"{base_name}_Embedding_MapData.json",
                    "mapchunk_path": parent_dir / f"{base_name}_Embedding_MapChunk.json",
                }
                indexes.append(index_info)
        
        logging.info(f"Found {len(indexes)} FAISS indexes")
        return indexes
    
    def load_faiss_index(self, faiss_path: Path) -> Optional[faiss.Index]:
        """Load FAISS index from file."""
        try:
            index = faiss.read_index(str(faiss_path))
            logging.info(f"Loaded FAISS index: {faiss_path.name} ({index.ntotal} vectors)")
            return index
        except Exception as e:
            logging.error(f"Failed to load FAISS index {faiss_path}: {e}")
            return None
    
    def load_json_file(self, json_path: Path) -> Optional[Any]:
        """Load JSON file."""
        if not json_path.exists():
            logging.warning(f"JSON file not found: {json_path}")
            return None
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logging.info(f"Loaded JSON: {json_path.name}")
            return data
        except Exception as e:
            logging.error(f"Failed to load JSON {json_path}: {e}")
            return None
    
    def determine_target_table(self, index_name: str, source_dir: Path) -> str:
        """
        Determine target table based on index name and location.
        
        Heuristics:
        - If name contains "Category" or in "vectors" folder → bases
        - If name contains "HNMU" or similar doc names → chunks
        - Default: chunks
        """
        name_lower = index_name.lower()
        
        if "categor" in name_lower or "base" in name_lower:
            return "bases"
        elif "answer" in name_lower or "qa" in name_lower:
            return "answers"
        elif "crawl" in name_lower or "forum" in name_lower:
            return "crawls"
        elif "response" in name_lower or "user" in name_lower:
            return "respons"
        else:
            # Default to chunks (for document chunks)
            return "chunks"
    
    def migrate_index(
        self,
        index_info: Dict[str, Path],
        target_table: Optional[str] = None,
        batch_size: int = 100,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Migrate a single FAISS index to PostgreSQL.
        
        Args:
            index_info: Index information dict
            target_table: Target table (auto-detect if None)
            batch_size: Batch size for inserts
            dry_run: If True, don't actually insert
        
        Returns:
            Migration result dict
        """
        logging.info(f"\n{'='*60}")
        logging.info(f"Migrating index: {index_info['name']}")
        logging.info(f"{'='*60}")
        
        # Load FAISS index
        faiss_index = self.load_faiss_index(index_info["faiss_path"])
        if faiss_index is None:
            return {"success": False, "error": "Failed to load FAISS index"}
        
        # Load mapping/data files
        mapping = self.load_json_file(index_info["mapping_path"])
        mapdata = self.load_json_file(index_info["mapdata_path"])
        mapchunk = self.load_json_file(index_info["mapchunk_path"])
        
        if not mapdata:
            logging.warning("No MapData found, skipping this index")
            return {"success": False, "error": "No MapData"}
        
        # Determine target table
        if target_table is None:
            target_table = self.determine_target_table(
                index_info["name"],
                index_info["source_dir"]
            )
        
        logging.info(f"Target table: {target_table}")
        
        # Extract vectors from FAISS
        num_vectors = faiss_index.ntotal
        vectors_array = np.zeros((num_vectors, faiss_index.d), dtype=np.float32)
        for i in range(num_vectors):
            vectors_array[i] = faiss_index.reconstruct(i)
        
        logging.info(f"Extracted {num_vectors} vectors from FAISS")
        
        # Prepare records for insertion
        records = []
        for i, (vector, data) in enumerate(zip(vectors_array, mapdata)):
            # Create JSON record
            if isinstance(data, dict):
                json_data = data
            elif isinstance(data, str):
                json_data = {"text": data}
            else:
                json_data = {"content": str(data)}
            
            # Add metadata
            metadata = {
                "source": "faiss_migration",
                "original_index": index_info["name"],
                "original_id": i,
            }
            
            records.append({
                "vector": vector,
                "json_data": json_data,
                "metadata": metadata,
            })
        
        logging.info(f"Prepared {len(records)} records")
        
        # Insert in batches
        if dry_run:
            logging.info("DRY RUN: Would insert records but skipping...")
            return {
                "success": True,
                "dry_run": True,
                "table": target_table,
                "count": len(records),
            }
        
        # Initialize services
        self._init_services()
        
        # Insert
        inserted_ids = []
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            
            json_data_list = [r["json_data"] for r in batch]
            metadata_list = [r["metadata"] for r in batch]
            
            try:
                batch_ids = self._insert_service.insert_batch(
                    table_name=target_table,
                    json_data_list=json_data_list,
                    metadata_list=metadata_list,
                )
                inserted_ids.extend(batch_ids)
                logging.info(f"Inserted batch {i//batch_size + 1} ({len(batch)} records)")
            
            except Exception as e:
                logging.error(f"Failed to insert batch {i//batch_size + 1}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "partial_count": len(inserted_ids),
                }
        
        logging.info(f"✅ Migration complete: {len(inserted_ids)} records inserted into {target_table}")
        
        return {
            "success": True,
            "table": target_table,
            "count": len(inserted_ids),
            "ids": inserted_ids,
        }
    
    def migrate_all(
        self,
        batch_size: int = 100,
        dry_run: bool = False,
        skip_errors: bool = True,
    ) -> Dict[str, Any]:
        """
        Migrate all FAISS indexes.
        
        Args:
            batch_size: Batch size for inserts
            dry_run: If True, don't actually insert
            skip_errors: If True, continue on errors
        
        Returns:
            Overall migration result
        """
        indexes = self.find_faiss_indexes()
        
        if not indexes:
            logging.warning("No FAISS indexes found")
            return {"success": False, "error": "No indexes found"}
        
        results = []
        
        for index_info in indexes:
            try:
                result = self.migrate_index(
                    index_info,
                    batch_size=batch_size,
                    dry_run=dry_run,
                )
                results.append(result)
                
                if not result["success"] and not skip_errors:
                    logging.error("Migration failed, stopping")
                    break
            
            except Exception as e:
                logging.error(f"Exception during migration: {e}")
                if not skip_errors:
                    break
        
        # Summary
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        total_count = sum(r.get("count", 0) for r in successful)
        
        logging.info(f"\n{'='*60}")
        logging.info("MIGRATION SUMMARY")
        logging.info(f"{'='*60}")
        logging.info(f"Total indexes: {len(indexes)}")
        logging.info(f"Successful: {len(successful)}")
        logging.info(f"Failed: {len(failed)}")
        logging.info(f"Total records migrated: {total_count}")
        logging.info(f"{'='*60}")
        
        return {
            "success": len(failed) == 0,
            "total": len(indexes),
            "successful": len(successful),
            "failed": len(failed),
            "total_records": total_count,
            "results": results,
        }


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate FAISS data to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't insert)")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument("--skip-errors", action="store_true", help="Continue on errors")
    
    args = parser.parse_args()
    
    migration = FAISSToPostgreSQLMigration()
    result = migration.migrate_all(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        skip_errors=args.skip_errors,
    )
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
