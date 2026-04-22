"""JSON Schema validation evaluator."""

import json
from collections.abc import Callable


def make_schema_evaluator(schema: dict) -> Callable[[str, dict], bool]:
    """Return a JSON Schema validation evaluator.

    Parses ``output`` as JSON and validates it against the provided JSON
    Schema dict using ``jsonschema``.  Useful for asserting that LLM outputs
    conform to a declared schema regardless of the specific values produced.

    The JSON schema and validator are both bound at factory-creation time so
    the same validator can be reused across many evaluation rows without
    re-compiling or re-importing.

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
    try:
        import jsonschema
    except ImportError as exc:
        raise ImportError(
            "jsonschema is required to use make_schema_evaluator. "
            "Install it with: pip install 'jsonschema>=4.0'"
        ) from exc

    validator = jsonschema.Draft7Validator(schema)

    def schema_valid(output: str, expected: dict) -> bool:  # noqa: ARG001
        if output is None:
            return False
        try:
            instance = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return False
        return validator.is_valid(instance)

    schema_valid.__name__ = "schema_valid"
    return schema_valid
