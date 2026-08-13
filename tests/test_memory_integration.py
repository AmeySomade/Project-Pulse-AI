import asyncio

from langchain_core.tools import tool

from projectpulse.langgraph_agent import (
    build_projectpulse_graph,
)
from projectpulse.memory import (
    MemoryStore,
    ShortTermMemory,
)


# ---------------------------------------------------------
# Fake MCP-compatible tools
# ---------------------------------------------------------

@tool
def search_project_history(
    query: str,
    top_k: int = 2,
) -> dict:
    """
    Fake direct project-history search for graph tests.
    """
    return {
        "tool": "search_project_history",
        "query": query,
        "top_k": top_k,
    }


@tool
def investigate_project(
    query: str,
    top_k_per_query: int = 2,
) -> dict:
    """
    Fake multi-step investigation for graph tests.
    """
    return {
        "tool": "investigate_project",
        "query": query,
        "top_k_per_query": top_k_per_query,
    }


def _build_test_graph(
    tmp_path,
    max_items: int = 6,
):
    store = MemoryStore(
        tmp_path / "memory.json"
    )

    short_term = ShortTermMemory(
        max_items=max_items
    )

    graph = build_projectpulse_graph(
        tools=[
            search_project_history,
            investigate_project,
        ],
        memory_store=store,
        short_term_memory=short_term,
    )

    return graph, store, short_term


# ---------------------------------------------------------
# Long-term memory retrieval
# ---------------------------------------------------------

def test_graph_loads_relevant_long_term_memory(
    tmp_path,
):
    graph, store, _ = _build_test_graph(
        tmp_path
    )

    store.add(
        content=(
            "We decided to use MCP "
            "for tool integration."
        ),
        category="decision",
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "What MCP integration "
                    "decision was made?"
                ),
                "top_k": 2,
            }
        )
    )

    memories = result[
        "relevant_memories"
    ]

    assert len(memories) == 1
    assert memories[0]["category"] == "decision"
    assert "MCP" in memories[0]["content"]


# ---------------------------------------------------------
# Selective persistent memory
# ---------------------------------------------------------

def test_graph_persists_important_user_statement(
    tmp_path,
):
    graph, store, _ = _build_test_graph(
        tmp_path
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "We decided to use SQLite "
                    "for durable memory."
                ),
                "top_k": 2,
            }
        )
    )

    stored_memory = result[
        "stored_memory"
    ]

    assert stored_memory is not None
    assert (
        stored_memory["category"]
        == "decision"
    )

    memories = store.list_memories()

    assert len(memories) == 1
    assert (
        "SQLite"
        in memories[0].content
    )


def test_graph_does_not_persist_normal_question(
    tmp_path,
):
    graph, store, _ = _build_test_graph(
        tmp_path
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "What work was done "
                    "on GitHub integration?"
                )
            }
        )
    )

    assert result["stored_memory"] is None
    assert store.list_memories() == []


# ---------------------------------------------------------
# Short-term conversation memory
# ---------------------------------------------------------

def test_graph_keeps_short_term_context_across_calls(
    tmp_path,
):
    graph, _, short_term = _build_test_graph(
        tmp_path,
        max_items=6,
    )

    asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "What work was done "
                    "on GitHub integration?"
                )
            }
        )
    )

    second_result = asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "What is the current "
                    "project status?"
                )
            }
        )
    )

    context = second_result[
        "recent_context"
    ]

    assert len(context) == 4

    assert context[0]["role"] == "user"
    assert (
        "GitHub integration"
        in context[0]["content"]
    )

    assert context[1]["role"] == "assistant"

    assert context[2]["role"] == "user"
    assert (
        "current project status"
        in context[2]["content"]
    )

    assert context[3]["role"] == "assistant"

    assert (
        short_term.get_context()
        == context
    )


# ---------------------------------------------------------
# Memory configuration validation
# ---------------------------------------------------------

def test_graph_rejects_invalid_memory_search_limit(
    tmp_path,
):
    store = MemoryStore(
        tmp_path / "memory.json"
    )

    short_term = ShortTermMemory()

    try:
        build_projectpulse_graph(
            tools=[
                search_project_history,
                investigate_project,
            ],
            memory_store=store,
            short_term_memory=short_term,
            memory_search_limit=0,
        )
    except ValueError as error:
        assert (
            "memory_search_limit"
            in str(error)
        )
    else:
        raise AssertionError(
            "Expected ValueError."
        )