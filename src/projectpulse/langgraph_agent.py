import asyncio
from typing import Any, Literal, TypedDict

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import END, START, StateGraph

from projectpulse.mcp_client import create_mcp_client
from projectpulse.planner import create_plan


# ---------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------

class ProjectPulseState(TypedDict, total=False):
    """
    Shared state that moves through the ProjectPulse graph.
    """

    query: str
    intent: str
    selected_tool: str
    top_k: int
    result: Any


# ---------------------------------------------------------
# Graph construction
# ---------------------------------------------------------

def build_projectpulse_graph(
    tools: list[BaseTool],
):
    """
    Build a LangGraph workflow around MCP-discovered tools.
    """

    tool_map = {
        tool.name: tool
        for tool in tools
    }

    required_tools = {
        "search_project_history",
        "investigate_project",
    }

    missing_tools = (
        required_tools - set(tool_map.keys())
    )

    if missing_tools:
        raise RuntimeError(
            f"Missing required MCP tools: {missing_tools}"
        )

    # -----------------------------------------------------
    # Node 1: Planner / router
    # -----------------------------------------------------

    def plan_route(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Detect the user's intent and select the appropriate
        MCP capability.
        """

        query = state["query"].strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        plan = create_plan(query)

        # General/focused questions only need one
        # semantic retrieval call.
        if plan.intent == "general":
            selected_tool = (
                "search_project_history"
            )

        # Complex project questions benefit from the
        # planner + multi-query investigation pipeline.
        else:
            selected_tool = (
                "investigate_project"
            )

        return {
            "query": query,
            "intent": plan.intent,
            "selected_tool": selected_tool,
        }

    # -----------------------------------------------------
    # Conditional routing
    # -----------------------------------------------------

    def choose_route(
        state: ProjectPulseState,
    ) -> Literal[
        "direct_search",
        "investigation",
    ]:
        """
        Convert selected MCP tool into a graph branch.
        """

        if (
            state["selected_tool"]
            == "search_project_history"
        ):
            return "direct_search"

        return "investigation"

    # -----------------------------------------------------
    # Node 2A: Direct semantic retrieval through MCP
    # -----------------------------------------------------

    async def direct_search(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Invoke the direct-search MCP tool.
        """

        top_k = state.get(
            "top_k",
            2,
        )

        result = await tool_map[
            "search_project_history"
        ].ainvoke(
            {
                "query": state["query"],
                "top_k": top_k,
            }
        )

        return {
            "result": result,
        }

    # -----------------------------------------------------
    # Node 2B: Multi-step investigation through MCP
    # -----------------------------------------------------

    async def investigation(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Invoke the multi-step investigation MCP tool.
        """

        top_k = state.get(
            "top_k",
            2,
        )

        result = await tool_map[
            "investigate_project"
        ].ainvoke(
            {
                "query": state["query"],
                "top_k_per_query": top_k,
            }
        )

        return {
            "result": result,
        }

    # -----------------------------------------------------
    # Assemble graph
    # -----------------------------------------------------

    builder = StateGraph(
        ProjectPulseState
    )

    builder.add_node(
        "plan_route",
        plan_route,
    )

    builder.add_node(
        "direct_search",
        direct_search,
    )

    builder.add_node(
        "investigation",
        investigation,
    )

    builder.add_edge(
        START,
        "plan_route",
    )

    builder.add_conditional_edges(
        "plan_route",
        choose_route,
        {
            "direct_search": "direct_search",
            "investigation": "investigation",
        },
    )

    builder.add_edge(
        "direct_search",
        END,
    )

    builder.add_edge(
        "investigation",
        END,
    )

    return builder.compile()


# ---------------------------------------------------------
# Demo
# ---------------------------------------------------------

async def main():
    client = create_mcp_client()

    print("=" * 70)
    print("PROJECTPULSE LANGGRAPH + MCP AGENT")
    print("=" * 70)

    async with client.session(
        "projectpulse"
    ) as session:

        tools = await load_mcp_tools(
            session
        )

        graph = build_projectpulse_graph(
            tools
        )

        test_queries = [
            (
                "What work was done on "
                "GitHub integration?"
            ),
            (
                "What changed in ProjectPulse "
                "and what is the current "
                "project status?"
            ),
        ]

        for query in test_queries:

            print("\n" + "=" * 70)
            print(f"QUERY: {query}")
            print("=" * 70)

            result = await graph.ainvoke(
                {
                    "query": query,
                    "top_k": 2,
                }
            )

            print(
                f"\nDetected intent: "
                f"{result['intent']}"
            )

            print(
                f"Selected MCP tool: "
                f"{result['selected_tool']}"
            )

            print(
                "\nTool result:"
            )

            print(
                result["result"]
            )

    print("\n" + "=" * 70)
    print(
        "LANGGRAPH + MCP VERIFICATION PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())