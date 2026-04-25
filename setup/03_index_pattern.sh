#!/bin/bash
# ===========================================================================
# 03_index_pattern.sh — Criar Index Pattern no OpenSearch Dashboards
# Configura telecom-noc-* com timestamp como campo temporal
# ===========================================================================
set -euo pipefail

DASHBOARDS_URL="${DASHBOARDS_URL:-http://localhost:5601}"

echo "🔧 Criando Index Pattern: telecom-noc-*..."

# Aguardar Dashboards estar pronto
echo "⏳ Aguardando OpenSearch Dashboards ficar disponível..."
for i in $(seq 1 30); do
  if curl -sf "${DASHBOARDS_URL}/api/status" > /dev/null 2>&1; then
    echo "   Dashboards pronto!"
    break
  fi
  echo "   Tentativa $i/30... aguardando 5s"
  sleep 5
done

# Criar index pattern via Saved Objects API
curl -sf -X POST "${DASHBOARDS_URL}/api/saved_objects/index-pattern/telecom-noc-pattern" \
  -H "osd-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
  "attributes": {
    "title": "telecom-noc-*",
    "timeFieldName": "timestamp",
    "fields": "[]"
  }
}' && echo ""

echo ""

# Definir como padrão
echo "🔧 Definindo como index pattern padrão..."
curl -sf -X POST "${DASHBOARDS_URL}/api/opensearch-dashboards/settings" \
  -H "osd-xsrf: true" \
  -H "Content-Type: application/json" \
  -d '{
  "changes": {
    "defaultIndex": "telecom-noc-pattern"
  }
}' && echo ""

echo ""
echo "✅ Index Pattern criado e definido como padrão!"
