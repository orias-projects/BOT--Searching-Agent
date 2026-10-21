"""
Enhanced embedding service for vector search with subvectors support.

Provides:
1. Full JSON embedding (normalized text)
2. Per-field embeddings (subvectors)
3. Batch processing
4. Multiple embedding models support
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class EnhancedEmbeddingService:
    """
    Enhanced embedding service that generates:
    - Full vectors: embedding of entire JSON (normalized)
    - Subvectors: embedding of each field separately
    """
    
    def __init__(
        self,
        model_name: str = "VoVanPhuc/sup-SimCSE-VietNamese-phobert-base",
        device: str = None,
        batch_size: int = 32,
        max_seq_length: int = 256,
        normalize_embeddings: bool = True,
    ):
        """
        Initialize embedding service.
        
        Args:
            model_name: Hugging Face model name
            device: Device to use ('cuda' or 'cpu'), auto-detect if None
            batch_size: Batch size for encoding
            max_seq_length: Maximum sequence length
            normalize_embeddings: Whether to L2 normalize embeddings
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.normalize_embeddings = normalize_embeddings
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Load model
        logging.info(f"Loading embedding model: {model_name}")
        logging.info(f"Using device: {self.device}")
        
        self.model = SentenceTransformer(model_name, device=self.device)
        self.model.max_seq_length = max_seq_length
        
        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logging.info(f"Embedding dimension: {self.embedding_dim}")
    
    def normalize_json_to_text(self, data: Any) -> str:
        """
        Normalize JSON to text by replacing JSON structure with newlines.
        
        Example:
            {"question": "Hello", "answer": "Hi"} 
            → "question\nHello\nanswer\nHi"
        
        Args:
            data: JSON data (dict, list, or primitive)
        
        Returns:
            Normalized text string
        """
        if isinstance(data, dict):
            parts = []
            for key, value in data.items():
                parts.append(str(key))
                parts.append(self.normalize_json_to_text(value))
            return "\n".join(parts)
        
        elif isinstance(data, list):
            parts = [self.normalize_json_to_text(item) for item in data]
            return "\n".join(parts)
        
        elif data is None:
            return ""
        
        else:
            # Primitive types (str, int, float, bool)
            return str(data)
    
    def extract_text_fields(self, data: Dict[str, Any], max_depth: int = 3, current_depth: int = 0) -> Dict[str, str]:
        """
        Extract text fields from JSON for per-field embedding.
        
        Recursively traverses JSON and extracts string fields with their paths.
        
        Args:
            data: JSON object
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
        
        Returns:
            Dict mapping field paths to text values
            Example: {"question": "...", "answer": "...", "metadata.title": "..."}
        """
        fields = {}
        
        if not isinstance(data, dict) or current_depth >= max_depth:
            return fields
        
        for key, value in data.items():
            if isinstance(value, str) and value.strip():
                # String field
                fields[key] = value
            
            elif isinstance(value, (int, float, bool)):
                # Convert primitive to string
                fields[key] = str(value)
            
            elif isinstance(value, dict):
                # Nested dict - recurse
                nested = self.extract_text_fields(value, max_depth, current_depth + 1)
                for nested_key, nested_value in nested.items():
                    fields[f"{key}.{nested_key}"] = nested_value
            
            elif isinstance(value, list) and value:
                # List - join if all strings, otherwise skip
                if all(isinstance(item, str) for item in value):
                    fields[key] = " ".join(value)
        
        return fields
    
    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            text: Single text or list of texts
        
        Returns:
            Numpy array of shape (embedding_dim,) or (n, embedding_dim)
        """
        if isinstance(text, str):
            text = [text]
        
        embeddings = self.model.encode(
            text,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        
        return embeddings[0] if len(text) == 1 else embeddings
    
    def generate_full_embedding(self, json_data: Any) -> np.ndarray:
        """
        Generate embedding for entire JSON (normalized to text).
        
        Args:
            json_data: JSON data
        
        Returns:
            Embedding vector as numpy array
        """
        normalized_text = self.normalize_json_to_text(json_data)
        return self.embed_text(normalized_text)
    
    def generate_subvectors(self, json_data: Dict[str, Any], max_depth: int = 3) -> Dict[str, List[float]]:
        """
        Generate per-field embeddings (subvectors).
        
        Args:
            json_data: JSON object
            max_depth: Maximum depth for field extraction
        
        Returns:
            Dict mapping field names to embedding vectors (as lists)
            Example: {"question": [0.1, 0.2, ...], "answer": [0.3, 0.4, ...]}
        """
        # Extract text fields
        fields = self.extract_text_fields(json_data, max_depth=max_depth)
        
        if not fields:
            return {}
        
        # Generate embeddings for all fields in batch
        field_names = list(fields.keys())
        field_texts = list(fields.values())
        
        embeddings = self.embed_text(field_texts)
        
        # Ensure embeddings is always 2D (N, dim)
        # embed_text returns 1D array for single text, 2D for multiple
        if embeddings.ndim == 1:
            embeddings = np.array([embeddings])
        
        # Convert to dict of lists (for JSON serialization)
        subvectors = {}
        for field_name, embedding in zip(field_names, embeddings):
            subvectors[field_name] = embedding.tolist()
        
        return subvectors
    
    def prepare_record(self, json_data: Any, max_depth: int = 3) -> Tuple[np.ndarray, Dict[str, List[float]]]:
        """
        Prepare complete record: full vector + subvectors.
        
        Args:
            json_data: JSON data
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            Tuple of (full_vector, subvectors_dict)
        """
        # Generate full embedding
        full_vector = self.generate_full_embedding(json_data)
        
        # Generate subvectors (only for dict)
        if isinstance(json_data, dict):
            subvectors = self.generate_subvectors(json_data, max_depth=max_depth)
        else:
            subvectors = {}
        
        return full_vector, subvectors
    
    def prepare_batch(
        self,
        json_data_list: List[Any],
        max_depth: int = 3
    ) -> List[Tuple[np.ndarray, Dict[str, List[float]]]]:
        """
        Prepare multiple records in batch (more efficient).
        
        Args:
            json_data_list: List of JSON data
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            List of (full_vector, subvectors_dict) tuples
        """
        results = []
        
        # Process each record
        for json_data in json_data_list:
            full_vector, subvectors = self.prepare_record(json_data, max_depth)
            results.append((full_vector, subvectors))
        
        return results
    
    def extract_context_data(self, json_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Separate context and category from record.
        
        Context: {"Article": "...", "Content": [...]}
        Category: {"Level 0": "...", "Level 1": "...", "Level 2": "..."}
        
        Args:
            json_data: Full record JSON
        
        Returns:
            Tuple of (context_dict, category_dict)
        """
        context = {}
        category = {}
        
        for key, value in json_data.items():
            if key in ["Article", "Content"]:
                context[key] = value
            elif key in ["Level 0", "Level 1", "Level 2"]:
                category[key] = value
            else:
                # Unknown keys go to category
                category[key] = value
        
        return context, category
    
    def prepare_record_context(
        self, 
        json_data: Dict[str, Any], 
        max_depth: int = 3
    ) -> Tuple[np.ndarray, Dict[str, List[float]], Dict[str, Any]]:
        """
        Prepare record with context-only embedding (new schema).
        
        Only embeds context (article + content) fields.
        Category fields (Level 0, Level 1, Level 2) are extracted separately.
        
        Args:
            json_data: Full record JSON
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            Tuple of (full_vector, subvectors_dict, category_dict)
        """
        # Separate context and category
        context, category = self.extract_context_data(json_data)
        
        # Generate full embedding from context only
        full_vector = self.generate_full_embedding(context)
        
        # Generate subvectors from context only
        subvectors = self.generate_subvectors(context, max_depth=max_depth)
        
        return full_vector, subvectors, category
    
    def prepare_batch_context(
        self,
        json_data_list: List[Dict[str, Any]],
        max_depth: int = 3
    ) -> List[Tuple[np.ndarray, Dict[str, List[float]], Dict[str, Any]]]:
        """
        Prepare batch of records with context-only embedding (new schema).
        
        Args:
            json_data_list: List of full record JSONs
            max_depth: Maximum depth for subvector extraction
        
        Returns:
            List of (full_vector, subvectors_dict, category_dict) tuples
        """
        results = []
        
        for json_data in json_data_list:
            full_vector, subvectors, category = self.prepare_record_context(json_data, max_depth)
            results.append((full_vector, subvectors, category))
        
        return results


# Convenience function for backward compatibility
def create_embedding_service(
    model_name: str = "VoVanPhuc/sup-SimCSE-VietNamese-phobert-base",
    device: str = None,
    **kwargs
) -> EnhancedEmbeddingService:
    """
    Factory function to create embedding service.
    
    Args:
        model_name: Model name
        device: Device ('cuda' or 'cpu')
        **kwargs: Additional arguments for EnhancedEmbeddingService
    
    Returns:
        EnhancedEmbeddingService instance
    """
    return EnhancedEmbeddingService(model_name=model_name, device=device, **kwargs)


# Example usage
if __name__ == "__main__":
    # Initialize service
    service = EnhancedEmbeddingService()
    
    # Example data
    data = {
        "question": "Làm thế nào để cài đặt Python?",
        "answer": "Tải Python từ python.org và chạy installer.",
        "topic": "Installation"
    }
    
    # Generate full embedding
    full_vec = service.generate_full_embedding(data)
    print(f"Full vector shape: {full_vec.shape}")
    print(f"Full vector (first 5): {full_vec[:5]}")
    
    # Generate subvectors
    subvecs = service.generate_subvectors(data)
    print(f"\nSubvectors keys: {list(subvecs.keys())}")
    for key in subvecs:
        print(f"  {key}: shape ({len(subvecs[key])},) first 5: {subvecs[key][:5]}")
    
    # Prepare complete record
    vec, subs = service.prepare_record(data)
    print(f"\nPrepared record:")
    print(f"  Vector: {vec.shape}")
    print(f"  Subvectors: {len(subs)} fields")
