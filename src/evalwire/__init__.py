"""evalwire — systematic evaluation of LangGraph nodes with Arize Phoenix."""

from evalwire.evaluators import make_membership_evaluator, make_top_k_evaluator
from evalwire.observability import setup_observability
from evalwire.runner import ExperimentRunner
from evalwire.uploader import DatasetUploader

__all__ = [
    "DatasetUploader",
    "ExperimentRunner",
    "make_membership_evaluator",
    "make_top_k_evaluator",
    "setup_observability",
    # LangGraph helpers — available when the `evalwire[langgraph]` extra is
    # installed.  Importing from the top-level package is supported; if
    # langgraph is absent the ImportError is raised at call time, not import time.
    "build_subgraph",
    "invoke_node",
]


def __getattr__(name: str):  # noqa: ANN202
    """Lazily expose optional LangGraph helpers at the top-level package.

    This allows ``from evalwire import build_subgraph`` to work when
    ``evalwire[langgraph]`` is installed, without importing langgraph at
    package import time (which would fail if the extra is absent).
    """
    if name in {"build_subgraph", "invoke_node"}:
        from evalwire import langgraph as _lg

        return getattr(_lg, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
