"""Observability setup for evalwire — registers Phoenix as the OTel provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider


def setup_observability(
    instrumentors: list[Any] | None = None,
    *,
    auto_instrument: bool = True,
) -> TracerProvider:
    """Register Phoenix as the OpenTelemetry tracer provider.

    Parameters
    ----------
    instrumentors:
        List of OpenInference instrumentor instances to activate.
        Each must implement ``.instrument(tracer_provider=...)``.
    auto_instrument:
        Passed to ``phoenix.otel.register()``. When ``True``, Phoenix will
        attempt to auto-detect and instrument known libraries.

    Returns
    -------
    TracerProvider
        The registered tracer provider.
    """
    from phoenix.otel import register

    tracer_provider = register(auto_instrument=auto_instrument)

    for instrumentor in instrumentors or []:
        instrumentor.instrument(tracer_provider=tracer_provider)

    return tracer_provider
