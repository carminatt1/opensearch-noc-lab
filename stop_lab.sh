#!/bin/bash
# ===========================================================================
# stop_lab.sh — Desliga todo o ambiente do Laboratório OpenSearch
# ===========================================================================
echo "🛑 Desligando geradores de dados Python..."
pkill -f gerar_dados_noc.py || echo "Nenhum gerador de dados rodando."
pkill -f forecasting.py || echo "Nenhum forecaster rodando."

echo "🐳 Desligando containers Docker..."
cd /home/carminatti/opensearch-lab
docker compose down

echo ""
echo "✅ Ambiente desligado com sucesso. Bom descanso!"
