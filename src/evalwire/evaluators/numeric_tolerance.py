"""Numeric proximity (tolerance) evaluator."""

from collections.abc import Callable

from evalwire.evaluators._helpers import _parse_expected


def make_numeric_tolerance_evaluator(
    atol: float = 1e-6,
    rtol: float = 0.0,
) -> Callable[[str | float, dict], bool]:
    """Return a numeric proximity evaluator.

    Checks whether a numeric model output is within an absolute and/or
    relative tolerance of the expected value.  Mirrors the semantics of
    :func:`math.isclose`:

    .. code-block:: text

        |output - expected| <= atol + rtol * |expected|

    Useful for math-reasoning, unit-conversion, and calculation agent tasks.

    Parameters
    ----------
    atol:
        Absolute tolerance (default ``1e-6``).
    rtol:
        Relative tolerance as a fraction of the expected value
        (default ``0.0``).  Set to e.g. ``0.01`` for a 1 % tolerance.

    Returns
    -------
    Callable[[str | float, dict], bool]
        Evaluator with signature ``numeric_close(output, expected) -> bool``.
        ``output`` may be a numeric string or a ``float``/``int``.
        ``expected`` is a dict with key ``"expected_output"`` containing a
        numeric string or a single-element list with a numeric string.
        Returns ``False`` when either value cannot be converted to ``float``,
        when ``expected`` is empty, or when the key is missing.
    """

    def numeric_close(output: str | float, expected: dict) -> bool:
        if output is None:
            return False
        expected_items = _parse_expected(expected)
        if not expected_items:
            return False
        try:
            out_val = float(output)
            exp_val = float(expected_items[0])
        except (ValueError, TypeError):
            return False
        return abs(out_val - exp_val) <= atol + rtol * abs(exp_val)

    numeric_close.__name__ = "numeric_close"
    return numeric_close
