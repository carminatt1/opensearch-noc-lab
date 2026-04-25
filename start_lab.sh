#!/bin/bash
# ===========================================================================
# start_lab.sh — Liga todo o ambiente do Laboratório OpenSearch
# ===========================================================================
cd /home/carminatti/opensearch-lab

echo "🐳 Subindo containers Docker..."
docker compose up -d

echo "⏳ Aguardando o OpenSearch ficar saudável (amarelo/verde)..."
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"\(green\|yellow\)"'; do
    echo "Aguardando OpenSearch..."
    sleep 5
done
echo "✅ OpenSearch online!"

echo "🐍 Iniciando geradores de dados Python em background..."
source .venv/bin/activate

# Inicia o gerador principal
nohup python3 scripts/gerar_dados_noc.py > generator.log 2>&1 &
echo "✅ Gerador de Telemetria rodando (PID $!)."

# Inicia o previsor de falhas
nohup python3 scripts/forecasting.py > forecaster.log 2>&1 &
echo "✅ Machine Learning Forecaster rodando (PID $!)."

echo ""
echo "🚀 Laboratório totalmente operacional!"
echo "👉 Acesse o Dashboard em: http://localhost:5601"
