"""Top-K position-weighted retrieval scoring evaluator."""

from collections.abc import Callable
from statistics import mean

from evalwire.evaluators._helpers import _parse_expected


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
