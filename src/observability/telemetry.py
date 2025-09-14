"""
OpenTelemetry Observability Implementation
==========================================

SPARC SPECIFICATION:
-------------------
Purpose: Comprehensive observability for distributed EdTech intelligence platform
Requirements:
  - Distributed tracing across Ray workers and API calls
  - Custom metrics for business KPIs
  - Error tracking with context
  - Performance monitoring with SLOs
  
Exporters:
  - Jaeger for tracing
  - Prometheus for metrics
  - Loki for logs
  - Grafana for visualization
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

from loguru import logger
from opentelemetry import metrics, trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode
from prometheus_client import Counter, Gauge, Histogram, Summary

from src.core.config import get_settings


class TelemetryManager:
    """
    Centralized telemetry management for the platform.
    
    SPARC Architecture:
    - Singleton pattern for global telemetry state
    - Lazy initialization of providers
    - Graceful degradation if telemetry unavailable
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.settings = get_settings()
        self.tracer = None
        self.meter = None
        self.metrics = {}
        
        self._setup_telemetry()
        self._initialized = True
    
    def _setup_telemetry(self):
        """Initialize OpenTelemetry providers."""
        
        # Create resource identifying the service
        resource = Resource.create({
            "service.name": self.settings.OTEL_SERVICE_NAME,
            "service.version": self.settings.APP_VERSION,
            "deployment.environment": self.settings.ENVIRONMENT,
            "service.instance.id": f"{self.settings.OTEL_SERVICE_NAME}-{time.time()}",
        })
        
        # Setup tracing
        if self.settings.OTEL_TRACES_ENABLED:
            self._setup_tracing(resource)
        
        # Setup metrics
        if self.settings.OTEL_METRICS_ENABLED:
            self._setup_metrics(resource)
        
        # Setup custom business metrics
        self._setup_business_metrics()
        
        # Auto-instrument libraries
        self._setup_auto_instrumentation()
    
    def _setup_tracing(self, resource: Resource):
        """Configure distributed tracing."""
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Add OTLP exporter for Jaeger
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=True,
        )
        
        # Add batch processor for performance
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            max_export_interval_millis=5000,
        )
        
        tracer_provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(__name__)
        
        logger.info("OpenTelemetry tracing initialized")
    
    def _setup_metrics(self, resource: Resource):
        """Configure metrics collection."""
        
        # Create meter provider with Prometheus exporter
        prometheus_reader = PrometheusMetricReader()
        
        meter_provider = MeterProvider(
            resource=resource,
            metric_readers=[prometheus_reader],
        )
        
        # Set global meter provider
        metrics.set_meter_provider(meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(__name__)
        
        logger.info("OpenTelemetry metrics initialized")
    
    def _setup_business_metrics(self):
        """Setup custom business KPI metrics."""
        
        # API metrics
        self.metrics['api_requests'] = Counter(
            'corporate_intel_api_requests_total',
            'Total API requests',
            ['method', 'endpoint', 'status']
        )
        
        self.metrics['api_latency'] = Histogram(
            'corporate_intel_api_latency_seconds',
            'API request latency',
            ['method', 'endpoint'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        # Data processing metrics
        self.metrics['documents_processed'] = Counter(
            'corporate_intel_documents_processed_total',
            'Total documents processed',
            ['document_type', 'status']
        )
        
        self.metrics['processing_time'] = Summary(
            'corporate_intel_processing_time_seconds',
            'Document processing time',
            ['document_type']
        )
        
        # Business metrics
        self.metrics['companies_tracked'] = Gauge(
            'corporate_intel_companies_tracked',
            'Number of companies being tracked',
            ['category']
        )
        
        self.metrics['data_freshness'] = Gauge(
            'corporate_intel_data_freshness_hours',
            'Hours since last data update',
            ['data_source']
        )
        
        # Analysis metrics
        self.metrics['analyses_performed'] = Counter(
            'corporate_intel_analyses_performed_total',
            'Total analyses performed',
            ['analysis_type', 'status']
        )
        
        self.metrics['analysis_accuracy'] = Gauge(
            'corporate_intel_analysis_accuracy',
            'Analysis accuracy score',
            ['analysis_type']
        )
        
        # Cache metrics
        self.metrics['cache_hits'] = Counter(
            'corporate_intel_cache_hits_total',
            'Cache hit count',
            ['cache_type']
        )
        
        self.metrics['cache_misses'] = Counter(
            'corporate_intel_cache_misses_total',
            'Cache miss count',
            ['cache_type']
        )
        
        # Ray cluster metrics
        self.metrics['ray_workers_active'] = Gauge(
            'corporate_intel_ray_workers_active',
            'Active Ray workers'
        )
        
        self.metrics['ray_tasks_pending'] = Gauge(
            'corporate_intel_ray_tasks_pending',
            'Pending Ray tasks'
        )
    
    def _setup_auto_instrumentation(self):
        """Auto-instrument common libraries."""
        
        # FastAPI
        FastAPIInstrumentor.instrument(
            tracer_provider=trace.get_tracer_provider(),
            meter_provider=metrics.get_meter_provider(),
        )
        
        # SQLAlchemy
        SQLAlchemyInstrumentor().instrument(
            engine=None,  # Will be set when engine is created
            tracer_provider=trace.get_tracer_provider(),
        )
        
        # Redis
        RedisInstrumentor().instrument(
            tracer_provider=trace.get_tracer_provider(),
        )
        
        # AioHttp Client
        AioHttpClientInstrumentor().instrument(
            tracer_provider=trace.get_tracer_provider(),
        )
        
        logger.info("Auto-instrumentation configured")
    
    @contextmanager
    def trace_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL
    ):
        """Context manager for creating trace spans."""
        
        if not self.tracer:
            yield None
            return
        
        with self.tracer.start_as_current_span(
            name,
            kind=kind,
            attributes=attributes or {}
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """Record a custom metric."""
        
        if metric_name not in self.metrics:
            logger.warning(f"Unknown metric: {metric_name}")
            return
        
        metric = self.metrics[metric_name]
        
        if isinstance(metric, Counter):
            if labels:
                metric.labels(**labels).inc(value)
            else:
                metric.inc(value)
        
        elif isinstance(metric, Gauge):
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
        
        elif isinstance(metric, (Histogram, Summary)):
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)


def trace_async(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator for tracing async functions."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            telemetry = TelemetryManager()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with telemetry.trace_span(span_name, attributes):
                start_time = time.time()
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record success metric
                    telemetry.record_metric(
                        'function_calls',
                        1,
                        {'function': span_name, 'status': 'success'}
                    )
                    
                    return result
                    
                except Exception as e:
                    # Record failure metric
                    telemetry.record_metric(
                        'function_calls',
                        1,
                        {'function': span_name, 'status': 'error'}
                    )
                    raise
                
                finally:
                    # Record duration
                    duration = time.time() - start_time
                    telemetry.record_metric(
                        'function_duration',
                        duration,
                        {'function': span_name}
                    )
        
        return wrapper
    return decorator


def trace_sync(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator for tracing sync functions."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            telemetry = TelemetryManager()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with telemetry.trace_span(span_name, attributes):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Record success metric
                    telemetry.record_metric(
                        'function_calls',
                        1,
                        {'function': span_name, 'status': 'success'}
                    )
                    
                    return result
                    
                except Exception as e:
                    # Record failure metric
                    telemetry.record_metric(
                        'function_calls',
                        1,
                        {'function': span_name, 'status': 'error'}
                    )
                    raise
                
                finally:
                    # Record duration
                    duration = time.time() - start_time
                    telemetry.record_metric(
                        'function_duration',
                        duration,
                        {'function': span_name}
                    )
        
        return wrapper
    return decorator


class SLOMonitor:
    """
    Service Level Objective monitoring.
    
    Tracks:
    - API latency (p99 < 1s)
    - Data freshness (< 4 hours)
    - Analysis accuracy (> 90%)
    - System availability (> 99.9%)
    """
    
    def __init__(self):
        self.telemetry = TelemetryManager()
        self._setup_slo_metrics()
    
    def _setup_slo_metrics(self):
        """Setup SLO-specific metrics."""
        
        self.slo_metrics = {
            'api_latency_p99': Gauge(
                'corporate_intel_slo_api_latency_p99',
                'API latency 99th percentile'
            ),
            'data_freshness_violation': Counter(
                'corporate_intel_slo_data_freshness_violations_total',
                'Data freshness SLO violations'
            ),
            'analysis_accuracy': Gauge(
                'corporate_intel_slo_analysis_accuracy',
                'Analysis accuracy percentage'
            ),
            'availability': Gauge(
                'corporate_intel_slo_availability',
                'System availability percentage'
            ),
        }
    
    def check_api_latency_slo(self, latency_p99: float) -> bool:
        """Check if API latency meets SLO."""
        slo_target = 1.0  # 1 second
        
        self.slo_metrics['api_latency_p99'].set(latency_p99)
        
        if latency_p99 > slo_target:
            logger.warning(f"API latency SLO violation: {latency_p99:.2f}s > {slo_target}s")
            return False
        
        return True
    
    def check_data_freshness_slo(self, hours_since_update: float) -> bool:
        """Check if data freshness meets SLO."""
        slo_target = 4.0  # 4 hours
        
        if hours_since_update > slo_target:
            self.slo_metrics['data_freshness_violation'].inc()
            logger.warning(f"Data freshness SLO violation: {hours_since_update:.1f}h > {slo_target}h")
            return False
        
        return True
    
    def update_analysis_accuracy(self, accuracy: float):
        """Update analysis accuracy metric."""
        self.slo_metrics['analysis_accuracy'].set(accuracy * 100)
        
        if accuracy < 0.9:
            logger.warning(f"Analysis accuracy below target: {accuracy:.1%} < 90%")
    
    def update_availability(self, uptime_seconds: float, total_seconds: float):
        """Update system availability metric."""
        availability = (uptime_seconds / total_seconds) * 100
        self.slo_metrics['availability'].set(availability)
        
        if availability < 99.9:
            logger.warning(f"Availability below target: {availability:.2f}% < 99.9%")


# Global telemetry instance
telemetry = TelemetryManager()