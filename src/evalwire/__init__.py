"""evalwire — evaluate any async callable with Arize Phoenix experiments."""

import logging
from importlib.metadata import version

from evalwire.evaluators import (
    make_all_pass_evaluator,
    make_any_pass_evaluator,
    make_contains_evaluator,
    make_exact_match_evaluator,
    make_json_match_evaluator,
    make_llm_judge_evaluator,
    make_membership_evaluator,
    make_numeric_tolerance_evaluator,
    make_regex_evaluator,
    make_schema_evaluator,
    make_top_k_evaluator,
    make_weighted_evaluator,
)
from evalwire.observability import setup_observability
from evalwire.runner import ExperimentRunner
from evalwire.uploader import DatasetUploader

__version__ = version("evalwire")

logging.getLogger("evalwire").addHandler(logging.NullHandler())

__all__ = [
    "DatasetUploader",
    "ExperimentRunner",
    "make_all_pass_evaluator",
    "make_any_pass_evaluator",
    "make_contains_evaluator",
    "make_exact_match_evaluator",
    "make_json_match_evaluator",
    "make_llm_judge_evaluator",
    "make_membership_evaluator",
    "make_numeric_tolerance_evaluator",
    "make_regex_evaluator",
    "make_schema_evaluator",
    "make_top_k_evaluator",
    "make_weighted_evaluator",
    "setup_observability",
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
