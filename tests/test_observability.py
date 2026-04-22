"""Tests for evalwire.observability.setup_observability."""

from unittest.mock import MagicMock, patch


class TestSetupObservability:
    def test_calls_register_with_auto_instrument_true(self):
        mock_provider = MagicMock()
        with patch(
            "phoenix.otel.register", return_value=mock_provider, create=True
        ) as mock_register:
            from evalwire.observability import setup_observability

            result = setup_observability()

        mock_register.assert_called_once_with(auto_instrument=True)
        assert result is mock_provider

    def test_calls_register_with_auto_instrument_false(self):
        mock_provider = MagicMock()
        with patch(
            "phoenix.otel.register", return_value=mock_provider, create=True
        ) as mock_register:
            from evalwire.observability import setup_observability

            result = setup_observability(auto_instrument=False)

        mock_register.assert_called_once_with(auto_instrument=False)
        assert result is mock_provider

    def test_instruments_each_instrumentor(self):
        mock_provider = MagicMock()
        inst_a = MagicMock()
        inst_b = MagicMock()

        with patch("phoenix.otel.register", return_value=mock_provider, create=True):
            from evalwire.observability import setup_observability

            setup_observability(instrumentors=[inst_a, inst_b])

        inst_a.instrument.assert_called_once_with(tracer_provider=mock_provider)
        inst_b.instrument.assert_called_once_with(tracer_provider=mock_provider)

    def test_no_instrumentors_none(self):
        mock_provider = MagicMock()
        with patch("phoenix.otel.register", return_value=mock_provider, create=True):
            from evalwire.observability import setup_observability

            # Should not raise when instrumentors is None (default)
            result = setup_observability(instrumentors=None)

        assert result is mock_provider

    def test_empty_instrumentors_list(self):
        mock_provider = MagicMock()
        with patch("phoenix.otel.register", return_value=mock_provider, create=True):
            from evalwire.observability import setup_observability

            result = setup_observability(instrumentors=[])

        assert result is mock_provider
