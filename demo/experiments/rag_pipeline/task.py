"""task.py — RAG pipeline experiment task for evalwire.

The task isolates the ``retrieve`` node of the RAG graph using
``evalwire.langgraph.invoke_node``, invokes it with the user query, and
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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phoenix.experiments.types import Example

# Allow ``from agent.graph import ...`` when running from the demo/ root.
_demo_root = Path(__file__).resolve().parents[2]
if str(_demo_root) not in sys.path:
    sys.path.insert(0, str(_demo_root))

from agent.graph import RAGState, retrieve  # noqa: E402

from evalwire.langgraph import invoke_node  # noqa: E402


async def task(example: Example) -> list[str]:
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
    result = await invoke_node(retrieve, example.input["user_query"], RAGState)  # ty: ignore[invalid-argument-type]
    return result["retrieved_titles"]
