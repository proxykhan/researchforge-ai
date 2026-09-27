"""OpenTelemetry tracing setup.

Production: exports spans via OTLP (to a collector sidecar on ECS).
Development: optional console exporter for debugging.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

SERVICE_NAME = "researchforge-ai"


def setup_tracing(
    *,
    otlp_endpoint: str = "",
    console: bool = False,
    service_name: str = SERVICE_NAME,
    environment: str = "development",
) -> None:
    """Initialize the global TracerProvider.

    Args:
        otlp_endpoint: OTLP gRPC endpoint (e.g. "http://localhost:4317").
                       Empty string disables OTLP export.
        console: If True, also print spans to stdout (dev only).
        service_name: OpenTelemetry service name.
        environment: Deployment environment tag.
    """
    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": environment,
        }
    )

    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    if console:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)


def get_tracer(name: str = SERVICE_NAME) -> trace.Tracer:
    """Get a tracer from the global provider."""
    return trace.get_tracer(name)
