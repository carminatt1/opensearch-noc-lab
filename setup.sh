#!/bin/bash
# ===========================================================================
# setup.sh — Orquestrador master do OpenSearch Lab
# Executa todas as etapas de configuração na ordem correta
#
# Uso:
#   ./setup.sh              # Setup completo (sem iniciar gerador de dados)
#   ./setup.sh --with-data  # Setup completo + inicia gerador de dados
# ===========================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_DIR="${SCRIPT_DIR}/setup"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"
DASHBOARDS_URL="${DASHBOARDS_URL:-http://localhost:5601}"

export OPENSEARCH_URL
export DASHBOARDS_URL

WITH_DATA=false
if [[ "${1:-}" == "--with-data" ]]; then
  WITH_DATA=true
fi

echo "============================================================"
echo " 🚀 OpenSearch Lab — Setup Completo"
echo "============================================================"
echo " OpenSearch:  ${OPENSEARCH_URL}"
echo " Dashboards:  ${DASHBOARDS_URL}"
echo " Gerar dados: ${WITH_DATA}"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------
# Etapa 0: Aguardar OpenSearch ficar saudável
# -----------------------------------------------------------------------
echo "⏳ [0/5] Aguardando OpenSearch ficar disponível..."
MAX_RETRIES=60
RETRY_COUNT=0
while ! curl -sf "${OPENSEARCH_URL}/_cluster/health" > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "❌ OpenSearch não respondeu após ${MAX_RETRIES} tentativas."
    echo "   Certifique-se de que os containers estão rodando:"
    echo "   docker compose up -d"
    exit 1
  fi
  echo "   Tentativa ${RETRY_COUNT}/${MAX_RETRIES}... aguardando 5s"
  sleep 5
done

CLUSTER_STATUS=$(curl -sf "${OPENSEARCH_URL}/_cluster/health" | python3 -c "import sys,json; h=json.load(sys.stdin); print(f\"name={h['cluster_name']} status={h['status']} nodes={h['number_of_nodes']}\")" 2>/dev/null || echo "conectado")
echo "✅ OpenSearch disponível: ${CLUSTER_STATUS}"
echo ""

# -----------------------------------------------------------------------
# Etapa 1: Index Template
# -----------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " [1/5] Index Template"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "${SETUP_DIR}/01_index_template.sh"
echo ""

# -----------------------------------------------------------------------
# Etapa 2: ISM Policy
# -----------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " [2/5] ISM Policy (Rotatividade de Dados)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "${SETUP_DIR}/02_ism_policy.sh"
echo ""

# -----------------------------------------------------------------------
# Etapa 3: Index Pattern no Dashboards
# -----------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " [3/5] Index Pattern (Dashboards Discovery)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "${SETUP_DIR}/03_index_pattern.sh"
echo ""

# -----------------------------------------------------------------------
# Etapa 4: Anomaly Detection
# -----------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " [4/5] Anomaly Detection (Random Cut Forest)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Nota: Os detectores precisam de dados existentes para funcionar.
# Se não houver dados, eles serão criados mas iniciados após os dados chegarem.
echo "⚠️  NOTA: Os detectores serão criados mas só detectam anomalias"
echo "   após receberem dados suficientes (~5 minutos de ingestão)."
echo ""
bash "${SETUP_DIR}/04_anomaly_detector.sh"
echo ""

# -----------------------------------------------------------------------
# Etapa 5: Dashboard
# -----------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " [5/5] Dashboard Analítico"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "${SETUP_DIR}/05_import_dashboard.sh"
echo ""

# -----------------------------------------------------------------------
# Resumo Final
# -----------------------------------------------------------------------
echo ""
echo "============================================================"
echo " ✅ SETUP CONCLUÍDO COM SUCESSO!"
echo "============================================================"
echo ""
echo " 📊 Dashboard:    ${DASHBOARDS_URL}/app/dashboards#/view/dashboard-noc-analytics"
echo " 🔍 Discovery:    ${DASHBOARDS_URL}/app/discover"
echo " 🤖 Anomalias:    ${DASHBOARDS_URL}/app/anomaly-detection-dashboards"
echo " 📡 Cluster:      ${OPENSEARCH_URL}/_cluster/health?pretty"
echo ""

# -----------------------------------------------------------------------
# Opcional: Iniciar gerador de dados
# -----------------------------------------------------------------------
if [ "$WITH_DATA" = true ]; then
  echo "============================================================"
  echo " 📡 Iniciando Gerador de Dados NOC..."
  echo " (Ctrl+C para parar)"
  echo "============================================================"
  echo ""

  # Instalar dependências se necessário
  if [ -f "${SCRIPTS_DIR}/requirements.txt" ]; then
    echo "📦 Instalando dependências Python..."
    pip3 install -r "${SCRIPTS_DIR}/requirements.txt" --quiet 2>/dev/null || \
      pip install -r "${SCRIPTS_DIR}/requirements.txt" --quiet 2>/dev/null || \
      echo "⚠️  Falha ao instalar dependências. Instale manualmente: pip install -r scripts/requirements.txt"
  fi

  python3 "${SCRIPTS_DIR}/gerar_dados_noc.py"
else
  echo " 💡 Para iniciar a ingestão de dados:"
  echo "    pip install -r scripts/requirements.txt"
  echo "    python3 scripts/gerar_dados_noc.py"
  echo ""
  echo "    Ou rode novamente com:"
  echo "    ./setup.sh --with-data"
fi
