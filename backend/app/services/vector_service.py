"""Qdrant Vector database service for document RAG."""

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.config import get_settings

settings = get_settings()


def init_collection(client: QdrantClient):
    """Create the document chunks collection in Qdrant if not exists."""
    collection_name = "nexus_chunks"
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=1536,  # text-embedding-3-small dimensions
                    distance=models.Distance.COSINE
                )
            )
            print(f"Vector collection '{collection_name}' created.")
        else:
            print(f"Vector collection '{collection_name}' already exists.")
    except Exception as e:
        print(f"Failed to initialize Qdrant collection: {e}")
        raise e
