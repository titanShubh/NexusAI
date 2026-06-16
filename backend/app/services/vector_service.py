"""Qdrant Vector database service for document RAG."""

from typing import Any, Optional
from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import get_settings

settings = get_settings()


def get_qdrant_client() -> QdrantClient:
    """Get initialized Qdrant client, supporting local and cloud configurations."""
    host = settings.qdrant_host
    api_key = settings.qdrant_api_key or None
    
    # If host starts with http:// or https://, use url parameter
    if host.startswith(("http://", "https://")):
        return QdrantClient(
            url=host,
            api_key=api_key
        )
    
    # If API key is set and host looks like a domain or is "qdrant"
    if api_key and ("." in host or host == "qdrant"):
        url = host
        if not url.startswith("https://"):
            url = f"https://{url}"
        
        if settings.qdrant_port:
            if not url.endswith(f":{settings.qdrant_port}"):
                url = f"{url}:{settings.qdrant_port}"
                
        return QdrantClient(
            url=url,
            api_key=api_key
        )
        
    # Default local fallback
    return QdrantClient(
        host=host,
        port=settings.qdrant_port,
        api_key=api_key
    )


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


def upsert_document_chunks(
    client: QdrantClient,
    chunks: list[dict[str, Any]]
) -> None:
    """
    Upsert document chunks to Qdrant vector database.
    Each chunk dict should contain:
    - id (UUID)
    - vector (list of 1536 floats)
    - document_id (UUID)
    - content (str)
    - page_number (int)
    - chunk_type (str)
    - metadata (dict)
    """
    # Ensure collection exists before upserting
    init_collection(client)
    points = []
    for chunk in chunks:
        points.append(
            models.PointStruct(
                id=str(chunk["id"]),
                vector=chunk["vector"],
                payload={
                    "document_id": str(chunk["document_id"]),
                    "content": chunk["content"],
                    "page_number": chunk["page_number"],
                    "chunk_type": chunk["chunk_type"],
                    "metadata": chunk.get("metadata", {})
                }
            )
        )
    
    if points:
        client.upsert(
            collection_name="nexus_chunks",
            wait=True,
            points=points
        )


def delete_document_vectors(client: QdrantClient, document_id: UUID) -> None:
    """Delete all vectors matching document_id."""
    try:
        client.delete(
            collection_name="nexus_chunks",
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id))
                        )
                    ]
                )
            )
        )
    except UnexpectedResponse as e:
        if e.status_code == 404:
            print(f"Collection 'nexus_chunks' does not exist during deletion of document {document_id}. Skipping.")
        else:
            raise e


def search_vectors(
    client: QdrantClient,
    query_vector: list[float],
    limit: int = 10,
    document_ids: Optional[list[UUID]] = None
) -> list[dict[str, Any]]:
    """
    Search Qdrant vector database for nearest neighbors.
    Optionally filter by document_ids.
    """
    filter_cond = None
    if document_ids:
        filter_cond = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=[str(d_id) for d_id in document_ids])
                )
            ]
        )

    try:
        response = client.query_points(
            collection_name="nexus_chunks",
            query=query_vector,
            limit=limit,
            query_filter=filter_cond,
            with_payload=True
        )
        results = response.points
    except UnexpectedResponse as e:
        if e.status_code == 404:
            print("Collection 'nexus_chunks' does not exist during search. Returning empty list.")
            return []
        raise e

    hits = []
    for hit in results:
        hits.append({
            "chunk_id": UUID(hit.id) if hit.id else None,
            "document_id": UUID(hit.payload["document_id"]) if hit.payload.get("document_id") else None,
            "content": hit.payload.get("content", ""),
            "page_number": hit.payload.get("page_number", 1),
            "chunk_type": hit.payload.get("chunk_type", "text"),
            "metadata": hit.payload.get("metadata", {}),
            "score": hit.score
        })
    return hits
