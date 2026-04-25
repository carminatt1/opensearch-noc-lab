# OpenSearch NOC Lab 📡

Uma prova de conceito (PoC) de um pipeline de dados fim-a-fim utilizando **OpenSearch 2.13.0** para monitoramento avançado de Network Operations Center (NOC).

## 🚀 Funcionalidades Principais

1. **Ingestão em Tempo Real:** Gerador de dados em Python simulando múltiplos hosts, interfaces e métricas vitais de rede.
2. **Dashboard Executivo:** Visualizações ricas (Heatmaps, Histogramas, Stacked Bars) criadas no OpenSearch Dashboards.
3. **Mapeamento Geográfico (Geo-IP):** Mapa interativo de incidentes (Heatmap Geográfico) apontando ocorrências no Brasil em tempo real.
4. **Machine Learning Forecasting:** Script autônomo (Regressão Linear / OLS) que projeta o comportamento futuro da rede em gráficos integrados.
5. **Detecção de Anomalias (RCF):** Integração nativa com o plugin *Anomaly Detection* usando o algoritmo *Random Cut Forest* para achar desvios invisíveis a olho nu.
6. **Alertas Dinâmicos via Telegram:** Microserviço em Python que processa Webhooks do OpenSearch e notifica os operadores do NOC imediatamente no celular.
7. **Index State Management (ISM):** Políticas de ciclo de vida ativas (`Hot → Warm → Delete`).

## Como rodar o projeto

1. Renomeie `.env.example` para `.env` e adicione seus tokens do Telegram.
2. Suba a infraestrutura:
```bash
docker compose up -d
```
3. Aguarde o OpenSearch inicializar (status `Green`) e crie a virtualenv:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```
4. Execute o orquestrador para aplicar templates, políticas e iniciar a ingestão:
```bash
chmod +x setup.sh setup/*.sh
./setup.sh --with-data
```
