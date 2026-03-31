"""Shared helpers used by all evaluator factories."""

import ast
from typing import Any


def _parse_expected(expected: dict) -> list[str]:
    """Parse the ``expected_output`` entry of an *expected* dict into a list.

    Handles three cases:

    * Already a ``list`` – returned as-is (cast to ``list[str]``).
    * A ``str`` that is a valid Python literal (e.g. ``"['a', 'b']"``) –
      evaluated with :func:`ast.literal_eval`.
    * Any other ``str`` (plain identifiers, URLs, …) – wrapped in a
      single-element list.

    Parameters
    ----------
    expected:
        The full ``expected`` dict passed to an evaluator.

    Returns
    -------
    list[str]
        Always a list; may be empty if the key is absent or the value is
        an empty collection.
    """
    raw = expected.get("expected_output", [])
    if isinstance(raw, str):
        try:
            raw = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            raw = [raw]
    # ast.literal_eval may return a non-collection (e.g. a float or int for
    # numeric strings like "2.72").  Wrap scalars so the caller always gets a
    # list it can iterate over.
    if not isinstance(raw, (list, tuple)):
        raw = [raw]
    return list(raw)


def _zero_value_for(annotation: Any) -> Any:
    """Return a sensible zero/falsy value for a given type annotation.

    Used by :func:`~evalwire.evaluators.llm_judge.make_llm_judge_evaluator`
    to determine what to return on a silenced error, based on the declared
    type of ``result_key`` on the output schema.

    Supports ``bool`` → ``False``, any other annotation → ``0.0``.
    """
    if annotation is bool:
        return False
    return 0.0
