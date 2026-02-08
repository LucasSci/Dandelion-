#!/usr/bin/env bash
set -euo pipefail

action="${1:-}"
environment="${2:-}"
canary_percent="${3:-10}"
healthcheck_url="${HEALTHCHECK_URL:-}"

if [[ -z "$action" || -z "$environment" ]]; then
  echo "Usage: $0 <canary|promote|rollback|healthcheck> <environment> [canary_percent]" >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
release_id="${RELEASE_ID:-$timestamp}"

log() {
  echo "[$timestamp][$environment][$action] $*"
}

case "$action" in
  canary)
    log "Iniciando deploy canário com ${canary_percent}% do tráfego (release: ${release_id})."
    log "Aplique infraestrutura/manifestos para o canário aqui."
    ;;
  promote)
    log "Promovendo canário para 100% do tráfego (release: ${release_id})."
    log "Finalize a promoção do release canário aqui."
    ;;
  rollback)
    log "Executando rollback para o release anterior."
    log "Restaure manifests/infra para a versão estável aqui."
    ;;
  healthcheck)
    if [[ -n "$healthcheck_url" ]]; then
      log "Executando healthcheck em ${healthcheck_url}."
      curl -fsS "$healthcheck_url" >/dev/null
    else
      log "HEALTHCHECK_URL não definido; pulando verificação externa."
    fi
    ;;
  *)
    echo "Ação inválida: $action" >&2
    exit 1
    ;;
esac
