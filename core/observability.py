from prometheus_client import Counter, Gauge, Histogram, start_http_server
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from core.config import settings
import structlog

logger = structlog.get_logger()

# Prometheus metrics
prs_reviewed_total = Counter("prs_reviewed_total", "Total PRs reviewed")
fix_prs_opened_total = Counter("fix_prs_opened_total", "Total fix PRs opened")
plans_executed_total = Counter("plans_executed_total", "Total plans executed")
task_duration_seconds = Histogram(
    "task_duration_seconds", "Task execution duration", buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60)
)
active_plans = Gauge("active_plans", "Currently executing plans")

# OpenTelemetry setup
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "open-gitclaw"
})
trace.set_tracer_provider(TracerProvider(resource=resource))
if settings.OTLP_ENDPOINT:
    otlp_exporter = OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT, insecure=True)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
tracer = trace.get_tracer("open-gitclaw")

def setup_observability():
    # Start Prometheus metrics server on port 8001
    start_http_server(8001)
    logger.info("Observability started: Prometheus on :8001/metrics, OTLP to %s", settings.OTLP_ENDPOINT or "disabled")

# Context manager for tracing tasks
class traced_task:
    def __init__(self, name: str):
        self.name = name
        self.span = None

    def __enter__(self):
        self.span = tracer.start_as_current_span(self.name)
        active_plans.inc()
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        active_plans.dec()
        if exc_type is None:
            self.span.set_status(trace.StatusCode.OK)
        else:
            self.span.set_status(trace.StatusCode.ERROR, str(exc_val))
        self.span.end()
