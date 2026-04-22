"""Tests for evalwire.langgraph.build_subgraph."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

import pytest


class TestBuildSubgraph:
    """Tests for build_subgraph (requires evalwire[langgraph] extra)."""

    @pytest.fixture(autouse=True)
    def _skip_without_langgraph(self):
        pytest.importorskip("langgraph", reason="langgraph not installed")

    @pytest.fixture()
    def state_cls(self):
        @dataclass
        class State:
            value: str = ""

        return State

    def test_single_node_graph(self, state_cls: type):
        from evalwire.langgraph import build_subgraph

        def node_a(state: Any) -> dict:
            return {"value": "a"}

        compiled = build_subgraph(
            nodes=[("node_a", node_a)],
            state_cls=state_cls,
        )
        assert compiled is not None

    def test_linear_edge_wiring(self, state_cls: type):
        """START -> n1 -> n2 -> n3 -> END."""
        from evalwire.langgraph import build_subgraph

        call_order: list[str] = []

        def node_1(state: Any) -> dict:
            call_order.append("n1")
            return {"value": state.value + "1"}

        def node_2(state: Any) -> dict:
            call_order.append("n2")
            return {"value": state.value + "2"}

        def node_3(state: Any) -> dict:
            call_order.append("n3")
            return {"value": state.value + "3"}

        compiled = build_subgraph(
            nodes=[("n1", node_1), ("n2", node_2), ("n3", node_3)],
            state_cls=state_cls,
        )
        result = compiled.invoke({"value": ""})
        assert result["value"] == "123"
        assert call_order == ["n1", "n2", "n3"]

    def test_with_name_parameter(self, state_cls: type):
        from evalwire.langgraph import build_subgraph

        compiled = build_subgraph(
            nodes=[("n", lambda state: {"value": "x"})],
            state_cls=state_cls,
            name="my-graph",
        )
        assert compiled.name == "my-graph"

    def test_without_name_parameter(self, state_cls: type):
        from evalwire.langgraph import build_subgraph

        compiled = build_subgraph(
            nodes=[("n", lambda state: {"value": "x"})],
            state_cls=state_cls,
        )
        # Default name assigned by LangGraph (not None)
        assert compiled.name is not None

    def test_with_input_cls(self):
        from evalwire.langgraph import build_subgraph

        @dataclass
        class FullState:
            query: str = ""
            result: str = ""

        @dataclass
        class InputState:
            query: str = ""

        compiled = build_subgraph(
            nodes=[("n", lambda state: {"result": "done"})],
            state_cls=FullState,
            input_cls=InputState,
        )
        result = compiled.invoke({"query": "hello"})
        assert result["result"] == "done"

    def test_with_checkpointer(self, state_cls: type):
        from langgraph.checkpoint.memory import InMemorySaver

        from evalwire.langgraph import build_subgraph

        compiled = build_subgraph(
            nodes=[("n", lambda state: {"value": "x"})],
            state_cls=state_cls,
            checkpointer=InMemorySaver(),
        )
        assert compiled is not None

    def test_empty_nodes_raises(self, state_cls: type):
        from evalwire.langgraph import build_subgraph

        with pytest.raises(IndexError):
            build_subgraph(nodes=[], state_cls=state_cls)


class TestBuildSubgraphImportError:
    def test_raises_import_error_without_langgraph(self, monkeypatch):
        """build_subgraph raises ImportError if langgraph is not installed."""
        monkeypatch.setitem(sys.modules, "langgraph", None)
        monkeypatch.setitem(sys.modules, "langgraph.graph", None)

        from evalwire.langgraph import build_subgraph

        with pytest.raises(ImportError, match="evalwire\\[langgraph\\]"):
            build_subgraph(nodes=[("n", lambda s: s)], state_cls=object)
