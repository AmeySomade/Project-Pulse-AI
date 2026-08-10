import json
from pathlib import Path
from typing import Any


DEFAULT_INPUT_PATH = Path("data/github_documents.json")


def split_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[str]:
    """
    Split text into overlapping character chunks.

    Example:
        chunk_size = 800
        overlap = 150

    Chunk 1 -> characters 0-799
    Chunk 2 -> characters 650-1449
    """

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def create_chunks(
    documents: list[dict[str, Any]],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict[str, Any]]:
    """
    Convert normalized GitHub documents into smaller retrieval chunks.
    """

    all_chunks = []

    for document_index, document in enumerate(documents):

        content = document.get("content", "")

        text_chunks = split_text(
            text=content,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, chunk_text in enumerate(text_chunks):

            chunk = {
                "chunk_id": f"doc_{document_index}_chunk_{chunk_index}",
                "document_id": document.get(
                    "id",
                    f"doc_{document_index}",
                ),
                "chunk_index": chunk_index,
                "content": chunk_text,
                "metadata": {
                    "source": document.get("source"),
                    "type": document.get("type"),
                    "title": document.get("title"),
                    "url": document.get("url"),
                    "created_at": document.get("created_at"),
                    "updated_at": document.get("updated_at"),
                },
            }

            all_chunks.append(chunk)

    return all_chunks


def load_documents(
    input_path: Path = DEFAULT_INPUT_PATH,
) -> list[dict[str, Any]]:

    if not input_path.exists():
        raise FileNotFoundError(
            f"Document file not found: {input_path}"
        )

    with input_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        documents = json.load(file)

    if not isinstance(documents, list):
        raise ValueError(
            "Expected github_documents.json to contain a JSON list."
        )

    return documents


def main():

    documents = load_documents()

    chunks = create_chunks(documents)

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")

    if chunks:

        print("\nSample chunk")
        print("-" * 60)

        sample = chunks[0]

        print(f"Chunk ID: {sample['chunk_id']}")
        print(f"Document ID: {sample['document_id']}")
        print(f"Type: {sample['metadata']['type']}")
        print(f"Title: {sample['metadata']['title']}")

        print("\nContent:")
        print(sample["content"][:500])


if __name__ == "__main__":
    main()