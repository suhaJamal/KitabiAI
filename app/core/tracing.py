"""
OpenTelemetry tracing setup with Jaeger integration.
"""

import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from ..core.config import settings

logger = logging.getLogger(__name__)


def setup_tracing(app):
    """
    Setup OpenTelemetry tracing with Jaeger backend.
    
    To run Jaeger locally:
    docker run -d --name jaeger \
      -p 16686:16686 \
      -p 4317:4317 \
      jaegertracing/all-in-one:latest
    
    Access UI: http://localhost:16686
    """
    
    if not settings.ENABLE_TRACING:
        logger.info("⏭️  Tracing disabled")
        return None
    
    try:
        # Define service name
        resource = Resource(attributes={
            "service.name": "kitabiai-api"
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Setup Jaeger exporter
        jaeger_exporter = OTLPSpanExporter(
            endpoint=settings.JAEGER_ENDPOINT,
            insecure=True
        )
        
        # Add batch span processor
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        
        logger.info(f"✅ Tracing enabled: {settings.JAEGER_ENDPOINT}")
        logger.info(f"📊 View traces: http://localhost:16686")
        
        return trace.get_tracer(__name__)
    
    except Exception as e:
        logger.error(f"❌ Failed to setup tracing: {e}")
        return None


def get_tracer():
    """Get the current tracer."""
    return trace.get_tracer(__name__)