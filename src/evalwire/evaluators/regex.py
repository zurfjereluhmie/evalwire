"""Regular-expression match evaluator."""

import re
from collections.abc import Callable

from evalwire.evaluators._helpers import _parse_expected


def make_regex_evaluator() -> Callable[[str, dict], bool]:
    """Return a regular-expression match evaluator.

    Treats the first value of ``expected["expected_output"]`` as a regex
    pattern and applies :func:`re.search` against ``output``.  Useful for
    validating structured outputs such as dates, identifiers, URLs, or code
    snippets.

    The pattern is compiled at *call time* so that an invalid regex raises
    :class:`re.error` immediately, giving the user a clear signal.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``regex_match(output, expected) -> bool``.
        ``output`` is the string to match against.
        ``expected`` is a dict with key ``"expected_output"`` containing the
        regex pattern string.
        Returns ``False`` when ``output`` is ``None``, the pattern is empty,
        or the key is absent.
        Raises :class:`re.error` if the pattern is syntactically invalid.
    """

    def regex_match(output: str, expected: dict) -> bool:
        if output is None:
            return False
        expected_items = _parse_expected(expected)
        if not expected_items or not expected_items[0]:
            return False
        pattern = expected_items[0]
        return bool(re.search(pattern, output))

    regex_match.__name__ = "regex_match"
    return regex_match
