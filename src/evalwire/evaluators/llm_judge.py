"""LLM-as-a-judge evaluator backed by a LangChain chat model."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Literal

from evalwire.evaluators._helpers import _parse_expected, _zero_value_for

if TYPE_CHECKING:
    from pydantic import BaseModel


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
