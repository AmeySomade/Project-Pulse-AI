from projectpulse.agentic_retriever import (
    collect_evidence,
)
from projectpulse.planner import QueryPlan


def test_collect_evidence_deduplicates_chunks(monkeypatch):

    plan = QueryPlan(
        original_query="What changed?",
        intent="project_changes",
        sub_queries=[
            "What features were added?",
            "What bugs were reported?",
        ],
    )

    fake_results = {
        "What features were added?": [
            {
                "chunk_id": "chunk_1",
                "content": "Feature A was added.",
                "metadata": {
                    "type": "commit",
                    "title": "Add feature A",
                    "url": "https://example.com/1",
                },
                "rank": 1,
                "distance": 0.30,
            },
            {
                "chunk_id": "chunk_2",
                "content": "Documentation updated.",
                "metadata": {
                    "type": "commit",
                    "title": "Update docs",
                    "url": "https://example.com/2",
                },
                "rank": 2,
                "distance": 0.50,
            },
        ],

        "What bugs were reported?": [
            {
                "chunk_id": "chunk_1",
                "content": "Feature A was added.",
                "metadata": {
                    "type": "commit",
                    "title": "Add feature A",
                    "url": "https://example.com/1",
                },
                "rank": 2,
                "distance": 0.25,
            }
        ],
    }

    def fake_retrieve(query, top_k):
        return fake_results[query]

    monkeypatch.setattr(
        "projectpulse.agentic_retriever.retrieve",
        fake_retrieve,
    )

    evidence = collect_evidence(
        plan=plan,
        top_k_per_query=2,
    )

    assert len(evidence) == 2


def test_duplicate_chunk_tracks_all_queries(monkeypatch):

    plan = QueryPlan(
        original_query="What changed?",
        intent="project_changes",
        sub_queries=[
            "Query one",
            "Query two",
        ],
    )

    def fake_retrieve(query, top_k):

        if query == "Query one":
            distance = 0.40
        else:
            distance = 0.20

        return [
            {
                "chunk_id": "chunk_1",
                "content": "Shared evidence.",
                "metadata": {},
                "rank": 1,
                "distance": distance,
            }
        ]

    monkeypatch.setattr(
        "projectpulse.agentic_retriever.retrieve",
        fake_retrieve,
    )

    evidence = collect_evidence(
        plan=plan,
        top_k_per_query=1,
    )

    assert len(evidence) == 1

    item = evidence[0]

    assert item["match_count"] == 2

    assert item["matched_sub_queries"] == [
        "Query one",
        "Query two",
    ]

    assert item["best_distance"] == 0.20


def test_evidence_ranked_by_match_count(monkeypatch):

    plan = QueryPlan(
        original_query="What changed?",
        intent="project_changes",
        sub_queries=[
            "Query one",
            "Query two",
        ],
    )

    fake_results = {
        "Query one": [
            {
                "chunk_id": "shared_chunk",
                "content": "Shared evidence.",
                "metadata": {},
                "rank": 1,
                "distance": 0.40,
            },
            {
                "chunk_id": "single_chunk",
                "content": "Single-query evidence.",
                "metadata": {},
                "rank": 2,
                "distance": 0.10,
            },
        ],

        "Query two": [
            {
                "chunk_id": "shared_chunk",
                "content": "Shared evidence.",
                "metadata": {},
                "rank": 1,
                "distance": 0.35,
            }
        ],
    }

    def fake_retrieve(query, top_k):
        return fake_results[query]

    monkeypatch.setattr(
        "projectpulse.agentic_retriever.retrieve",
        fake_retrieve,
    )

    evidence = collect_evidence(
        plan=plan,
        top_k_per_query=2,
    )

    assert evidence[0]["chunk_id"] == "shared_chunk"
    assert evidence[0]["match_count"] == 2

    assert evidence[1]["chunk_id"] == "single_chunk"
    assert evidence[1]["match_count"] == 1


def test_invalid_top_k_raises_error():

    plan = QueryPlan(
        original_query="What changed?",
        intent="project_changes",
        sub_queries=["Query one"],
    )

    try:
        collect_evidence(
            plan=plan,
            top_k_per_query=0,
        )

        assert False, "Expected ValueError"

    except ValueError as error:

        assert (
            str(error)
            == "top_k_per_query must be greater than 0."
        )