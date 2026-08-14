import asyncio

import pytest

from projectpulse.langgraph_agent import build_projectpulse_graph


class FakeMCPTool:
    """
    Lightweight stand-in for an MCP-discovered LangChain tool.

    It records every invocation so tests can verify that
    LangGraph routed the query to the correct MCP capability.

    The optional config argument mirrors the Runnable/LangChain
    tool interface used by the real MCP-discovered tools.
    """

    def __init__(self, name: str):
        self.name = name
        self.calls = []

    async def ainvoke(
        self,
        arguments,
        config=None,
    ):
        self.calls.append(arguments)

        return {
            "tool": self.name,
            "arguments": arguments,
        }


def create_fake_tools():
    search_tool = FakeMCPTool(
        "search_project_history"
    )

    investigation_tool = FakeMCPTool(
        "investigate_project"
    )

    return search_tool, investigation_tool


def test_general_query_routes_to_direct_search():
    search_tool, investigation_tool = create_fake_tools()

    graph = build_projectpulse_graph(
        [
            search_tool,
            investigation_tool,
        ]
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "What work was done on "
                    "GitHub integration?"
                ),
                "top_k": 2,
            }
        )
    )

    assert result["intent"] == "general"

    assert (
        result["selected_tool"]
        == "search_project_history"
    )

    assert len(search_tool.calls) == 1
    assert len(investigation_tool.calls) == 0

    assert search_tool.calls[0] == {
        "query": (
            "What work was done on "
            "GitHub integration?"
        ),
        "top_k": 2,
    }


def test_status_query_routes_to_investigation():
    search_tool, investigation_tool = create_fake_tools()

    graph = build_projectpulse_graph(
        [
            search_tool,
            investigation_tool,
        ]
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "query": (
                    "What changed in ProjectPulse "
                    "and what is the current "
                    "project status?"
                ),
                "top_k": 3,
            }
        )
    )

    assert result["intent"] == "status"

    assert (
        result["selected_tool"]
        == "investigate_project"
    )

    assert len(search_tool.calls) == 0
    assert len(investigation_tool.calls) == 1

    assert investigation_tool.calls[0] == {
        "query": (
            "What changed in ProjectPulse "
            "and what is the current "
            "project status?"
        ),
        "top_k_per_query": 3,
    }


def test_graph_rejects_missing_required_mcp_tool():
    search_tool = FakeMCPTool(
        "search_project_history"
    )

    with pytest.raises(
        RuntimeError,
        match="Missing required MCP tools",
    ):
        build_projectpulse_graph(
            [search_tool]
        )


def test_graph_rejects_empty_query():
    search_tool, investigation_tool = create_fake_tools()

    graph = build_projectpulse_graph(
        [
            search_tool,
            investigation_tool,
        ]
    )

    with pytest.raises(
        ValueError,
        match="Query cannot be empty",
    ):
        asyncio.run(
            graph.ainvoke(
                {
                    "query": "   ",
                }
            )
        )