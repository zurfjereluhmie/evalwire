"""Async tests for task callables and evalwire.langgraph.invoke_node.

QA 7.1 — all task functions are ``async def``.  This module verifies that
the async execution path is exercised: tasks can be ``await``-ed directly and
return the expected value without requiring a running Phoenix experiment loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_example(input_: dict, output: dict | None = None) -> MagicMock:
    """Return a lightweight stand-in for ``phoenix.experiments.types.Example``."""
    ex = MagicMock()
    ex.input = input_
    ex.output = output or {}
    return ex


# ---------------------------------------------------------------------------
# Tests: async task callable contract
# ---------------------------------------------------------------------------


class TestAsyncTaskCallable:
    """Verify that async task functions can be awaited and return correct values."""

    async def test_async_task_returns_list(self):
        """A minimal async task that mimics the evalwire task contract."""

        async def task(example) -> list[str]:
            return ["doc-a", "doc-b"]

        example = _make_example({"user_query": "find cycling paths"})
        result = await task(example)
        assert result == ["doc-a", "doc-b"]

    async def test_async_task_receives_example_input(self):
        """The task callable receives the example and can read its input field."""
        received: list[dict] = []

        async def task(example) -> str:
            received.append(example.input)
            return example.input["user_query"]

        example = _make_example({"user_query": "hello"})
        result = await task(example)
        assert result == "hello"
        assert received == [{"user_query": "hello"}]

    async def test_async_task_with_mocked_invoke_node(self):
        """Async task that delegates to invoke_node works when invoke_node is mocked."""
        mock_result = {"retrieved_titles": ["title-1", "title-2"]}

        with patch(
            "evalwire.langgraph.invoke_node",
            new=AsyncMock(return_value=mock_result),
        ):
            from evalwire.langgraph import invoke_node

            async def task(example) -> list[str]:
                result = await invoke_node(
                    lambda state, config: None,
                    example.input["user_query"],
                    object,
                )
                return result["retrieved_titles"]

            example = _make_example({"user_query": "query"})
            result = await task(example)

        assert result == ["title-1", "title-2"]

    async def test_async_task_exception_propagates(self):
        """Exceptions raised inside an async task propagate to the caller."""

        async def task(example) -> list[str]:
            raise ValueError("retrieval failed")

        example = _make_example({"user_query": "anything"})
        with pytest.raises(ValueError, match="retrieval failed"):
            await task(example)


# ---------------------------------------------------------------------------
# Tests: invoke_node directly (exercises the async path in evalwire.langgraph)
# ---------------------------------------------------------------------------


class TestInvokeNodeAsync:
    """Exercise evalwire.langgraph.invoke_node as an async function."""

    async def test_invoke_node_awaits_node_fn(self):
        """invoke_node should call the node function and return its result."""
        pytest.importorskip("langchain_core", reason="langchain-core not installed")

        from dataclasses import dataclass, field

        from evalwire.langgraph import invoke_node

        @dataclass
        class SimpleState:
            messages: list = field(default_factory=list)
            retrieved_titles: list[str] = field(default_factory=list)

        async def fake_node(state, config=None):
            return {"retrieved_titles": ["result-from-node"]}

        result = await invoke_node(fake_node, "test query", SimpleState)
        assert result == {"retrieved_titles": ["result-from-node"]}

    async def test_invoke_node_passes_query_as_human_message(self):
        """invoke_node places the query inside a HumanMessage in message_field."""
        from dataclasses import dataclass, field

        import pytest

        pytest.importorskip("langchain_core", reason="langchain-core not installed")

        from langchain_core.messages import (
            HumanMessage,
        )

        from evalwire.langgraph import invoke_node

        @dataclass
        class SimpleState:
            messages: list = field(default_factory=list)

        captured: list = []

        async def spy_node(state, config=None):
            captured.append(state.messages)
            return {}

        await invoke_node(spy_node, "my query", SimpleState)
        assert len(captured) == 1
        assert isinstance(captured[0][0], HumanMessage)
        assert captured[0][0].content == "my query"

    async def test_invoke_node_raises_on_missing_langchain_core(self, monkeypatch):
        """invoke_node raises ImportError if langchain-core is not available."""
        import sys

        from evalwire.langgraph import invoke_node

        monkeypatch.setitem(sys.modules, "langchain_core", None)
        monkeypatch.setitem(sys.modules, "langchain_core.messages", None)
        monkeypatch.setitem(sys.modules, "langchain_core.runnables", None)

        from dataclasses import dataclass, field

        @dataclass
        class S:
            messages: list = field(default_factory=list)

        with pytest.raises(ImportError, match="langchain-core is required"):
            await invoke_node(lambda state, config: None, "q", S)
