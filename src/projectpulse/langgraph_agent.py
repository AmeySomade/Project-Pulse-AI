import asyncio
import json
from dataclasses import asdict
from typing import Any, Literal, TypedDict

from langchain_core.runnables import RunnableConfig
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
    memory stores only a bounded representation.
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

    LangGraph automatically traces graph nodes.

    RunnableConfig is passed directly into MCP-discovered
    LangChain tools so their runs remain connected to the
    LangGraph parent trace, including on Python 3.10.
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

    # -----------------------------------------------------
    # Memory dependencies
    # -----------------------------------------------------

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
    # Node 1: Load memory
    # -----------------------------------------------------

    def load_memory(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Load relevant persistent memories before planning.

        The current user query is always stored temporarily.

        Only information matching the selective-memory policy
        is persisted into long-term memory.
        """

        query = state["query"].strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        # Search OLD long-term memories first.
        relevant_records = long_term_memory.search(
            query,
            limit=memory_search_limit,
        )

        relevant_memories = [
            asdict(record)
            for record in relevant_records
        ]

        # Current user message enters short-term memory.
        conversation_memory.add(
            "user",
            query,
        )

        # Persist only important user information.
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
        Detect query intent and choose the appropriate
        MCP retrieval capability.
        """

        query = state["query"].strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        plan = create_plan(query)

        # General/focused questions only need direct
        # semantic retrieval.
        if plan.intent == "general":
            selected_tool = (
                "search_project_history"
            )

        # Complex project questions use the multi-query
        # investigation pipeline.
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
        Convert the selected MCP capability into the
        appropriate LangGraph branch.
        """

        if (
            state["selected_tool"]
            == "search_project_history"
        ):
            return "direct_search"

        return "investigation"

    # -----------------------------------------------------
    # Node 3A: Direct semantic retrieval
    # -----------------------------------------------------

    async def direct_search(
        state: ProjectPulseState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """
        Execute focused semantic retrieval through the real
        MCP-discovered LangChain tool.

        Passing config directly preserves LangSmith parent/
        child trace relationships.
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
            },
            config=config,
        )

        return {
            "result": result,
        }

    # -----------------------------------------------------
    # Node 3B: Multi-step investigation
    # -----------------------------------------------------

    async def investigation(
        state: ProjectPulseState,
        config: RunnableConfig,
    ) -> dict[str, Any]:
        """
        Execute the multi-query ProjectPulse investigation
        through the real MCP-discovered LangChain tool.

        Passing RunnableConfig directly allows the MCP tool
        run to nest under this LangGraph node in LangSmith.
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
            },
            config=config,
        )

        return {
            "result": result,
        }

    # -----------------------------------------------------
    # Node 4: Update short-term memory
    # -----------------------------------------------------

    def update_short_term_memory(
        state: ProjectPulseState,
    ) -> dict[str, Any]:
        """
        Store a bounded representation of the tool result
        in temporary conversation memory.
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
    # Assemble LangGraph
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
# Manual verification
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

            print("\nTool result:")

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