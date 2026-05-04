"""Direct tests for evalwire.evaluators._helpers."""

from evalwire.evaluators._helpers import _parse_expected, _zero_value_for


class TestParseExpected:
    def test_list_input_returned_as_is(self):
        result = _parse_expected({"expected_output": ["a", "b"]})
        assert result == ["a", "b"]

    def test_string_literal_list(self):
        result = _parse_expected({"expected_output": "['x', 'y']"})
        assert result == ["x", "y"]

    def test_plain_string_wrapped_in_list(self):
        result = _parse_expected({"expected_output": "hello"})
        assert result == ["hello"]

    def test_numeric_string_wrapped_in_list(self):
        """ast.literal_eval('3.14') -> float 3.14, which gets wrapped."""
        result = _parse_expected({"expected_output": "3.14"})
        assert result == [3.14]

    def test_integer_string_wrapped_in_list(self):
        result = _parse_expected({"expected_output": "42"})
        assert result == [42]

    def test_missing_key_returns_empty_list(self):
        result = _parse_expected({})
        assert result == []

    def test_empty_list_input(self):
        result = _parse_expected({"expected_output": []})
        assert result == []

    def test_empty_string_wrapped_in_list(self):
        result = _parse_expected({"expected_output": ""})
        # empty string can't be literal_eval'd -> wrapped
        assert result == [""]

    def test_tuple_input_converted_to_list(self):
        result = _parse_expected({"expected_output": ("a", "b")})
        assert result == ["a", "b"]

    def test_string_literal_tuple(self):
        result = _parse_expected({"expected_output": "('a', 'b')"})
        assert result == ["a", "b"]

    def test_nested_list_literal(self):
        """ast.literal_eval on a nested list returns the nested structure."""
        result = _parse_expected({"expected_output": "[['a', 'b'], ['c']]"})
        assert result == [["a", "b"], ["c"]]

    def test_url_string_not_parsed(self):
        """URLs should not be parsed by ast.literal_eval."""
        result = _parse_expected({"expected_output": "https://example.com"})
        assert result == ["https://example.com"]

    def test_none_value(self):
        """None is not a list, not a string -> wrapped as-is."""
        result = _parse_expected({"expected_output": None})
        assert result == [None]

    def test_boolean_string(self):
        """'True' is a valid Python literal."""
        result = _parse_expected({"expected_output": "True"})
        assert result == [True]

    def test_scalar_float_from_literal_eval_is_wrapped_in_list(self):
        """ast.literal_eval('2.72') returns float 2.72; must be wrapped in a list."""
        result = _parse_expected({"expected_output": "2.72"})
        assert result == [2.72]
        assert isinstance(result, list)

    def test_scalar_int_from_literal_eval_is_wrapped_in_list(self):
        """ast.literal_eval('0') returns int 0; must be wrapped in a list."""
        result = _parse_expected({"expected_output": "0"})
        assert result == [0]
        assert isinstance(result, list)

    def test_default_value_when_key_missing_is_empty_list(self):
        """Missing key must return [] not raise and not return None."""
        result = _parse_expected({})
        assert result == []
        assert isinstance(result, list)


class TestZeroValueFor:
    def test_bool_returns_false(self):
        assert _zero_value_for(bool) is False

    def test_int_returns_zero_float(self):
        assert _zero_value_for(int) == 0.0

    def test_float_returns_zero_float(self):
        assert _zero_value_for(float) == 0.0

    def test_str_returns_zero_float(self):
        assert _zero_value_for(str) == 0.0

    def test_none_returns_zero_float(self):
        assert _zero_value_for(None) == 0.0

    def test_custom_type_returns_zero_float(self):
        class Custom:
            pass

        assert _zero_value_for(Custom) == 0.0
