from typing import Any

from projectpulse.vector_store import (
    get_chroma_collection,
    load_embedding_model,
)


def retrieve(
    query: str,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve the most relevant ProjectPulse chunks
    for a natural-language query.
    """

    query = query.strip()

    if not query:
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    # Load our embedding model
    model = load_embedding_model()

    # Convert the user's question into a vector
    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
    )

    # Load the persistent Chroma collection
    collection = get_chroma_collection()

    stored_count = collection.count()

    if stored_count == 0:
        return []

    # Cannot request more results than we have stored
    result_count = min(
        top_k,
        stored_count,
    )

    # Semantic vector search
    results = collection.query(
        query_embeddings=[
            query_embedding.tolist()
        ],
        n_results=result_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    retrieved_documents = []

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for rank, (
        chunk_id,
        document,
        metadata,
        distance,
    ) in enumerate(
        zip(
            ids,
            documents,
            metadatas,
            distances,
        ),
        start=1,
    ):

        retrieved_documents.append(
            {
                "rank": rank,
                "chunk_id": chunk_id,
                "content": document,
                "metadata": metadata,
                "distance": float(distance),
            }
        )

    return retrieved_documents


def print_results(
    query: str,
    results: list[dict[str, Any]],
):
    """
    Pretty-print retrieved ProjectPulse evidence.
    """

    print("\n" + "=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)

    if not results:
        print("No relevant documents found.")
        return

    for result in results:

        metadata = result["metadata"]

        print(
            f"\nRank: {result['rank']}"
        )

        print(
            f"Distance: {result['distance']:.4f}"
        )

        print(
            f"Type: {metadata.get('type', '')}"
        )

        print(
            f"Title: {metadata.get('title', '')}"
        )

        print(
            f"URL: {metadata.get('url', '')}"
        )

        print("\nContent:")

        print(
            result["content"]
        )

        print("-" * 70)


def main():

    query = input(
        "Ask ProjectPulse: "
    )

    results = retrieve(
        query=query,
        top_k=3,
    )

    print_results(
        query=query,
        results=results,
    )


if __name__ == "__main__":
    main()