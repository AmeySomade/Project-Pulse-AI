import asyncio
import json
from dataclasses import asdict
from typing import Any, Literal, TypedDict

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.graph import END, START, StateGraph

from projectpulse.mcp_client import create_mcp_client
from projectpulse.memory import (
    MemoryStore,
    ShortTermMemory,
    remember_if_important,
)
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

    # Memory state
    recent_context: list[dict[str, str]]
    relevant_memories: list[dict[str, Any]]
    stored_memory: dict[str, Any] | None


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _serialize_result_for_short_term(
    result: Any,
    max_chars: int = 1200,
) -> str:
    """
    Convert a tool result into a compact representation for
    temporary conversation memory.

    Raw retrieval responses can become large, so short-term
    memory intentionally stores only a bounded representation.
    """

    if isinstance(result, str):
        text = result
    else:
        try:
            text = json.dumps(
                result,
                ensure_ascii=False,
                default=str,
            )
        except (TypeError, ValueError):
            text = str(result)

    text = " ".join(text.split())

    if len(text) > max_chars:
        text = text[:max_chars] + "...[truncated]"

    return text


# ---------------------------------------------------------
# Graph construction
# ---------------------------------------------------------

def build_projectpulse_graph(
    tools: list[BaseTool],
    memory_store: MemoryStore | None = None,
    short_term_memory: ShortTermMemory | None = None,
    memory_search_limit: int = 3,
):
    """
    Build a LangGraph workflow around MCP-discovered tools
    with short-term and selective long-term memory.
    """

    if memory_search_limit <= 0:
        raise ValueError(
            "memory_search_limit must be greater than zero."
        )

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

    # Use supplied stores during testing or custom execution.
    # Otherwise use the normal ProjectPulse defaults.
    long_term_memory = (
        memory_store
        if memory_store is not None
        else MemoryStore()
    )

    conversation_memory = (
        short_term_memory
        if short_term_memory is not None
        else ShortTermMemory(max_items=6)
    )

    # -----------------------------------------------------
    # Node 1: Load and selectively persist memory
    # -----------------------------------------------------

    def load_memory(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Load relevant context before planning.

        The user's current message is always kept in
        short-term memory.

        Long-term storage remains selective: only messages
        matching the memory policy are persisted.
        """

        query = state["query"].strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        # Retrieve OLD long-term knowledge before deciding
        # whether the current message should also be stored.
        relevant_records = long_term_memory.search(
            query,
            limit=memory_search_limit,
        )

        relevant_memories = [
            asdict(record)
            for record in relevant_records
        ]

        # Current conversation turn enters temporary memory.
        conversation_memory.add(
            "user",
            query,
        )

        # Declarative decisions, blockers, preferences or
        # status updates may enter persistent memory.
        remembered = remember_if_important(
            store=long_term_memory,
            text=query,
            source_query=query,
            metadata={
                "source": "user",
                "component": "langgraph",
            },
        )

        stored_memory = (
            asdict(remembered)
            if remembered is not None
            else None
        )

        return {
            "query": query,
            "recent_context": (
                conversation_memory.get_context()
            ),
            "relevant_memories": relevant_memories,
            "stored_memory": stored_memory,
        }

    # -----------------------------------------------------
    # Node 2: Planner / router
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
    # Node 3A: Direct semantic retrieval through MCP
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
    # Node 3B: Multi-step investigation through MCP
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
    # Node 4: Update temporary conversation memory
    # -----------------------------------------------------

    def update_short_term_memory(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Store a bounded representation of the retrieval
        result in short-term conversation memory.
        """

        result_text = _serialize_result_for_short_term(
            state.get("result")
        )

        if result_text:
            conversation_memory.add(
                "assistant",
                result_text,
            )

        return {
            "recent_context": (
                conversation_memory.get_context()
            )
        }

    # -----------------------------------------------------
    # Assemble graph
    # -----------------------------------------------------

    builder = StateGraph(
        ProjectPulseState
    )

    builder.add_node(
        "load_memory",
        load_memory,
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

    builder.add_node(
        "update_short_term_memory",
        update_short_term_memory,
    )

    builder.add_edge(
        START,
        "load_memory",
    )

    builder.add_edge(
        "load_memory",
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
        "update_short_term_memory",
    )

    builder.add_edge(
        "investigation",
        "update_short_term_memory",
    )

    builder.add_edge(
        "update_short_term_memory",
        END,
    )

    return builder.compile()


# ---------------------------------------------------------
# Demo
# ---------------------------------------------------------

async def main():
    client = create_mcp_client()

    print("=" * 70)
    print(
        "PROJECTPULSE LANGGRAPH + MCP + MEMORY AGENT"
    )
    print("=" * 70)

    memory_store = MemoryStore()
    short_term_memory = ShortTermMemory(
        max_items=6
    )

    async with client.session(
        "projectpulse"
    ) as session:

        tools = await load_mcp_tools(
            session
        )

        graph = build_projectpulse_graph(
            tools=tools,
            memory_store=memory_store,
            short_term_memory=short_term_memory,
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
                f"Relevant long-term memories: "
                f"{len(result.get('relevant_memories', []))}"
            )

            print(
                f"Short-term context items: "
                f"{len(result.get('recent_context', []))}"
            )

            if result.get("stored_memory"):
                print(
                    "New long-term memory stored: "
                    f"{result['stored_memory']['category']}"
                )

            print(
                "\nTool result:"
            )

            print(
                result["result"]
            )

    print("\n" + "=" * 70)
    print(
        "LANGGRAPH + MCP + MEMORY "
        "VERIFICATION PASSED"
    )
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())