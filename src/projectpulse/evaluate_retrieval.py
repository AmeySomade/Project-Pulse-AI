from projectpulse.retriever import retrieve


EVALUATION_CASES = [
    {
        "query": "What work was done on GitHub integration?",
        "expected_title": (
            "feat: add authenticated GitHub repository integration"
        ),
    },
    {
        "query": "How was the ProjectPulse architecture defined?",
        "expected_title": (
            "docs: define ProjectPulse architecture and MVP scope"
        ),
    },
    {
        "query": "What is the MVP scope of ProjectPulse?",
        "expected_title": (
            "docs: define ProjectPulse architecture and MVP scope"
        ),
    },
    {
        "query": "Was authenticated repository access added?",
        "expected_title": (
            "feat: add authenticated GitHub repository integration"
        ),
    },
]


def evaluate():
    total_queries = len(EVALUATION_CASES)

    top1_correct = 0
    reciprocal_rank_sum = 0.0

    print("=" * 75)
    print("PROJECTPULSE RETRIEVAL BASELINE")
    print("=" * 75)

    for number, case in enumerate(
        EVALUATION_CASES,
        start=1,
    ):
        query = case["query"]
        expected_title = case["expected_title"]

        results = retrieve(
            query=query,
            top_k=2,
        )

        found_rank = None

        for result in results:
            title = result["metadata"].get(
                "title",
                "",
            )

            if title == expected_title:
                found_rank = result["rank"]
                break

        if found_rank == 1:
            top1_correct += 1

        if found_rank is not None:
            reciprocal_rank_sum += 1 / found_rank

        retrieved_title = (
            results[0]["metadata"].get("title", "")
            if results
            else "NO RESULT"
        )

        top_distance = (
            results[0]["distance"]
            if results
            else None
        )

        print(f"\nQuery {number}: {query}")

        print(
            f"Expected: {expected_title}"
        )

        print(
            f"Top result: {retrieved_title}"
        )

        if top_distance is not None:
            print(
                f"Top distance: {top_distance:.4f}"
            )

        print(
            f"Expected document rank: "
            f"{found_rank if found_rank else 'NOT FOUND'}"
        )

        if found_rank == 1:
            print("Result: PASS")
        else:
            print("Result: FAIL")

    hit_at_1 = top1_correct / total_queries

    mrr = (
        reciprocal_rank_sum
        / total_queries
    )

    print("\n" + "=" * 75)
    print("BASELINE METRICS")
    print("=" * 75)

    print(
        f"Queries evaluated: {total_queries}"
    )

    print(
        f"Correct at Rank 1: "
        f"{top1_correct}/{total_queries}"
    )

    print(
        f"Hit@1: {hit_at_1:.3f}"
    )

    print(
        f"MRR: {mrr:.3f}"
    )


if __name__ == "__main__":
    evaluate()