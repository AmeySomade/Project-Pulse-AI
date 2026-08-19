from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from langchain_mcp_adapters.tools import load_mcp_tools

from projectpulse.langgraph_agent import build_projectpulse_graph
from projectpulse.mcp_client import create_mcp_client
from projectpulse.memory import MemoryStore, ShortTermMemory


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object while treating normal text as unstructured."""

    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    return {}


def normalize_tool_payload(value: Any) -> dict[str, Any]:
    """
    Normalize the result returned by an MCP-discovered tool.

    Current ProjectPulse MCP tools return dictionaries. The extra handling for
    JSON text and MCP text-content blocks keeps the UI stable if the adapter's
    result representation changes in a future dependency update.
    """

    if isinstance(value, Mapping):
        return dict(value)

    if isinstance(value, str):
        return _parse_json_object(value)

    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                if "structuredContent" in item:
                    normalized = normalize_tool_payload(
                        item["structuredContent"]
                    )
                    if normalized:
                        return normalized

                text = item.get("text")

                if isinstance(text, str):
                    normalized = _parse_json_object(text)
                    if normalized:
                        return normalized

    return {}


def extract_evidence(
    graph_result: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return evidence from either ProjectPulse retrieval route."""

    payload = normalize_tool_payload(
        graph_result.get("result")
    )

    raw_evidence = payload.get("evidence")

    if raw_evidence is None:
        raw_evidence = payload.get("results", [])

    if not isinstance(raw_evidence, list):
        return []

    return [
        dict(item)
        for item in raw_evidence
        if isinstance(item, Mapping)
    ]


def extract_plan(
    graph_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the investigation plan when the selected route produced one."""

    payload = normalize_tool_payload(
        graph_result.get("result")
    )

    plan = payload.get("plan", {})

    if isinstance(plan, Mapping):
        return dict(plan)

    return {}


def summarize_graph_result(
    graph_result: Mapping[str, Any],
) -> str:
    """Create a factual UI summary without pretending to synthesize an LLM answer."""

    evidence_count = len(
        extract_evidence(graph_result)
    )

    if evidence_count == 0:
        return (
            "No matching evidence was found in the currently indexed "
            "ProjectPulse history."
        )

    selected_tool = graph_result.get(
        "selected_tool",
        "",
    )

    if selected_tool == "investigate_project":
        plan = extract_plan(graph_result)
        sub_queries = plan.get("sub_queries", [])
        sub_query_count = (
            len(sub_queries)
            if isinstance(sub_queries, list)
            else 0
        )

        return (
            f"ProjectPulse ran {sub_query_count} focused investigation "
            f"queries and found {evidence_count} unique evidence "
            f"item{'s' if evidence_count != 1 else ''}."
        )

    return (
        f"ProjectPulse found {evidence_count} relevant project-history "
        f"evidence item{'s' if evidence_count != 1 else ''}."
    )


async def run_projectpulse_query(
    query: str,
    top_k: int = 2,
    memory_store: MemoryStore | None = None,
    short_term_memory: ShortTermMemory | None = None,
) -> dict[str, Any]:
    """
    Execute one UI query through the real LangGraph -> MCP pipeline.

    The Streamlit layer supplies a session-scoped ShortTermMemory instance so
    conversational context survives Streamlit reruns. Long-term memory remains
    backed by ProjectPulse's existing JSON store.
    """

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError("Query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than 0.")

    persistent_memory = (
        memory_store
        if memory_store is not None
        else MemoryStore()
    )

    conversation_memory = (
        short_term_memory
        if short_term_memory is not None
        else ShortTermMemory(max_items=6)
    )

    client = create_mcp_client()

    async with client.session("projectpulse") as session:
        tools = await load_mcp_tools(session)

        graph = build_projectpulse_graph(
            tools=tools,
            memory_store=persistent_memory,
            short_term_memory=conversation_memory,
        )

        result = await graph.ainvoke(
            {
                "query": cleaned_query,
                "top_k": top_k,
            }
        )

    return dict(result)
