"""
Test script: Search directly from PostgreSQL using PriorityVectorSearchService.
This shows how to query the uploaded data correctly.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backends.core.services.enhanced_embedding import create_embedding_service
from src.backends.core.services.pgConnectionService import get_connection_service
from src.backends.core.services.pgVectorSearch import PriorityVectorSearchService


def test_search():
    """Test searching uploaded data from PostgreSQL."""
    
    query = "Sinh viên được xét và công nhận tốt nghiệp khi có đủ các điều kiện nào?"
    
    print(f"\n🔍 Testing PostgreSQL Search")
    print(f"Query: {query}\n")
    
    try:
        # Initialize services
        embedding_service = create_embedding_service()
        connection_service = get_connection_service()
        search_service = PriorityVectorSearchService(
            embedding_service,
            connection_service,
            threshold=0.5  # Lower threshold for better results
        )
        
        # Search
        print("Searching...")
        result = search_service.search(query, top_k=10)
        
        print(f"\n📊 Search Stats:")
        stats = result.get('search_stats', {})
        print(f"  Searched bases: {stats.get('searched_bases')}")
        print(f"  Bases found: {stats.get('bases_found')}")
        print(f"  Stage 2 searched: {stats.get('stage2_searched')}")
        
        if result.get('success'):
            match = result.get('result', {})
            print(f"\n✅ Found match!")
            print(f"  Source table: {match.get('source')}")
            print(f"  Final score: {match.get('final_score'):.4f}")
            print(f"  Vector similarity: {match.get('vector_similarity'):.4f}")
            print(f"  Subvector max similarity: {match.get('subvector_max_similarity'):.4f}")
            
            # Try to extract text
            data = match.get('data', {})
            if isinstance(data, dict):
                text = data.get('answer') or data.get('content') or data.get('question') or str(data)[:200]
            else:
                text = str(data)[:200]
            print(f"  Text: {text}...")
            return True
        else:
            print(f"\n❌ No match found: {result.get('message')}")
            return False
        
        return len(results) > 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_search()
    sys.exit(0 if success else 1)
