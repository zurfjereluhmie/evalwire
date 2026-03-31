"""Built-in evaluator factories for evalwire."""

import ast
import json
import re
from collections.abc import Callable
from statistics import mean
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from pydantic import BaseModel

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
    # ast.literal_eval may return a non-collection (e.g. a float or int for
    # numeric strings like "2.72").  Wrap scalars so the caller always gets a
    # list it can iterate over.
    if not isinstance(raw, (list, tuple)):
        raw = [raw]
    return list(raw)


def _zero_value_for(annotation: Any) -> Any:
    """Return a sensible zero/falsy value for a given type annotation.

    Used by :func:`make_llm_judge_evaluator` to determine what to return
    on a silenced error, based on the declared type of ``result_key`` on
    the output schema.

    Supports ``bool`` → ``False``, any numeric type or ``float``/``int``
    annotation → ``0.0``.  Falls back to ``0.0`` for unknown annotations.
    """
    if annotation is bool:
        return False
    return 0.0


# ---------------------------------------------------------------------------
# Existing evaluators
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# New evaluators
# ---------------------------------------------------------------------------


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


def make_json_match_evaluator(
    keys: list[str] | None = None,
) -> Callable[[str, dict], float]:
    """Return a partial JSON key-value matching evaluator.

    Parses ``output`` as a JSON object and compares specific key-value pairs
    against an expected JSON object stored in ``expected["expected_output"]``.
    Useful for evaluating tool-call outputs, structured generation, and API
    response validation.

    Parameters
    ----------
    keys:
        An optional list of key names to check.  When provided, only those
        keys are compared; keys present in the expected object but absent from
        this list are ignored.  When ``None`` (default), all keys present in
        the expected object are checked.

    Returns
    -------
    Callable[[str, dict], float]
        Evaluator with signature ``json_match(output, expected) -> float``.
        ``output`` is a JSON string representing an object.
        ``expected`` is a dict with key ``"expected_output"`` containing a
        JSON string (or a Python-literal string) that represents the
        ground-truth object.
        Score is the fraction of checked keys whose values match exactly:
        ``n_matching / n_checked``.
        Returns ``0.0`` when ``output`` is not valid JSON, when the
        expected value is empty or not a JSON object, or when no keys are
        checked.
    """

    def json_match(output: str, expected: dict) -> float:
        if output is None:
            return 0.0

        # Parse output JSON
        try:
            output_obj = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return 0.0

        if not isinstance(output_obj, dict):
            return 0.0

        # Parse expected JSON from expected_output
        expected_items = _parse_expected(expected)
        if not expected_items:
            return 0.0
        try:
            expected_obj = json.loads(expected_items[0])
        except (json.JSONDecodeError, TypeError):
            return 0.0

        if not isinstance(expected_obj, dict):
            return 0.0

        # Determine which keys to check
        keys_to_check = keys if keys is not None else list(expected_obj.keys())
        if not keys_to_check:
            return 0.0

        matching = sum(
            1
            for k in keys_to_check
            if k in expected_obj and output_obj.get(k) == expected_obj[k]
        )
        return matching / len(keys_to_check)

    json_match.__name__ = "json_match"
    return json_match


def make_schema_evaluator(schema: dict) -> Callable[[str, dict], bool]:
    """Return a JSON Schema validation evaluator.

    Parses ``output`` as JSON and validates it against the provided JSON
    Schema dict using ``jsonschema``.  Useful for asserting that LLM outputs
    conform to a declared schema regardless of the specific values produced.

    The JSON schema is bound at factory-creation time so the same validator
    can be reused across many evaluation rows without re-compiling.

    Parameters
    ----------
    schema:
        A JSON Schema dict (Draft 7 / Draft 2020-12) describing the expected
        structure of the output.

    Returns
    -------
    Callable[[str, dict], bool]
        Evaluator with signature ``schema_valid(output, expected) -> bool``.
        ``output`` is the JSON string to validate.
        ``expected`` is not used at evaluation time (the schema is fixed at
        factory-creation time) but follows the standard evaluator contract.
        Returns ``True`` when ``output`` is valid JSON that satisfies
        ``schema``, ``False`` otherwise.

    Raises
    ------
    ImportError
        If ``jsonschema`` is not installed.  Install it with::

            pip install 'jsonschema>=4.0'
    """

    def schema_valid(output: str, expected: dict) -> bool:  # noqa: ARG001
        if output is None:
            return False
        try:
            import jsonschema
        except ImportError as exc:
            raise ImportError(
                "jsonschema is required to use make_schema_evaluator. "
                "Install it with: pip install 'jsonschema>=4.0'"
            ) from exc

        try:
            instance = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return False
        try:
            jsonschema.validate(instance=instance, schema=schema)
        except jsonschema.ValidationError:
            return False
        return True

    schema_valid.__name__ = "schema_valid"
    return schema_valid


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


def make_llm_judge_evaluator(
    model: Any,
    prompt_template: str,
    output_schema: "type[BaseModel]",
    *,
    result_key: str = "score",
    on_error: Literal["silent", "reraise"] = "silent",
    error_callback: Callable[[Exception], None] | None = None,
) -> Callable[[str, dict], Any]:
    """Return an LLM-as-a-judge evaluator backed by a LangChain chat model.

    Uses a user-supplied LangChain ``BaseChatModel`` with structured output
    (via :meth:`~langchain_core.language_models.BaseChatModel.with_structured_output`)
    to evaluate free-text model outputs against an expected value.  The judge
    model, evaluation prompt, and output schema are all provided by the caller,
    making this evaluator fully flexible across task types (binary pass/fail,
    1-5 rating, open rubrics, etc.).

    Following Arize best-practice guidance, the prompt template should:

    * State the evaluation criteria explicitly.
    * Request chain-of-thought reasoning *before* the final score/verdict so
      the explanation field precedes the ``result_key`` field in the schema.
    * Use ``{output}`` and ``{expected_output}`` as placeholders for the
      model output and the ground-truth value respectively.

    Example usage::

        from langchain.chat_models import init_chat_model
        from pydantic import BaseModel

        class Verdict(BaseModel):
            explanation: str
            score: bool           # True = correct, False = incorrect

        judge = make_llm_judge_evaluator(
            model=init_chat_model("gpt-4o-mini"),
            prompt_template=(
                "You are an expert evaluator.\\n"
                "Question answer: {output}\\n"
                "Expected answer: {expected_output}\\n"
                "Is the answer factually correct? "
                "Think step by step, then set score to true or false."
            ),
            output_schema=Verdict,
        )

    Parameters
    ----------
    model:
        A LangChain ``BaseChatModel`` instance (e.g. obtained via
        ``langchain.chat_models.init_chat_model``).
    prompt_template:
        A string containing ``{output}`` and optionally
        ``{expected_output}`` placeholders that will be formatted at
        evaluation time.
    output_schema:
        A Pydantic ``BaseModel`` subclass.  The factory calls
        ``model.with_structured_output(output_schema)`` once to bind the
        structured-output chain.
    result_key:
        Name of the field on the schema instance whose value is returned
        as the final score.  Defaults to ``"score"``.  The return type of
        the evaluator is inferred from the field's type annotation
        (``bool`` → returns ``bool``; anything else → returns ``float``).
    on_error:
        Behaviour when the LLM call or result extraction raises an
        exception:

        * ``"silent"`` (default) – swallow the exception and return the
          zero-value for the inferred type (``False`` for ``bool``,
          ``0.0`` otherwise).
        * ``"reraise"`` – call ``error_callback(exc)`` then re-raise.
          ``error_callback`` is required when this option is chosen.
    error_callback:
        A callable that receives the exception before it is re-raised.
        Required when ``on_error="reraise"``, ignored otherwise.

    Returns
    -------
    Callable[[str, dict], float | bool]
        Evaluator with signature ``llm_judge(output, expected) -> score``.

    Raises
    ------
    ValueError
        If ``on_error="reraise"`` is selected without supplying an
        ``error_callback``.
    ImportError
        If ``langchain-core`` is not installed.  Install it with::

            pip install 'evalwire[llm-judge]'
    """
    if on_error == "reraise" and error_callback is None:
        raise ValueError(
            "error_callback is required when on_error='reraise'. "
            "Provide a callable that accepts the exception as its only argument."
        )

    # Infer the zero-value from the Pydantic field annotation so that silent
    # errors return a type-appropriate default.
    try:
        field_annotation = output_schema.model_fields[result_key].annotation
    except KeyError:
        field_annotation = float
    _zero: Any = _zero_value_for(field_annotation)

    # Bind the structured-output chain once at factory-creation time so that
    # any ImportError for langchain-core surfaces early with a clear message.
    try:
        structured_chain = model.with_structured_output(output_schema)
    except AttributeError:
        # model doesn't have with_structured_output → langchain-core missing
        raise ImportError(
            "langchain-core is required to use make_llm_judge_evaluator. "
            "Install it with: pip install 'evalwire[llm-judge]'"
        )

    def llm_judge(output: str, expected: dict) -> Any:
        expected_items = _parse_expected(expected)
        expected_output = expected_items[0] if expected_items else ""
        prompt = prompt_template.format(
            output=output if output is not None else "",
            expected_output=expected_output,
        )
        try:
            result = structured_chain.invoke(prompt)
            return getattr(result, result_key)
        except Exception as exc:  # noqa: BLE001
            if on_error == "reraise":
                if error_callback is not None:
                    error_callback(exc)
                raise
            return _zero

    llm_judge.__name__ = "llm_judge"
    return llm_judge
