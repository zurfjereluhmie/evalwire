"""LangGraph node isolation helpers (requires evalwire[langgraph] extra)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def build_subgraph(
    nodes: list[tuple[str, Callable]],
    state_cls: type,
    input_cls: type | None = None,
    *,
    name: str | None = None,
    checkpointer: Any = None,
) -> Any:
    """Assemble a minimal linear StateGraph from a list of node callables.

    Edges are added in declaration order:
    ``START → nodes[0] → nodes[1] → … → END``.

    Parameters
    ----------
    nodes:
        Ordered list of ``(node_name, node_callable)`` pairs.
    state_cls:
        LangGraph state dataclass for the graph.
    input_cls:
        Optional input-schema dataclass passed as ``input_schema=input_cls``
        to ``StateGraph``.
    name:
        Optional graph name used for Phoenix tracing.
    checkpointer:
        Optional LangGraph checkpointer.

    Returns
    -------
    CompiledStateGraph
        The compiled subgraph, ready for ``await graph.ainvoke(...)``.
    """
    try:
        from langgraph.graph import (  # type: ignore[import-untyped]
            END,
            START,
            StateGraph,
        )
    except ImportError as exc:
        raise ImportError(
            "evalwire[langgraph] is required to use build_subgraph. "
            "Install it with: pip install 'evalwire[langgraph]'"
        ) from exc

    kwargs: dict[str, Any] = {}
    if input_cls is not None:
        kwargs["input_schema"] = input_cls

    graph = StateGraph(state_cls, **kwargs)

    for node_name, node_fn in nodes:
        graph.add_node(node_name, node_fn)

    node_names = [n for n, _ in nodes]
    for i, node_name in enumerate(node_names):
        if i == 0:
            graph.add_edge(START, node_name)
        if i < len(node_names) - 1:
            graph.add_edge(node_name, node_names[i + 1])
        else:
            graph.add_edge(node_name, END)

    compile_kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    compiled = graph.compile(**compile_kwargs)
    if name is not None:
        compiled.name = name  # type: ignore[attr-defined]

    return compiled


async def invoke_node(
    node_fn: Callable,
    query: str,
    state_cls: type,
    *,
    message_field: str = "messages",
    config: Any = None,
) -> Any:
    """Directly call a single LangGraph node as a standalone async function.

    Constructs a ``state_cls`` instance with a single ``HumanMessage`` placed
    in ``message_field``, calls ``await node_fn(state=state, config=config)``,
    and returns the raw result.

    Parameters
    ----------
    node_fn:
        The node callable to invoke.
    query:
        The human message content to place in ``message_field``.
    state_cls:
        LangGraph state dataclass used to build the input state.
    message_field:
        Name of the field on ``state_cls`` that holds the messages list.
    config:
        Optional ``RunnableConfig``. A default empty config is used if ``None``.

    Returns
    -------
    Any
        The raw return value of the node callable.
    """
    try:
        from langchain_core.messages import HumanMessage  # type: ignore[import-untyped]
        from langchain_core.runnables import (
            RunnableConfig,  # type: ignore[import-untyped]
        )
    except ImportError as exc:
        raise ImportError(
            "langchain-core is required to use invoke_node. "
            "Install it with: pip install langchain-core"
        ) from exc

    state = state_cls(**{message_field: [HumanMessage(content=query)]})
    resolved_config = config if config is not None else RunnableConfig()
    return await node_fn(state=state, config=resolved_config)
