import re
from dataclasses import dataclass


@dataclass
class QueryPlan:
    """
    Represents the investigation plan generated
    for a user's project question.
    """

    original_query: str
    intent: str
    sub_queries: list[str]


def contains_word(
    query: str,
    word: str,
) -> bool:
    """
    Check for a complete word instead of
    matching a substring inside another word.
    """

    pattern = rf"\b{re.escape(word)}\b"

    return bool(
        re.search(
            pattern,
            query,
            flags=re.IGNORECASE,
        )
    )


def detect_intent(query: str) -> str:
    """
    Detect the main investigation intent.

    Specific intents are checked before broad
    change/status intents to avoid conflicts.
    """

    query_lower = query.lower()

    # -------------------------
    # Pull requests
    # -------------------------

    if any(
        phrase in query_lower
        for phrase in [
            "pull request",
            "pull requests",
            "merged",
        ]
    ) or contains_word(
        query,
        "pr",
    ) or contains_word(
        query,
        "prs",
    ):
        return "pull_requests"

    # -------------------------
    # Blockers / issues
    # -------------------------

    if any(
        word in query_lower
        for word in [
            "blocker",
            "blockers",
            "blocked",
            "problem",
            "problems",
            "issue",
            "issues",
        ]
    ):
        return "blockers"

    # -------------------------
    # Timeline
    # -------------------------

    if any(
        word in query_lower
        for word in [
            "delay",
            "delayed",
            "deadline",
            "deadlines",
            "late",
        ]
    ):
        return "timeline"

    # -------------------------
    # Feature
    # -------------------------

    if any(
        word in query_lower
        for word in [
            "feature",
            "features",
            "implementation",
        ]
    ):
        return "feature"

    # -------------------------
    # Status
    # -------------------------

    if any(
        phrase in query_lower
        for phrase in [
            "status",
            "progress",
            "current state",
        ]
    ):
        return "status"

    # -------------------------
    # Broad project changes
    # -------------------------

    if any(
        phrase in query_lower
        for phrase in [
            "changed",
            "changes",
            "what happened",
            "recently",
            "this week",
        ]
    ):
        return "project_changes"

    return "general"


def build_sub_queries(
    query: str,
    intent: str,
) -> list[str]:
    """
    Convert an identified intent into focused
    retrieval questions.
    """

    if intent == "project_changes":
        return [
            "What features or functionality were recently added?",
            "What files or components were recently changed?",
            "What bugs, issues, or blockers were recently reported?",
            "Were any project plans, deadlines, or priorities changed?",
            "What is the latest overall project status?",
        ]

    if intent == "blockers":
        return [
            "What blockers or problems are currently reported?",
            "What GitHub issues describe failures or unresolved work?",
            "What recent changes may be related to these blockers?",
            "Is there evidence that any blocker has been resolved?",
        ]

    if intent == "timeline":
        return [
            "What deadlines or milestones are documented?",
            "Were any deadlines or milestones recently changed?",
            "What blockers or unfinished work could affect the timeline?",
            "What recent project progress is relevant to the schedule?",
        ]

    if intent == "pull_requests":
        return [
            "Which pull requests were recently created or updated?",
            "Which pull requests were recently merged?",
            "What features or fixes were introduced by recent pull requests?",
            "Are any pull requests still unresolved or blocked?",
        ]

    if intent == "feature":
        return [
            f"What project documents mention this request: {query}",
            f"What code changes are related to this request: {query}",
            f"What issues or pull requests are related to this request: {query}",
            f"What is the current status of this request: {query}",
        ]

    if intent == "status":
        return [
            "What work has recently been completed?",
            "What work is currently in progress?",
            "What blockers or unresolved issues remain?",
            "What are the next documented project tasks?",
        ]

    return [query]


def create_plan(query: str) -> QueryPlan:
    """
    Create an investigation plan for a user's query.
    """

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError(
            "Query cannot be empty."
        )

    intent = detect_intent(
        cleaned_query
    )

    sub_queries = build_sub_queries(
        query=cleaned_query,
        intent=intent,
    )

    return QueryPlan(
        original_query=cleaned_query,
        intent=intent,
        sub_queries=sub_queries,
    )


def print_plan(
    plan: QueryPlan,
):
    """
    Pretty-print a generated investigation plan.
    """

    print("\n" + "=" * 70)

    print(
        "PROJECTPULSE INVESTIGATION PLAN"
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

    print("\nSub-queries:")

    for index, sub_query in enumerate(
        plan.sub_queries,
        start=1,
    ):
        print(
            f"{index}. {sub_query}"
        )

    print("=" * 70)


def main():

    query = input(
        "Ask ProjectPulse: "
    )

    plan = create_plan(
        query
    )

    print_plan(
        plan
    )


if __name__ == "__main__":
    main()