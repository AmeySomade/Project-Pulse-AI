from typing import Any

from mcp.server.fastmcp import FastMCP

from projectpulse.agentic_retriever import investigate
from projectpulse.retriever import retrieve


# ---------------------------------------------------------
# ProjectPulse MCP Server
# ---------------------------------------------------------

mcp = FastMCP(
    "ProjectPulse MCP Server"
)


# ---------------------------------------------------------
# Tool 1: Direct semantic retrieval
# ---------------------------------------------------------

@mcp.tool()
def search_project_history(
    query: str,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Search indexed ProjectPulse project history using
    semantic vector retrieval.

    Use this tool for focused questions where direct
    retrieval is sufficient.
    """

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError(
            "Query cannot be empty."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than 0."
        )

    results = retrieve(
        query=cleaned_query,
        top_k=top_k,
    )

    return {
        "query": cleaned_query,
        "result_count": len(results),
        "results": results,
    }


# ---------------------------------------------------------
# Tool 2: Multi-step project investigation
# ---------------------------------------------------------

@mcp.tool()
def investigate_project(
    query: str,
    top_k_per_query: int = 3,
) -> dict[str, Any]:
    """
    Investigate a ProjectPulse project question using
    the existing planner and multi-step semantic retrieval.

    Use this tool for questions about project changes,
    blockers, timelines, status, features, or pull requests
    that may require multiple retrieval queries.
    """

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError(
            "Query cannot be empty."
        )

    if top_k_per_query <= 0:
        raise ValueError(
            "top_k_per_query must be greater than 0."
        )

    plan, evidence = investigate(
        query=cleaned_query,
        top_k_per_query=top_k_per_query,
    )

    return {
        "query": cleaned_query,
        "plan": {
            "original_query": plan.original_query,
            "intent": plan.intent,
            "sub_queries": plan.sub_queries,
        },
        "evidence_count": len(evidence),
        "evidence": evidence,
    }


# ---------------------------------------------------------
# Server entry point
# ---------------------------------------------------------

def main():
    """
    Start ProjectPulse MCP server using stdio transport.
    """

    mcp.run(
        transport="stdio"
    )


if __name__ == "__main__":
    main()