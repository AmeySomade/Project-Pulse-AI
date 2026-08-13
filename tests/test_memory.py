import pytest

from projectpulse.memory import (
    MemoryStore,
    ShortTermMemory,
    classify_memory,
    remember_if_important,
)


# ---------------------------------------------------------
# Short-term memory
# ---------------------------------------------------------

def test_short_term_memory_keeps_recent_items():
    memory = ShortTermMemory(max_items=2)

    memory.add("user", "first")
    memory.add("assistant", "second")
    memory.add("user", "third")

    context = memory.get_context()

    assert len(context) == 2
    assert context[0]["content"] == "second"
    assert context[1]["content"] == "third"


# ---------------------------------------------------------
# Selective memory classification
# ---------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected_category"),
    [
        (
            "We decided to use ChromaDB for retrieval.",
            "decision",
        ),
        (
            "The ingestion pipeline is blocked by an API error.",
            "blocker",
        ),
        (
            "I prefer concise project summaries.",
            "preference",
        ),
        (
            "MCP integration is completed.",
            "status",
        ),
    ],
)
def test_memory_classification(
    text,
    expected_category,
):
    assert (
        classify_memory(text)
        == expected_category
    )


def test_normal_question_is_not_long_term_memory():
    assert (
        classify_memory(
            "What changed in ProjectPulse?"
        )
        is None
    )


def test_irrelevant_statement_is_not_long_term_memory():
    assert (
        classify_memory(
            "Hello ProjectPulse."
        )
        is None
    )


# ---------------------------------------------------------
# Persistent memory
# ---------------------------------------------------------

def test_memory_store_persists_between_instances(
    tmp_path,
):
    memory_file = tmp_path / "memory.json"

    store = MemoryStore(memory_file)

    record = store.add(
        content=(
            "We decided to use MCP for tool integration."
        ),
        category="decision",
    )

    reloaded_store = MemoryStore(memory_file)

    records = reloaded_store.list_memories()

    assert len(records) == 1
    assert records[0].memory_id == record.memory_id
    assert (
        records[0].content
        == "We decided to use MCP for tool integration."
    )


def test_memory_store_deduplicates_records(
    tmp_path,
):
    store = MemoryStore(
        tmp_path / "memory.json"
    )

    first = store.add(
        content="MCP integration is completed.",
        category="status",
    )

    second = store.add(
        content="MCP integration is completed.",
        category="status",
    )

    assert first.memory_id == second.memory_id
    assert len(store.list_memories()) == 1


def test_selective_memory_only_saves_important_text(
    tmp_path,
):
    store = MemoryStore(
        tmp_path / "memory.json"
    )

    ignored = remember_if_important(
        store,
        "Hello ProjectPulse.",
    )

    remembered = remember_if_important(
        store,
        "We decided to use LangGraph for orchestration.",
    )

    assert ignored is None
    assert remembered is not None
    assert remembered.category == "decision"
    assert len(store.list_memories()) == 1


def test_memory_search_returns_relevant_record(
    tmp_path,
):
    store = MemoryStore(
        tmp_path / "memory.json"
    )

    store.add(
        content=(
            "We decided to use MCP for tool integration."
        ),
        category="decision",
    )

    store.add(
        content=(
            "The ingestion pipeline is blocked by GitHub API errors."
        ),
        category="blocker",
    )

    results = store.search(
        "MCP integration"
    )

    assert len(results) == 1
    assert results[0].category == "decision"