"""task.py — RAG pipeline experiment task for evalwire.

The task isolates the ``retrieve`` node of the RAG graph using
``evalwire.langgraph.build_subgraph``, invokes it with the user query, and
returns the list of retrieved document titles.

Phoenix passes each dataset row as a ``phoenix.experiments.types.Example``
dataclass — access fields via attributes (``example.input``, ``example.output``),
not by subscript.

The ``task`` callable must be an ``async def`` so that Phoenix's
``async_run_experiment`` can ``await`` it directly.  Using ``asyncio.run()``
inside a sync task would raise ``RuntimeError: asyncio.run() cannot be called
from a running event loop`` because Phoenix already runs inside one.
"""

from __future__ import annotations

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


async def task(example) -> list[str]:
    """Run the retrieve node for a single dataset example.

    Parameters
    ----------
    example:
        A ``phoenix.experiments.types.Example`` dataclass whose ``.input``
        mapping contains ``"user_query"``.

    Returns
    -------
    list[str]
        The titles of the documents retrieved for the query.
    """
    query: str = example.input["user_query"]

    from langchain_core.messages import HumanMessage

    state = RAGState(messages=[HumanMessage(content=query)])
    result = await _subgraph.ainvoke(state)
    return result["retrieved_titles"]
