from typing import Any

from langsmith import traceable

from projectpulse.planner import (
    QueryPlan,
    create_plan,
)
from projectpulse.retriever import retrieve


# ---------------------------------------------------------
# Observability helpers
# ---------------------------------------------------------


@traceable(
    name="create_investigation_plan",
    metadata={
        "component": "agentic_retriever",
        "stage": "planning",
    },
)
def _create_investigation_plan(
    query: str,
) -> QueryPlan:
    """
    Create the planner output for an agentic investigation.

    This wrapper exists so the planning stage appears
    explicitly in LangSmith without changing planner logic.
    """

    return create_plan(query)


@traceable(
    name="semantic_subquery_retrieval",
    run_type="retriever",
    metadata={
        "component": "agentic_retriever",
        "stage": "retrieval",
    },
)
def _retrieve_sub_query(
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    """
    Execute semantic retrieval for one planner-generated
    sub-query.

    Each invocation becomes an individual LangSmith span,
    allowing us to inspect the cost and latency of the
    multi-query retrieval strategy.
    """

    return retrieve(
        query=query,
        top_k=top_k,
    )


# ---------------------------------------------------------
# Agentic evidence collection
# ---------------------------------------------------------


@traceable(
    name="collect_evidence",
    metadata={
        "component": "agentic_retriever",
        "stage": "evidence_aggregation",
    },
)
def collect_evidence(
    plan: QueryPlan,
    top_k_per_query: int = 3,
) -> list[dict[str, Any]]:
    """
    Run semantic retrieval for every sub-query generated
    by the planner and combine the evidence.

    Duplicate chunks are merged while keeping track of
    every sub-query that discovered the chunk.
    """

    if top_k_per_query <= 0:
        raise ValueError(
            "top_k_per_query must be greater than 0."
        )

    evidence_by_chunk = {}

    for sub_query in plan.sub_queries:

        results = _retrieve_sub_query(
            query=sub_query,
            top_k=top_k_per_query,
        )

        for result in results:

            chunk_id = result["chunk_id"]

            if chunk_id not in evidence_by_chunk:

                evidence_by_chunk[chunk_id] = {
                    "chunk_id": chunk_id,
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "best_distance": result["distance"],
                    "best_rank": result["rank"],
                    "matched_sub_queries": [
                        sub_query
                    ],
                }

            else:

                evidence = evidence_by_chunk[
                    chunk_id
                ]

                if (
                    sub_query
                    not in evidence[
                        "matched_sub_queries"
                    ]
                ):
                    evidence[
                        "matched_sub_queries"
                    ].append(
                        sub_query
                    )

                if (
                    result["distance"]
                    < evidence["best_distance"]
                ):
                    evidence[
                        "best_distance"
                    ] = result["distance"]

                    evidence[
                        "best_rank"
                    ] = result["rank"]

    evidence_list = list(
        evidence_by_chunk.values()
    )

    for evidence in evidence_list:

        evidence["match_count"] = len(
            evidence[
                "matched_sub_queries"
            ]
        )

    evidence_list.sort(
        key=lambda item: (
            -item["match_count"],
            item["best_distance"],
        )
    )

    return evidence_list


# ---------------------------------------------------------
# Complete investigation pipeline
# ---------------------------------------------------------


@traceable(
    name="agentic_investigation",
    metadata={
        "component": "mcp_server",
        "pipeline": "agentic_retrieval",
    },
)
def investigate(
    query: str,
    top_k_per_query: int = 3,
) -> tuple[
    QueryPlan,
    list[dict[str, Any]],
]:
    """
    Create an investigation plan and execute semantic
    retrieval for every planned query.

    LangSmith tracing exposes the planning, retrieval,
    and evidence-aggregation stages of this pipeline.
    """

    plan = _create_investigation_plan(
        query
    )

    evidence = collect_evidence(
        plan=plan,
        top_k_per_query=top_k_per_query,
    )

    return plan, evidence


# ---------------------------------------------------------
# Console output
# ---------------------------------------------------------


def print_investigation(
    plan: QueryPlan,
    evidence: list[dict[str, Any]],
):
    """
    Pretty-print the investigation plan and aggregated
    evidence.
    """

    print("\n" + "=" * 70)
    print(
        "PROJECTPULSE AGENTIC RETRIEVAL"
    )
    print("=" * 70)

    print(
        f"\nOriginal query: "
        f"{plan.original_query}"
    )

    print(
        f"Detected intent: "
        f"{plan.intent}"
    )

    print(
        "\nInvestigation queries:"
    )

    for index, sub_query in enumerate(
        plan.sub_queries,
        start=1,
    ):
        print(
            f"{index}. {sub_query}"
        )

    print(
        f"\nUnique evidence chunks: "
        f"{len(evidence)}"
    )

    if not evidence:
        print(
            "\nNo evidence found."
        )
        return

    print(
        "\n" + "=" * 70
    )

    print(
        "AGGREGATED EVIDENCE"
    )

    print(
        "=" * 70
    )

    for index, item in enumerate(
        evidence,
        start=1,
    ):

        metadata = item["metadata"]

        print(
            f"\nEvidence #{index}"
        )

        print(
            f"Chunk ID: "
            f"{item['chunk_id']}"
        )

        print(
            f"Matched queries: "
            f"{item['match_count']}"
        )

        print(
            f"Best distance: "
            f"{item['best_distance']:.4f}"
        )

        print(
            f"Type: "
            f"{metadata.get('type', '')}"
        )

        print(
            f"Title: "
            f"{metadata.get('title', '')}"
        )

        print(
            f"URL: "
            f"{metadata.get('url', '')}"
        )

        print(
            "\nFound by:"
        )

        for sub_query in item[
            "matched_sub_queries"
        ]:
            print(
                f"- {sub_query}"
            )

        print(
            "\nContent:"
        )

        print(
            item["content"]
        )

        print(
            "-" * 70
        )


# ---------------------------------------------------------
# Manual execution
# ---------------------------------------------------------


def main():

    query = input(
        "Ask ProjectPulse: "
    )

    plan, evidence = investigate(
        query=query,
        top_k_per_query=3,
    )

    print_investigation(
        plan=plan,
        evidence=evidence,
    )


if __name__ == "__main__":
    main()