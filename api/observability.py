from __future__ import annotations

import json
import logging
import os
import time
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_ID_HEADER = "X-Request-ID"
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status_code"],
)
REQUEST_ERRORS = Counter(
    "http_request_errors_total",
    "Total HTTP error responses",
    labelnames=["method", "path", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": request_id_ctx_var.get(),
        }
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }
        }
        if extra:
            log_record.update(extra)
        return json.dumps(log_record, ensure_ascii=False)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    root_logger.addHandler(handler)


def _should_export_traces() -> bool:
    return bool(
        os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    )


def configure_tracing(service_name: str) -> None:
    if trace.get_tracer_provider().__class__ is TracerProvider:
        return
    resource = Resource.create({"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)
    if _should_export_traces():
        exporter = OTLPSpanExporter()
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)
    RequestsInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()


def _get_correlation_id(request: Request) -> str:
    header_value = request.headers.get(REQUEST_ID_HEADER)
    return header_value if header_value else str(uuid4())


def instrument_app(app: FastAPI) -> None:
    configure_logging()
    configure_tracing(service_name=app.title)
    FastAPIInstrumentor.instrument_app(app)

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next) -> Response:
        correlation_id = _get_correlation_id(request)
        token = request_id_ctx_var.set(correlation_id)
        start_time = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.perf_counter() - start_time
            path = request.url.path
            method = request.method
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
            REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            if status_code >= 400:
                REQUEST_ERRORS.labels(method=method, path=path, status_code=status_code).inc()
            logging.getLogger("api.request").info(
                "request.completed",
                extra={
                    "http": {
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                        "duration_ms": round(duration * 1000, 2),
                    }
                },
            )
            request_id_ctx_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = correlation_id
        return response

    @app.get("/metrics")
    def metrics() -> Response:
        data = generate_latest()
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def start_internal_span(name: str, attributes: dict[str, Any] | None = None):
    tracer = trace.get_tracer("api.internal")
    span = tracer.start_span(name)
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    return span


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    span = trace.get_current_span()
    if attributes:
        span.add_event(name, attributes=attributes)
    else:
        span.add_event(name)
