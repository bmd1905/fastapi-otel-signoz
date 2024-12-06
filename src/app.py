import time

import uvicorn
from fastapi import FastAPI, Request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.semconv.resource import ResourceAttributes

# Initialize Resource
resource = Resource.create({ResourceAttributes.SERVICE_NAME: "fastapi-app"})

# Initialize TracerProvider
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_span_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_span_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Initialize MeterProvider
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
)
metrics.set_meter_provider(
    MeterProvider(resource=resource, metric_readers=[metric_reader])
)

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create some metrics
request_counter = meter.create_counter(
    name="request_counter",
    description="Counts the number of requests",
    unit="1",
)

request_duration = meter.create_histogram(
    name="request_duration",
    description="Duration of requests",
    unit="ms",
)

app = FastAPI()

# Instrument FastAPI application
FastAPIInstrumentor.instrument_app(app)


@app.get("/")
def read_root():
    # Increment request counter
    request_counter.add(1, {"endpoint": "root"})

    with tracer.start_as_current_span("read_root") as span:
        with tracer.start_as_current_span("read_root_inner"):
            data = {"message": "Hello, World!"}
        with tracer.start_as_current_span("read_root_inner_inner"):
            data["message"] = "Hello, World! Inner Inner"

        # Record duration (this is a simplified example - you might want to use actual timing)
        request_duration.record(100, {"endpoint": "root"})

        return data


@app.middleware("http")
async def add_metrics(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000  # Convert to milliseconds

    request_counter.add(
        1,
        {
            "endpoint": request.url.path,
            "method": request.method,
        },
    )

    request_duration.record(
        duration,
        {
            "endpoint": request.url.path,
            "method": request.method,
        },
    )

    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
