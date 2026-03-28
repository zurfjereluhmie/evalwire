"""task.py — RAG pipeline experiment task for evalwire.

The task isolates the ``retrieve`` node of the RAG graph using
``evalwire.langgraph.build_subgraph``, invokes it with the user query, and
returns the list of retrieved document titles.

Expected dataset example shape (produced by DatasetUploader):
    {
        "input":  {"user_query": "..."},
        "output": {"expected_output": ["Title A", "Title B", ...]},
    }

The ``task`` callable must accept one dict argument and return the system
output — here a plain list of retrieved titles.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow ``from agent.graph import ...`` when running from the demo/ root.
_demo_root = Path(__file__).resolve().parents[2]
if str(_demo_root) not in sys.path:
    sys.path.insert(0, str(_demo_root))

from agent.graph import RAGState, retrieve  # noqa: E402

from evalwire.langgraph import build_subgraph  # noqa: E402

# Build a single-node subgraph that only runs ``retrieve``.
_subgraph = build_subgraph(
    nodes=[("retrieve", retrieve)],
    state_cls=RAGState,
    name="retrieve_only",
)


def task(example: dict) -> list[str]:
    """Run the retrieve node for a single dataset example.

    Parameters
    ----------
    example:
        A dict with at least an ``"input"`` key containing ``"user_query"``.

    Returns
    -------
    list[str]
        The titles of the documents retrieved for the query.
    """
    query: str = example["input"]["user_query"]

    from langchain_core.messages import HumanMessage

    state = RAGState(messages=[HumanMessage(content=query)])
    result = asyncio.run(_subgraph.ainvoke(state))
    return result["retrieved_titles"]
