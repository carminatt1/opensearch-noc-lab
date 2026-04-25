#!/usr/bin/env python3
"""
Módulo de Previsão de Falhas (Machine Learning Forecasting)
Usa Regressão Linear Simples (OLS) para projetar a utilização de rede no futuro.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timezone, timedelta

from opensearchpy import OpenSearch, helpers

# Configurações
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
HISTORICAL_MINUTES = 60
FORECAST_MINUTES = 15
INTERVAL_SECONDS = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("forecaster")

def create_client():
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        use_ssl=False, verify_certs=False, timeout=30
    )

def linear_regression(x, y):
    """Calcula a regressão linear simples (y = mx + b)."""
    n = len(x)
    if n < 2: return 0, 0
    
    sum_x = sum(x)
    sum_y = sum(y)
    sum_x_sq = sum(xi * xi for xi in x)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    
    denominator = (n * sum_x_sq - sum_x * sum_x)
    if denominator == 0: return 0, 0
    
    m = (n * sum_xy - sum_x * sum_y) / denominator
    b = (sum_y - m * sum_x) / n
    return m, b

def run_forecast(client):
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=HISTORICAL_MINUTES)
    
    # Query para buscar a média de utilização por minuto e por hostname
    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"range": {"timestamp": {"gte": start_time.isoformat()}}},
                    {"exists": {"field": "utilization_pct"}}
                ],
                "must_not": [
                    {"wildcard": {"_index": {"value": "*forecast*"}}}
                ]
            }
        },
        "aggs": {
            "by_hostname": {
                "terms": {"field": "hostname", "size": 100},
                "aggs": {
                    "by_minute": {
                        "date_histogram": {
                            "field": "timestamp",
                            "fixed_interval": "1m",
                            "min_doc_count": 1
                        },
                        "aggs": {
                            "avg_utilization": {"avg": {"field": "utilization_pct"}}
                        }
                    }
                }
            }
        }
    }
    
    try:
        res = client.search(index="telecom-noc-*", body=query)
    except Exception as e:
        logger.error(f"Erro ao consultar OpenSearch: {e}")
        return

    actions = []
    index_name = f"telecom-noc-forecast-{now.strftime('%Y.%m.%d')}"
    
    # Processar cada hostname
    buckets = res.get("aggregations", {}).get("by_hostname", {}).get("buckets", [])
    for host_bucket in buckets:
        hostname = host_bucket["key"]
        time_buckets = host_bucket.get("by_minute", {}).get("buckets", [])
        
        if len(time_buckets) < 2:
            continue
            
        # Preparar dados para regressão (X = minutos relativos, Y = utilização)
        x_data = []
        y_data = []
        base_time = None
        
        for tb in time_buckets:
            ts = tb["key"] # Timestamp epoch em milissegundos
            val = tb.get("avg_utilization", {}).get("value")
            if val is not None:
                if base_time is None:
                    base_time = ts
                x_data.append((ts - base_time) / 60000.0) # Converter para minutos
                y_data.append(val)
                
        # Calcular a linha de tendência (y = mx + b)
        m, b = linear_regression(x_data, y_data)
        
        # Gerar os pontos do futuro
        last_ts = time_buckets[-1]["key"]
        
        # Deletar forecasts antigos para não acumular lixo no futuro imediato
        # Mas para simplificar a POC, apenas injetamos novos pontos
        for minute_ahead in range(1, FORECAST_MINUTES + 1):
            future_ts_ms = last_ts + (minute_ahead * 60000)
            future_x = (future_ts_ms - base_time) / 60000.0
            
            # y = mx + b
            predicted_y = (m * future_x) + b
            
            # Limites realistas de rede
            if predicted_y < 0: predicted_y = 0
            if predicted_y > 100: predicted_y = 100
            
            future_date = datetime.fromtimestamp(future_ts_ms / 1000.0, timezone.utc)
            
            actions.append({
                "_index": index_name,
                "_source": {
                    "timestamp": future_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                    "hostname": hostname,
                    "utilization_pct": round(predicted_y, 2)
                }
            })
            
    if actions:
        success, _ = helpers.bulk(client, actions, raise_on_error=False)
        logger.info(f"Forecast injetado: +{success} pontos no futuro para {len(buckets)} hosts.")

def main():
    logger.info("Iniciando ML Forecaster (Regressão Linear)")
    client = create_client()
    
    while True:
        run_forecast(client)
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
