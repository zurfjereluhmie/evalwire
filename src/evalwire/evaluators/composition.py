"""Evaluator composition factories."""

from collections.abc import Callable


def make_weighted_evaluator(
    evaluators: list[tuple[Callable, float]],
) -> Callable[[str, dict], float]:
    """Return a weighted-average composition evaluator.

    Parameters
    ----------
    evaluators:
        List of ``(evaluator, weight)`` pairs. Weights are normalised
        internally and must be non-negative with at least one positive value.

    Returns
    -------
    Callable[[str, dict], float]
        Evaluator with signature ``weighted(output, expected) -> float``.
    """
    if not evaluators:
        raise ValueError("at least one evaluator is required")
    for _, w in evaluators:
        if w < 0:
            raise ValueError("weights must be non-negative")
    total = sum(w for _, w in evaluators)
    if total == 0:
        raise ValueError("total weight must be non-zero")

    normalised = [(fn, w / total) for fn, w in evaluators]

    def weighted(output: str, expected: dict) -> float:
        return float(sum(fn(output, expected) * w for fn, w in normalised))

    weighted.__name__ = "weighted"
    return weighted


def make_all_pass_evaluator(
    evaluators: list[Callable],
) -> Callable[[str, dict], bool]:
    """Return an AND-composition evaluator.

    Returns ``True`` only if every sub-evaluator returns a truthy value.
    Short-circuits on the first falsy result.

    Parameters
    ----------
    evaluators:
        Non-empty list of evaluator callables.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``all_pass(output, expected) -> bool``.
    """
    if not evaluators:
        raise ValueError("at least one evaluator is required")

    def all_pass(output: str, expected: dict) -> bool:
        return all(bool(fn(output, expected)) for fn in evaluators)

    all_pass.__name__ = "all_pass"
    return all_pass


def make_any_pass_evaluator(
    evaluators: list[Callable],
) -> Callable[[str, dict], bool]:
    """Return an OR-composition evaluator.

    Returns ``True`` if at least one sub-evaluator returns a truthy value.
    Short-circuits on the first truthy result.

    Parameters
    ----------
    evaluators:
        Non-empty list of evaluator callables.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``any_pass(output, expected) -> bool``.
    """
    if not evaluators:
        raise ValueError("at least one evaluator is required")

    def any_pass(output: str, expected: dict) -> bool:
        return any(bool(fn(output, expected)) for fn in evaluators)

    any_pass.__name__ = "any_pass"
    return any_pass
