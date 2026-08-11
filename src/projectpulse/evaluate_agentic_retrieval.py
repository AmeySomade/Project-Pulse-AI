from statistics import mean
from time import perf_counter

from projectpulse.agentic_retriever import investigate
from projectpulse.retriever import retrieve


TEST_QUERIES = [
    "What changed in ProjectPulse recently?",
    "What blockers or issues are affecting ProjectPulse?",
    "What is the current status of ProjectPulse?",
]


def mean_distance(results):
    """
    Calculate the average retrieval distance.
    Lower distance means greater semantic similarity.
    """

    if not results:
        return None

    return mean(
        item["distance"]
        for item in results
    )


def mean_agentic_distance(evidence):
    """
    Calculate the average best distance
    across aggregated agentic evidence.
    """

    if not evidence:
        return None

    return mean(
        item["best_distance"]
        for item in evidence
    )


def evaluate_query(
    query: str,
    top_k: int = 3,
):
    """
    Compare normal single-query retrieval
    against planner-driven multi-query retrieval.
    """

    # -------------------------
    # Baseline retrieval
    # -------------------------

    baseline_start = perf_counter()

    baseline_results = retrieve(
        query=query,
        top_k=top_k,
    )

    baseline_end = perf_counter()

    baseline_latency_ms = (
        baseline_end - baseline_start
    ) * 1000

    # -------------------------
    # Agentic retrieval
    # -------------------------

    agentic_start = perf_counter()

    plan, agentic_evidence = investigate(
        query=query,
        top_k_per_query=top_k,
    )

    agentic_end = perf_counter()

    agentic_latency_ms = (
        agentic_end - agentic_start
    ) * 1000

    # -------------------------
    # Evidence comparison
    # -------------------------

    baseline_ids = {
        item["chunk_id"]
        for item in baseline_results
    }

    agentic_ids = {
        item["chunk_id"]
        for item in agentic_evidence
    }

    new_agentic_ids = (
        agentic_ids - baseline_ids
    )

    shared_ids = (
        baseline_ids & agentic_ids
    )

    baseline_unique = len(
        baseline_ids
    )

    agentic_unique = len(
        agentic_ids
    )

    additional_chunks = (
        agentic_unique
        - baseline_unique
    )

    if baseline_unique > 0:
        evidence_expansion_percent = (
            additional_chunks
            / baseline_unique
        ) * 100
    else:
        evidence_expansion_percent = 0.0

    return {
        "query": query,
        "intent": plan.intent,
        "sub_query_count": len(
            plan.sub_queries
        ),

        "baseline_retrieval_calls": 1,
        "agentic_retrieval_calls": len(
            plan.sub_queries
        ),

        "baseline_unique_chunks": (
            baseline_unique
        ),

        "agentic_unique_chunks": (
            agentic_unique
        ),

        "additional_unique_chunks": (
            additional_chunks
        ),

        "shared_chunks": len(
            shared_ids
        ),

        "new_agentic_chunk_ids": sorted(
            new_agentic_ids
        ),

        "evidence_expansion_percent": (
            evidence_expansion_percent
        ),

        "baseline_mean_distance": (
            mean_distance(
                baseline_results
            )
        ),

        "agentic_mean_best_distance": (
            mean_agentic_distance(
                agentic_evidence
            )
        ),

        "baseline_latency_ms": (
            baseline_latency_ms
        ),

        "agentic_latency_ms": (
            agentic_latency_ms
        ),
    }


def format_distance(value):
    if value is None:
        return "N/A"

    return f"{value:.4f}"


def print_result(result):

    print("\n" + "=" * 70)

    print(
        f"QUERY: {result['query']}"
    )

    print("=" * 70)

    print(
        f"Intent: "
        f"{result['intent']}"
    )

    print(
        f"Planner sub-queries: "
        f"{result['sub_query_count']}"
    )

    print("\n--- RETRIEVAL CALLS ---")

    print(
        f"Baseline calls: "
        f"{result['baseline_retrieval_calls']}"
    )

    print(
        f"Agentic calls: "
        f"{result['agentic_retrieval_calls']}"
    )

    print("\n--- EVIDENCE COVERAGE ---")

    print(
        f"Baseline unique chunks: "
        f"{result['baseline_unique_chunks']}"
    )

    print(
        f"Agentic unique chunks: "
        f"{result['agentic_unique_chunks']}"
    )

    print(
        f"Additional unique chunks: "
        f"{result['additional_unique_chunks']}"
    )

    print(
        f"Shared chunks: "
        f"{result['shared_chunks']}"
    )

    print(
        f"Evidence expansion: "
        f"{result['evidence_expansion_percent']:.2f}%"
    )

    print(
        "New chunks found only by agentic retrieval: "
        f"{result['new_agentic_chunk_ids']}"
    )

    print("\n--- SEMANTIC DISTANCE ---")

    print(
        "Baseline mean distance: "
        f"{format_distance(result['baseline_mean_distance'])}"
    )

    print(
        "Agentic mean best distance: "
        f"{format_distance(result['agentic_mean_best_distance'])}"
    )

    print("\n--- LATENCY ---")

    print(
        f"Baseline latency: "
        f"{result['baseline_latency_ms']:.2f} ms"
    )

    print(
        f"Agentic latency: "
        f"{result['agentic_latency_ms']:.2f} ms"
    )


def print_summary(results):

    print("\n" + "#" * 70)
    print("OVERALL AGENTIC RETRIEVAL EVALUATION")
    print("#" * 70)

    avg_baseline_latency = mean(
        result["baseline_latency_ms"]
        for result in results
    )

    avg_agentic_latency = mean(
        result["agentic_latency_ms"]
        for result in results
    )

    avg_baseline_chunks = mean(
        result["baseline_unique_chunks"]
        for result in results
    )

    avg_agentic_chunks = mean(
        result["agentic_unique_chunks"]
        for result in results
    )

    avg_expansion = mean(
        result[
            "evidence_expansion_percent"
        ]
        for result in results
    )

    total_baseline_calls = sum(
        result[
            "baseline_retrieval_calls"
        ]
        for result in results
    )

    total_agentic_calls = sum(
        result[
            "agentic_retrieval_calls"
        ]
        for result in results
    )

    print(
        f"\nQueries evaluated: "
        f"{len(results)}"
    )

    print(
        f"Average baseline chunks: "
        f"{avg_baseline_chunks:.2f}"
    )

    print(
        f"Average agentic chunks: "
        f"{avg_agentic_chunks:.2f}"
    )

    print(
        f"Average evidence expansion: "
        f"{avg_expansion:.2f}%"
    )

    print(
        f"\nTotal baseline retrieval calls: "
        f"{total_baseline_calls}"
    )

    print(
        f"Total agentic retrieval calls: "
        f"{total_agentic_calls}"
    )

    print(
        f"\nAverage baseline latency: "
        f"{avg_baseline_latency:.2f} ms"
    )

    print(
        f"Average agentic latency: "
        f"{avg_agentic_latency:.2f} ms"
    )

    if avg_baseline_latency > 0:

        latency_multiplier = (
            avg_agentic_latency
            / avg_baseline_latency
        )

        print(
            f"Agentic latency multiplier: "
            f"{latency_multiplier:.2f}x"
        )

    print("\nInterpretation:")

    if avg_agentic_chunks > avg_baseline_chunks:

        print(
            "Agentic retrieval increased "
            "evidence coverage."
        )

    else:

        print(
            "Agentic retrieval did not increase "
            "unique evidence coverage on the "
            "current corpus."
        )

    print(
        "Multi-query retrieval requires more "
        "retrieval calls and therefore has a "
        "latency/cost trade-off."
    )

    print(
        "A larger and more diverse indexed "
        "corpus is required for a stronger "
        "coverage evaluation."
    )

    print("#" * 70)


def main():

    print(
        "Warming up embedding model..."
    )

    # Prevent model-loading time from unfairly
    # affecting the baseline measurement.
    retrieve(
        query="ProjectPulse",
        top_k=1,
    )

    results = []

    for query in TEST_QUERIES:

        result = evaluate_query(
            query=query,
            top_k=3,
        )

        results.append(
            result
        )

        print_result(
            result
        )

    print_summary(
        results
    )


if __name__ == "__main__":
    main()