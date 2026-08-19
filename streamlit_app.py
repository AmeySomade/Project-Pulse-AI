from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from projectpulse.memory import MemoryStore, ShortTermMemory
from projectpulse.ui_service import (
    extract_evidence,
    extract_plan,
    run_projectpulse_query,
    summarize_graph_result,
)


APP_TITLE = "ProjectPulse AI"

SAMPLE_QUERIES = (
    "What work was done on GitHub integration?",
    "What changed in ProjectPulse and what is the current project status?",
    "Which architecture decisions are documented?",
    "What are the current blockers?",
)


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state() -> None:
    """Create Streamlit session state used by the chat experience."""

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "short_term_memory" not in st.session_state:
        st.session_state.short_term_memory = ShortTermMemory(
            max_items=6
        )


def format_number(value: Any, digits: int = 4) -> str:
    """Format optional numeric evidence metadata for display."""

    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"

    return "—"


def render_evidence_item(
    item: dict[str, Any],
    index: int,
) -> None:
    """Render one retrieved GitHub evidence item."""

    metadata = item.get("metadata", {})

    if not isinstance(metadata, dict):
        metadata = {}

    title = (
        metadata.get("title")
        or item.get("chunk_id")
        or f"Evidence {index}"
    )

    distance = item.get(
        "best_distance",
        item.get("distance"),
    )

    match_count = item.get("match_count")

    with st.expander(
        f"Evidence {index} · {title}",
        expanded=index == 1,
    ):
        detail_columns = st.columns(3)

        detail_columns[0].metric(
            "Source type",
            metadata.get("type") or "unknown",
        )

        detail_columns[1].metric(
            "Semantic distance",
            format_number(distance),
        )

        detail_columns[2].metric(
            "Query matches",
            match_count if match_count is not None else "—",
        )

        matched_queries = item.get(
            "matched_sub_queries",
            [],
        )

        if isinstance(matched_queries, list) and matched_queries:
            st.caption("Matched investigation queries")
            st.markdown(
                "\n".join(
                    f"- {query}"
                    for query in matched_queries
                )
            )

        st.markdown(item.get("content") or "No content returned.")

        source_url = metadata.get("url")

        if isinstance(source_url, str) and source_url:
            st.link_button(
                "Open GitHub source",
                source_url,
            )


def render_execution_details(
    result: dict[str, Any],
) -> None:
    """Render routing, planning, and memory state for an assistant turn."""

    evidence = extract_evidence(result)
    plan = extract_plan(result)

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Intent",
        result.get("intent") or "unknown",
    )

    metric_columns[1].metric(
        "MCP tool",
        result.get("selected_tool") or "unknown",
    )

    metric_columns[2].metric(
        "Evidence",
        len(evidence),
    )

    metric_columns[3].metric(
        "Relevant memories",
        len(result.get("relevant_memories", [])),
    )

    stored_memory = result.get("stored_memory")

    if isinstance(stored_memory, dict):
        st.success(
            "Saved as selective long-term memory: "
            f"{stored_memory.get('category', 'memory')}"
        )

    if plan:
        sub_queries = plan.get("sub_queries", [])

        with st.expander("Investigation plan"):
            st.write(
                f"Detected intent: {plan.get('intent', 'unknown')}"
            )

            if isinstance(sub_queries, list):
                st.markdown(
                    "\n".join(
                        f"{index}. {query}"
                        for index, query in enumerate(
                            sub_queries,
                            start=1,
                        )
                    )
                )

    st.markdown("#### Retrieved evidence")

    if evidence:
        for index, item in enumerate(evidence, start=1):
            render_evidence_item(item, index)
    else:
        st.info(
            "The current index did not return matching evidence. "
            "The development corpus still contains only two chunks."
        )

    with st.expander("Raw tool result"):
        st.json(result.get("result"))


def render_message(message: dict[str, Any]) -> None:
    """Render a saved chat message."""

    role = message["role"]
    avatar = "🔎" if role == "assistant" else None

    with st.chat_message(role, avatar=avatar):
        if message.get("error"):
            st.error(message["content"])
            return

        st.markdown(message["content"])

        result = message.get("result")

        if isinstance(result, dict):
            render_execution_details(result)


def run_query(
    prompt: str,
    top_k: int,
) -> dict[str, Any]:
    """Synchronously bridge Streamlit to the async ProjectPulse pipeline."""

    return asyncio.run(
        run_projectpulse_query(
            query=prompt,
            top_k=top_k,
            memory_store=MemoryStore(),
            short_term_memory=(
                st.session_state.short_term_memory
            ),
        )
    )


initialize_session_state()

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem;}
    [data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 0.8rem;
        padding: 0.8rem;
    }
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## ◉ ProjectPulse")
    st.caption("Agentic RAG over changing software-project history")

    top_k = st.slider(
        "Evidence per retrieval query",
        min_value=1,
        max_value=5,
        value=2,
        help=(
            "The number of Chroma evidence chunks requested by each "
            "semantic retrieval call."
        ),
    )

    try:
        persistent_memory_count = len(
            MemoryStore().list_memories()
        )
    except (OSError, ValueError):
        persistent_memory_count = 0

    st.metric(
        "Long-term memories",
        persistent_memory_count,
    )

    st.metric(
        "Session context items",
        len(
            st.session_state.short_term_memory.get_context()
        ),
    )

    if st.button(
        "Clear chat and session context",
        width="stretch",
    ):
        st.session_state.messages = []
        st.session_state.short_term_memory.clear()
        st.rerun()

    st.divider()
    st.caption(
        "Execution path: LangGraph → MCP stdio tool → "
        "ProjectPulse retrieval"
    )
    st.caption(
        "Persistent memories are intentionally not deleted when the "
        "visible chat is cleared."
    )

st.title(APP_TITLE)
st.markdown(
    "Investigate project history through the real LangGraph, MCP, "
    "retrieval, memory, and LangSmith-observable pipeline."
)

st.info(
    "This MVP returns grounded retrieval evidence and execution details. "
    "An LLM answer-synthesis layer has not been added, so the interface "
    "does not present generated conclusions as facts."
)

st.markdown("#### Try a project question")

sample_columns = st.columns(2)
selected_prompt = None

for index, sample_query in enumerate(SAMPLE_QUERIES):
    with sample_columns[index % 2]:
        if st.button(
            sample_query,
            key=f"sample_query_{index}",
            width="stretch",
        ):
            selected_prompt = sample_query

st.divider()

for saved_message in st.session_state.messages:
    render_message(saved_message)

typed_prompt = st.chat_input(
    "Ask about changes, status, blockers, features, or decisions..."
)

prompt = selected_prompt or typed_prompt

if prompt:
    user_message = {
        "role": "user",
        "content": prompt,
    }

    st.session_state.messages.append(user_message)
    render_message(user_message)

    try:
        with st.status(
            "Investigating project history...",
            expanded=True,
        ) as status:
            st.write("Loading memory and detecting query intent")
            st.write("Discovering and invoking the selected MCP tool")
            st.write("Retrieving and ranking project evidence")

            graph_result = run_query(
                prompt=prompt,
                top_k=top_k,
            )

            status.update(
                label="Investigation complete",
                state="complete",
                expanded=False,
            )

        assistant_message = {
            "role": "assistant",
            "content": summarize_graph_result(
                graph_result
            ),
            "result": graph_result,
        }

    except Exception as error:
        assistant_message = {
            "role": "assistant",
            "content": (
                "ProjectPulse could not complete this query. "
                f"{type(error).__name__}: {error}"
            ),
            "error": True,
        }

    st.session_state.messages.append(assistant_message)
    render_message(assistant_message)
