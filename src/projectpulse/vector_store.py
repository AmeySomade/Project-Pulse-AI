from pathlib import Path
from typing import Any
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from projectpulse.chunker import create_chunks, load_documents


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

CHROMA_PATH = Path("data/chroma")
COLLECTION_NAME = "projectpulse_github"


@lru_cache(maxsize=1)
def load_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once per Python process
    and reuse it for subsequent queries.
    """
    return SentenceTransformer(MODEL_NAME)


def prepare_metadata(
    metadata: dict[str, Any],
) -> dict[str, str]:
    """
    Convert metadata values into Chroma-safe string values.

    None values become empty strings.
    """

    cleaned_metadata = {}

    for key, value in metadata.items():
        if value is None:
            cleaned_metadata[key] = ""
        else:
            cleaned_metadata[key] = str(value)

    return cleaned_metadata


def get_chroma_collection():
    """
    Create or load the persistent ProjectPulse Chroma collection.
    """

    CHROMA_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        configuration={
            "hnsw": {
                "space": "cosine"
            }
        },
    )

    return collection


def index_chunks(
    chunks: list[dict[str, Any]],
):
    """
    Generate embeddings and store chunks inside ChromaDB.
    """

    if not chunks:
        raise ValueError("No chunks available for indexing.")

    print(f"Loading embedding model: {MODEL_NAME}")

    model = load_embedding_model()

    texts = [
        chunk["content"]
        for chunk in chunks
    ]

    print(
        f"Generating embeddings for {len(texts)} chunks..."
    )

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    collection = get_chroma_collection()

    ids = [
        chunk["chunk_id"]
        for chunk in chunks
    ]

    metadatas = [
        prepare_metadata(chunk["metadata"])
        for chunk in chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=metadatas,
    )

    return collection, embeddings


def main():

    print("Loading normalized GitHub documents...")

    documents = load_documents()

    chunks = create_chunks(documents)

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")

    collection, embeddings = index_chunks(chunks)

    print("\nVector indexing completed successfully.")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Stored vectors: {collection.count()}")

    if len(embeddings) > 0:
        print(
            f"Embedding dimensions: {len(embeddings[0])}"
        )


if __name__ == "__main__":
    main()