from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


MemoryCategory = Literal[
    "decision",
    "blocker",
    "preference",
    "status",
]


# ---------------------------------------------------------
# Long-term memory record
# ---------------------------------------------------------

@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    content: str
    category: MemoryCategory
    created_at: str
    source_query: str = ""
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------
# Short-term conversation memory
# ---------------------------------------------------------

class ShortTermMemory:
    """
    Keep only the most recent conversation turns.

    This memory is intentionally temporary and exists only
    for the lifetime of the running Python process.
    """

    def __init__(self, max_items: int = 6):
        if max_items <= 0:
            raise ValueError("max_items must be greater than zero.")

        self.max_items = max_items
        self._items: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        role = role.strip()
        content = content.strip()

        if not role:
            raise ValueError("role cannot be empty.")

        if not content:
            raise ValueError("content cannot be empty.")

        self._items.append(
            {
                "role": role,
                "content": content,
            }
        )

        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items:]

    def get_context(self) -> list[dict[str, str]]:
        """
        Return a copy so callers cannot mutate internal state.
        """
        return [item.copy() for item in self._items]

    def clear(self) -> None:
        self._items.clear()


# ---------------------------------------------------------
# Selective memory policy
# ---------------------------------------------------------

MEMORY_SIGNALS: dict[MemoryCategory, tuple[str, ...]] = {
    "decision": (
        "we decided",
        "decided to",
        "decision is",
        "we will use",
        "we'll use",
        "going with",
        "we chose",
        "chosen",
    ),
    "blocker": (
        "blocked",
        "blocker",
        "blocking",
        "bug",
        "error",
        "failing",
        "fails",
        "failure",
    ),
    "preference": (
        "i prefer",
        "we prefer",
        "from now on",
        "always use",
        "do not use",
        "don't use",
    ),
    "status": (
        "completed",
        "finished",
        "implemented",
        "shipped",
        "tests passed",
        "verification passed",
    ),
}


def classify_memory(
    text: str,
) -> MemoryCategory | None:
    """
    Decide whether a piece of text is important enough for
    long-term memory.

    Returns the detected category or None when the text
    should not be stored.
    """

    normalized = " ".join(text.lower().split())

    if not normalized:
        return None

    # Questions normally request information rather than
    # introduce new long-term project knowledge.
    if normalized.endswith("?"):
        return None

    for category, signals in MEMORY_SIGNALS.items():
        if any(signal in normalized for signal in signals):
            return category

    return None


# ---------------------------------------------------------
# Persistent long-term memory
# ---------------------------------------------------------

class MemoryStore:
    """
    JSON-backed persistent memory store.

    The implementation is intentionally simple for the MVP:
    easy to inspect, test, version locally, and later replace
    with a vector/database-backed memory layer.
    """

    def __init__(
        self,
        path: str | Path = "data/projectpulse_memory.json",
    ):
        self.path = Path(path)

    def _load(self) -> list[MemoryRecord]:
        if not self.path.exists():
            return []

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            raw_records = json.load(file)

        return [
            MemoryRecord(**record)
            for record in raw_records
        ]

    def _save(
        self,
        records: list[MemoryRecord],
    ) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                [
                    asdict(record)
                    for record in records
                ],
                file,
                indent=2,
                ensure_ascii=False,
            )

        temp_path.replace(self.path)

    @staticmethod
    def _make_memory_id(
        content: str,
        category: MemoryCategory,
    ) -> str:
        fingerprint = (
            f"{category}|{content.strip().lower()}"
        )

        digest = hashlib.sha256(
            fingerprint.encode("utf-8")
        ).hexdigest()[:16]

        return f"mem_{digest}"

    def add(
        self,
        content: str,
        category: MemoryCategory,
        source_query: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        content = " ".join(content.split())

        if not content:
            raise ValueError(
                "Memory content cannot be empty."
            )

        memory_id = self._make_memory_id(
            content,
            category,
        )

        records = self._load()

        # Deduplicate identical semantic memory entries
        # using the deterministic fingerprint.
        for existing in records:
            if existing.memory_id == memory_id:
                return existing

        record = MemoryRecord(
            memory_id=memory_id,
            content=content,
            category=category,
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
            source_query=source_query.strip(),
            metadata=metadata,
        )

        records.append(record)
        self._save(records)

        return record

    def list_memories(
        self,
        category: MemoryCategory | None = None,
    ) -> list[MemoryRecord]:
        records = self._load()

        if category is None:
            return records

        return [
            record
            for record in records
            if record.category == category
        ]

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """
        Lightweight keyword retrieval for the MVP.

        Vector-based semantic memory retrieval can replace
        this implementation later without changing callers.
        """

        if limit <= 0:
            return []

        query_tokens = set(
            query.lower().split()
        )

        if not query_tokens:
            return []

        scored: list[
            tuple[int, MemoryRecord]
        ] = []

        for record in self._load():
            memory_tokens = set(
                record.content.lower().split()
            )

            overlap = len(
                query_tokens & memory_tokens
            )

            if overlap > 0:
                scored.append(
                    (
                        overlap,
                        record,
                    )
                )

        scored.sort(
            key=lambda item: (
                item[0],
                item[1].created_at,
            ),
            reverse=True,
        )

        return [
            record
            for _, record in scored[:limit]
        ]


# ---------------------------------------------------------
# Selective persistence helper
# ---------------------------------------------------------

def remember_if_important(
    store: MemoryStore,
    text: str,
    source_query: str = "",
    metadata: dict[str, Any] | None = None,
) -> MemoryRecord | None:
    """
    Persist text only when the selective-memory policy
    identifies useful long-term project information.
    """

    category = classify_memory(text)

    if category is None:
        return None

    return store.add(
        content=text,
        category=category,
        source_query=source_query,
        metadata=metadata,
    )