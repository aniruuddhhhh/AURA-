
from datetime import datetime
from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os

VECTOR_DB_DIR = "./aura_vector_db_hf"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CURRENT_USER_ID = "1503960366"

_embeddings_model = None
_vector_db = None


def get_embeddings():
    """Get or create embeddings model (singleton)."""
    global _embeddings_model
    if _embeddings_model is None:
        print("[INDEXER] Loading embedding model...")
        class DirectEmbeddings:
            def __init__(self, model_name):
                self.model = SentenceTransformer(model_name)
            
            def embed_documents(self, texts):
                return self.model.encode(texts).tolist()

            def embed_query(self, text):
                return self.model.encode([text])[0].tolist()
        _embeddings_model = DirectEmbeddings(EMBED_MODEL)
        print("[INDEXER] ✅ Embedding model loaded")
    return _embeddings_model

def get_vector_db():
    """Get or create vector database connection (singleton)."""
    global _vector_db
    if _vector_db is None:
        print("[INDEXER] Connecting to vector database...")
        embeddings = get_embeddings()
        
        if not os.path.exists(VECTOR_DB_DIR):
            os.makedirs(VECTOR_DB_DIR)
            print(f"[INDEXER] Created directory: {VECTOR_DB_DIR}")
        
        _vector_db = Chroma(
            persist_directory=VECTOR_DB_DIR,
            embedding_function=embeddings
        )
        print("[INDEXER] ✅ Vector DB connected")
    return _vector_db

def index_journal_entry(entry_text: str, timestamp: str = None, user_id: str = None) -> bool:
    """
    Add a single journal entry to the vector database in real-time.
    
    Args:
        entry_text: The journal entry content
        timestamp: Entry timestamp (defaults to now)
        user_id: User ID (defaults to CURRENT_USER_ID)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not entry_text or not entry_text.strip():
            print("[INDEXER] ⚠️  Empty entry, skipping indexing")
            return False

        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if user_id is None:
            user_id = CURRENT_USER_ID

        doc = Document(
            page_content=entry_text.strip(),
            metadata={
                "user_id": str(user_id),
                "timestamp": timestamp,
                "source": "realtime_entry"
            }
        )
        
        print(f"[INDEXER] 📝 Indexing entry: {entry_text[:50]}...") 
        vector_db = get_vector_db()
        vector_db.add_documents([doc])
        print(f"[INDEXER] ✅ Entry indexed successfully")
        return True
        
    except Exception as e:
        print(f"[INDEXER] ❌ Failed to index entry: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search(query: str, k: int = 3) -> None:
    """Test searching the vector database."""
    try:
        vector_db = get_vector_db()
        
        print(f"\n[INDEXER] 🔍 Testing search: '{query}'")
        
        results = vector_db.similarity_search(
            query,
            k=k,
            filter={"user_id": CURRENT_USER_ID}
        )
        print(f"[INDEXER] Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            timestamp = result.metadata.get('timestamp', 'unknown')
            content = result.page_content[:100]
            print(f"  {i}. [{timestamp}] {content}...")
    except Exception as e:
        print(f"[INDEXER] ❌ Search failed: {e}")

def get_db_stats() -> dict:
    """Get statistics about the vector database."""
    try:
        vector_db = get_vector_db()
        
        try:
            total_count = vector_db._collection.count()
        except:
            total_count = "Unknown"

        try:
            results = vector_db.similarity_search(
                "test",
                k=10000,  # Large number to get all
                filter={"user_id": CURRENT_USER_ID}
            )
            user_count = len(results)
        except:
            user_count = "Unknown"
        return {
            "total_documents": total_count,
            "user_documents": user_count,
            "database_path": VECTOR_DB_DIR,
            "user_id": CURRENT_USER_ID
        }  
    except Exception as e:
        return {
            "error": str(e)
        }

if __name__ == "__main__":
    print("="*80)
    print("REAL-TIME JOURNAL INDEXER TEST")
    print("="*80)

    print("\n1️⃣  Testing real-time indexing...")
    test_entry = f"Test entry created at {datetime.now()} - This is a test of real-time indexing."
    success = index_journal_entry(test_entry)
    if success:
        print("✅ Indexing successful")
    else:
        print("❌ Indexing failed")
    
    print("\n2️⃣  Testing search...")
    test_search("test entry real-time")

    print("\n3️⃣  Database statistics:")
    stats = get_db_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
