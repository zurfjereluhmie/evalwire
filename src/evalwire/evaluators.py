"""Built-in evaluator factories for evalwire."""

import ast
from collections.abc import Callable
from statistics import mean

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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
    return list(raw)


def make_top_k_evaluator(K: int = 20) -> Callable[[list[str], dict], float]:
    """Return a position-weighted retrieval scoring evaluator.

    The returned callable scores a ranked list output against expected items.

    Algorithm:
        score_per_item = 1.0 - (position / K)  if item found in output[:K]  else  0.0
        final_score    = mean(score_per_item for item in expected_output)

    Parameters
    ----------
    K:
        Window size. Items found beyond position K-1 score 0.0.

    Returns
    -------
    Callable[[list[str], dict], float]
        Evaluator with signature ``top_k(output, expected) -> float``.
        ``output`` is a list of strings ordered by relevance (most relevant first).
        ``expected`` is a dict with key ``"expected_output"`` containing a
        ``list[str]`` or a ``str`` parseable by ``ast.literal_eval``.
    """

    def top_k(output: list[str], expected: dict) -> float:
        if output is None:
            return 0.0

        expected_items = _parse_expected(expected)

        if not expected_items:
            return 0.0

        scores: list[float] = []
        top_k_results = output[:K]
        for item in expected_items:
            try:
                position = top_k_results.index(item)
                scores.append(1.0 - position / K)
            except ValueError:
                scores.append(0.0)

        return mean(scores)

    top_k.__name__ = "top_k"
    return top_k


def make_membership_evaluator() -> Callable[[str, dict], bool]:
    """Return an exact-membership check evaluator.

    Designed for classification/routing outputs where the expected value is one
    of a small set of labels.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``is_in(output, expected) -> bool``.
        ``output`` is the predicted label string.
        ``expected`` is a dict with key ``"expected_output"`` containing a
        ``list[str]`` or a ``str`` parseable by ``ast.literal_eval``.
        Returns ``True`` if ``output`` is in the expected list.
    """

    def is_in(output: str, expected: dict) -> bool:
        expected_items = _parse_expected(expected)
        return output in expected_items

    is_in.__name__ = "is_in"
    return is_in
