import asyncio
import json

import pytest

import projectpulse.ui_service as ui_service
from projectpulse.memory import MemoryStore, ShortTermMemory
from projectpulse.ui_service import (
    extract_evidence,
    extract_plan,
    normalize_tool_payload,
    run_projectpulse_query,
    summarize_graph_result,
)


def test_normalize_tool_payload_accepts_json_text():
    payload = {
        "query": "GitHub integration",
        "results": [],
    }

    assert normalize_tool_payload(
        json.dumps(payload)
    ) == payload


def test_normalize_tool_payload_accepts_mcp_text_block():
    payload = {
        "query": "project status",
        "evidence": [],
    }

    assert normalize_tool_payload(
        [
            {
                "type": "text",
                "text": json.dumps(payload),
            }
        ]
    ) == payload


def test_extract_evidence_supports_direct_search_result():
    evidence = {
        "chunk_id": "chunk_1",
        "content": "GitHub integration was added.",
    }

    graph_result = {
        "result": {
            "results": [evidence],
        }
    }

    assert extract_evidence(graph_result) == [evidence]


def test_extract_evidence_and_plan_support_investigation_result():
    evidence = {
        "chunk_id": "chunk_2",
        "content": "The project status changed.",
    }

    plan = {
        "intent": "status",
        "sub_queries": [
            "latest project status",
            "recent project changes",
        ],
    }

    graph_result = {
        "result": {
            "plan": plan,
            "evidence": [evidence],
        }
    }

    assert extract_evidence(graph_result) == [evidence]
    assert extract_plan(graph_result) == plan


def test_summarize_graph_result_describes_direct_evidence():
    graph_result = {
        "selected_tool": "search_project_history",
        "result": {
            "results": [
                {"chunk_id": "chunk_1"},
                {"chunk_id": "chunk_2"},
            ]
        },
    }

    assert summarize_graph_result(graph_result) == (
        "ProjectPulse found 2 relevant project-history evidence items."
    )


def test_summarize_graph_result_describes_investigation():
    graph_result = {
        "selected_tool": "investigate_project",
        "result": {
            "plan": {
                "sub_queries": ["one", "two", "three"],
            },
            "evidence": [
                {"chunk_id": "chunk_1"},
            ],
        },
    }

    assert summarize_graph_result(graph_result) == (
        "ProjectPulse ran 3 focused investigation queries and found "
        "1 unique evidence item."
    )


def test_run_projectpulse_query_rejects_empty_query_before_mcp():
    with pytest.raises(
        ValueError,
        match="Query cannot be empty",
    ):
        asyncio.run(
            run_projectpulse_query("   ")
        )


def test_run_projectpulse_query_rejects_invalid_top_k_before_mcp():
    with pytest.raises(
        ValueError,
        match="top_k must be greater than 0",
    ):
        asyncio.run(
            run_projectpulse_query(
                "What changed?",
                top_k=0,
            )
        )


def test_run_projectpulse_query_wires_mcp_graph_and_memory(
    monkeypatch,
    tmp_path,
):
    observed = {}
    fake_session = object()
    fake_tools = [object(), object()]

    class FakeSessionContext:
        async def __aenter__(self):
            return fake_session

        async def __aexit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

    class FakeClient:
        def session(self, server_name):
            observed["server_name"] = server_name
            return FakeSessionContext()

    class FakeGraph:
        async def ainvoke(self, state):
            observed["state"] = state
            return {
                "query": state["query"],
                "selected_tool": "search_project_history",
                "result": {"results": []},
            }

    async def fake_load_mcp_tools(session):
        observed["session"] = session
        return fake_tools

    def fake_build_projectpulse_graph(
        tools,
        memory_store,
        short_term_memory,
    ):
        observed["tools"] = tools
        observed["memory_store"] = memory_store
        observed["short_term_memory"] = short_term_memory
        return FakeGraph()

    monkeypatch.setattr(
        ui_service,
        "create_mcp_client",
        lambda: FakeClient(),
    )

    monkeypatch.setattr(
        ui_service,
        "load_mcp_tools",
        fake_load_mcp_tools,
    )

    monkeypatch.setattr(
        ui_service,
        "build_projectpulse_graph",
        fake_build_projectpulse_graph,
    )

    store = MemoryStore(
        tmp_path / "memory.json"
    )

    short_term = ShortTermMemory(
        max_items=6
    )

    result = asyncio.run(
        run_projectpulse_query(
            "  What changed?  ",
            top_k=3,
            memory_store=store,
            short_term_memory=short_term,
        )
    )

    assert observed["server_name"] == "projectpulse"
    assert observed["session"] is fake_session
    assert observed["tools"] is fake_tools
    assert observed["memory_store"] is store
    assert observed["short_term_memory"] is short_term
    assert observed["state"] == {
        "query": "What changed?",
        "top_k": 3,
    }
    assert result["query"] == "What changed?"
