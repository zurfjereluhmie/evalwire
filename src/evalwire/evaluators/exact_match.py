"""Strict string-equality evaluator."""

from collections.abc import Callable

from evalwire.evaluators._helpers import _parse_expected


def make_exact_match_evaluator() -> Callable[[str, dict], bool]:
    """Return a strict string-equality evaluator.

    Compares the model output against a single ground-truth string stored in
    ``expected["expected_output"]``.  Useful for extractive QA and any task
    where exactly one correct answer exists.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``exact_match(output, expected) -> bool``.
        ``output`` is the model-generated string.
        ``expected`` is a dict with key ``"expected_output"`` containing a
        single string (or a single-element list/literal whose first element
        is the ground truth).
        Returns ``True`` only when ``output`` equals the first expected item
        character-for-character (case-sensitive).
        Returns ``False`` when ``output`` is ``None``, the key is absent, or
        the expected list is empty.
    """

    def exact_match(output: str, expected: dict) -> bool:
        if output is None:
            return False
        expected_items = _parse_expected(expected)
        if not expected_items:
            return False
        return output == expected_items[0]

    exact_match.__name__ = "exact_match"
    return exact_match
