"""Substring-containment evaluator."""

from collections.abc import Callable

from evalwire.evaluators._helpers import _parse_expected


def make_contains_evaluator() -> Callable[[str, dict], bool]:
    """Return a substring-containment evaluator.

    Checks whether the first value in ``expected["expected_output"]`` appears
    as a substring of ``output``.  Useful for free-text generation tasks where
    the answer must include a specific phrase or keyword.

    To test the reverse (output is a substring of the expected string), wrap
    the result with ``not``::

        contains = make_contains_evaluator()
        inverted = lambda out, exp: not contains(out, exp)

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``contains(output, expected) -> bool``.
        ``output`` is the model-generated string.
        ``expected`` is a dict with key ``"expected_output"`` whose first item
        is the substring that must appear in ``output``.
        Returns ``False`` when ``output`` is ``None``, the key is absent, or
        the expected list is empty.
    """

    def contains(output: str, expected: dict) -> bool:
        if output is None:
            return False
        expected_items = _parse_expected(expected)
        if not expected_items:
            return False
        return expected_items[0] in output

    contains.__name__ = "contains"
    return contains
