import os
from typing import List, Optional

_index = None
_embeddings = None

def get_pinecone_index():
    global _index
    if _index is None:
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                return None
            from pinecone import Pinecone
            pc = Pinecone(api_key=api_key)
            index_name = os.getenv("PINECONE_INDEX", "aura-memory")
            _index = pc.Index(index_name)
        except Exception as e:
            print(f"⚠️ [PINECONE INIT NOTICE]: {e}")
            return None
    return _index

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        try:
            google_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not google_key:
                return None
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            _embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=google_key)
        except Exception as e:
            print(f"⚠️ [EMBEDDINGS INIT NOTICE]: {e}")
            return None
    return _embeddings

def save_to_memory(user_id: str, text: str) -> bool:
    """Saves user memory to vector database lazily and safely."""
    try:
        index = get_pinecone_index()
        embeddings = get_embeddings()
        if not index or not embeddings:
            return False

        vector = embeddings.embed_query(text)
        index.upsert(
            vectors=[
                {"id": f"{user_id}_{abs(hash(text))}", "values": vector, "metadata": {"user_id": user_id, "text": text}}
            ]
        )
        return True
    except Exception as e:
        print(f"⚠️ [VECTOR DB SAVE ERROR]: {e}")
        return False

def search_memory(user_id: str, query: str, top_k: int = 3) -> List[str]:
    """Retrieves memories by semantic similarity."""
    try:
        index = get_pinecone_index()
        embeddings = get_embeddings()
        if not index or not embeddings:
            return []

        query_vector = embeddings.embed_query(query)
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter={"user_id": {"$eq": user_id}} 
        )
        return [match['metadata']['text'] for match in results.get('matches', []) if 'metadata' in match]
    except Exception as e:
        print(f"⚠️ [VECTOR DB SEARCH ERROR]: {e}")
        return []