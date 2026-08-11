from projectpulse.planner import (
    create_plan,
    detect_intent,
)


def test_detect_project_changes_intent():

    query = (
        "What changed in ProjectPulse recently?"
    )

    intent = detect_intent(
        query
    )

    assert intent == "project_changes"


def test_detect_blockers_intent():

    query = (
        "What blockers are currently "
        "affecting the project?"
    )

    intent = detect_intent(
        query
    )

    assert intent == "blockers"


def test_detect_timeline_intent():

    query = (
        "Were any deadlines delayed?"
    )

    intent = detect_intent(
        query
    )

    assert intent == "timeline"


def test_detect_pull_request_intent():

    query = (
        "Which PR was recently merged?"
    )

    intent = detect_intent(
        query
    )

    assert intent == "pull_requests"


def test_projectpulse_name_does_not_trigger_pr_intent():

    query = (
        "What is the current status "
        "of ProjectPulse?"
    )

    intent = detect_intent(
        query
    )

    assert intent == "status"


def test_project_changes_creates_multiple_sub_queries():

    query = (
        "What changed in ProjectPulse recently?"
    )

    plan = create_plan(
        query
    )

    assert plan.original_query == query
    assert plan.intent == "project_changes"

    assert len(
        plan.sub_queries
    ) == 5

    assert (
        "What features or functionality "
        "were recently added?"
        in plan.sub_queries
    )

    assert (
        "What bugs, issues, or blockers "
        "were recently reported?"
        in plan.sub_queries
    )


def test_general_query_is_not_over_decomposed():

    query = (
        "Explain semantic retrieval"
    )

    plan = create_plan(
        query
    )

    assert plan.intent == "general"

    assert plan.sub_queries == [
        query
    ]


def test_empty_query_raises_error():

    try:

        create_plan(
            "   "
        )

        assert False, (
            "Expected ValueError"
        )

    except ValueError as error:

        assert (
            str(error)
            == "Query cannot be empty."
        )