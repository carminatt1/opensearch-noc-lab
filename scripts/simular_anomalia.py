#!/usr/bin/env python3
"""
Simulador de Anomalia — Injeta uma rajada de erros CRITICAL no OpenSearch
para forçar o disparo dos detectores RCF e envio de alerta via Telegram.
"""

import datetime
import random
import time
from opensearchpy import OpenSearch, helpers

# Configuração
HOST = 'localhost'
PORT = 9200
INDEX_PREFIX = 'telecom-noc-'
ANOMALY_DURATION_SEC = 30
DOCS_PER_SEC = 20

# Inicializa cliente OpenSearch
client = OpenSearch(
    hosts=[{'host': HOST, 'port': PORT}],
    http_compress=True
)

def generate_anomaly_docs():
    """Gera documentos focados em simular uma queda de link em SP-CORE-101."""
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y.%m.%d")
    index_name = f"{INDEX_PREFIX}{today}"
    
    docs = []
    for _ in range(DOCS_PER_SEC):
        doc = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "hostname": "BR-SP-CORE-101",
            "region": "BR-SP",
            "interface": "eth0",
            "severity": "CRITICAL",
            "message": "ANOMALIA INJETADA: BGP Peer Down / Link Failure",
            "utilization_pct": round(random.uniform(95.0, 99.9), 2),  # Pico de uso
            "latency_ms": random.randint(500, 1500),  # Latência absurda
            "packet_loss_pct": round(random.uniform(50.0, 100.0), 2)  # Perda de pacote maciça
        }
        docs.append({
            "_index": index_name,
            "_source": doc
        })
    return docs

if __name__ == "__main__":
    print("============================================================")
    print(" ⚠️  INICIANDO SIMULAÇÃO DE ANOMALIA (QUEDA DE LINK)")
    print("============================================================")
    print(f"Alvo: BR-SP-CORE-101 | Duração: {ANOMALY_DURATION_SEC}s")
    
    start_time = time.time()
    total_injected = 0
    
    try:
        while (time.time() - start_time) < ANOMALY_DURATION_SEC:
            docs = generate_anomaly_docs()
            helpers.bulk(client, docs, request_timeout=10)
            total_injected += len(docs)
            print(f"🔥 Injetados {total_injected} erros CRITICAL...")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nSimulação abortada pelo usuário.")
        
    print("============================================================")
    print(f" ✅ Simulação concluída. Total de anomalias: {total_injected}")
    print(" 💡 Aguarde ~2 minutos. O Random Cut Forest precisa analisar a")
    print("    janela de tempo, e logo após o Telegram irá apitar!")
    print("============================================================")
