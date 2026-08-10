from src.projectpulse.chunker import split_text, create_chunks


def test_short_text_creates_single_chunk():
    text = "ProjectPulse retrieves project information."

    chunks = split_text(
        text=text,
        chunk_size=100,
        overlap=20,
    )

    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_creates_multiple_chunks():
    text = "A" * 200

    chunks = split_text(
        text=text,
        chunk_size=100,
        overlap=20,
    )

    assert len(chunks) == 3

    assert len(chunks[0]) == 100
    assert len(chunks[1]) == 100
    assert len(chunks[2]) == 40


def test_chunk_overlap():
    text = "".join(
        str(i % 10)
        for i in range(150)
    )

    chunks = split_text(
        text=text,
        chunk_size=100,
        overlap=20,
    )

    first_chunk_overlap = chunks[0][-20:]
    second_chunk_start = chunks[1][:20]

    assert first_chunk_overlap == second_chunk_start


def test_create_chunks_preserves_metadata():

    documents = [
        {
            "id": "github_commit_123",
            "source": "github",
            "type": "commit",
            "title": "Add retrieval layer",
            "content": "Added semantic retrieval to ProjectPulse.",
            "url": "https://github.com/example/repo/commit/123",
            "created_at": "2026-08-10T10:00:00Z",
            "updated_at": "2026-08-10T10:00:00Z",
        }
    ]

    chunks = create_chunks(documents)

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk["document_id"] == "github_commit_123"
    assert chunk["metadata"]["source"] == "github"
    assert chunk["metadata"]["type"] == "commit"
    assert chunk["metadata"]["title"] == "Add retrieval layer"