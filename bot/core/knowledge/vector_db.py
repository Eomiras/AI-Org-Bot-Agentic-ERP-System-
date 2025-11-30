from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
from bot.core.config import settings
from functools import lru_cache

COLLECTION_NAME = "org_knowledge"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_SIZE = 384

@lru_cache(maxsize=1)
def get_embeddings():
    """
    Returns the HuggingFace embeddings model.
    Cached to avoid reloading the model on every call.
    """
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

def get_qdrant_client() -> QdrantClient:
    """Returns a configured QdrantClient."""
    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

def ensure_collection_exists(client: QdrantClient):
    """Checks if the collection exists, and creates it if not."""
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)

    if not exists:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE
            )
        )

def get_vector_store() -> QdrantVectorStore:
    """Returns the Qdrant vector store wrapper."""
    client = get_qdrant_client()
    ensure_collection_exists(client)

    embeddings = get_embeddings()

    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

def get_retriever():
    """Returns the retriever interface for the vector store."""
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": 3})
