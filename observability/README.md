# Observability

## Logging estruturado & correlação
- Ative logs JSON com correlação automática usando o header `X-Request-ID`.
- O middleware adiciona o header de resposta e propaga o mesmo ID dentro da aplicação.

## Métricas
- Endpoint `GET /metrics` expõe métricas Prometheus:
  - `http_requests_total`
  - `http_request_errors_total`
  - `http_request_duration_seconds`

## Tracing distribuído
- OpenTelemetry instrumenta FastAPI, requests e aiohttp automaticamente.
- Configure exportação OTLP via env:
  - `OTEL_EXPORTER_OTLP_ENDPOINT` ou `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
  - `OTEL_SERVICE_NAME` opcional (default: título do FastAPI)

## Prometheus
```bash
prometheus --config.file=observability/prometheus.yml
```

## Grafana
- Importe `observability/grafana/dashboards/vtt_api_dashboard.json`.

## Variáveis úteis
```bash
LOG_LEVEL=INFO
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=witcher-vtt-api
```
