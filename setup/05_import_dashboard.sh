#!/bin/bash
# ===========================================================================
# 05_import_dashboard.sh — Gera e importa Dashboard no OpenSearch Dashboards
# ===========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARDS_URL="${DASHBOARDS_URL:-http://localhost:5601}"

echo "🔧 Gerando Dashboard NDJSON..."
python3 "${SCRIPT_DIR}/generate_dashboard.py"

NDJSON_FILE="${SCRIPT_DIR}/05_dashboard.ndjson"

if [ ! -f "$NDJSON_FILE" ]; then
  echo "❌ Arquivo NDJSON não encontrado: $NDJSON_FILE"
  exit 1
fi

echo "📦 Importando Dashboard no OpenSearch Dashboards..."
RESPONSE=$(curl -sf -X POST "${DASHBOARDS_URL}/api/saved_objects/_import?overwrite=true" \
  -H "osd-xsrf: true" \
  --form file=@"${NDJSON_FILE}")

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# Verificar sucesso
SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null || echo "false")
if [ "$SUCCESS" = "True" ]; then
  echo ""
  echo "✅ Dashboard importado com sucesso!"
  echo "🔗 Acesse: ${DASHBOARDS_URL}/app/dashboards#/view/dashboard-noc-analytics"
else
  echo ""
  echo "⚠️  Verifique a resposta acima para possíveis erros na importação."
fi
