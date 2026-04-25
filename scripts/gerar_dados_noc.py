#!/usr/bin/env python3
"""
Gerador de dados NOC Telecom para OpenSearch.

Simula eventos de rede com anomalias periódicas para alimentar
Anomaly Detection (Random Cut Forest) e Dashboards analíticos.

Uso:
    python gerar_dados_noc.py
    OPENSEARCH_HOST=opensearch-node OPENSEARCH_PORT=9200 python gerar_dados_noc.py
"""

import os
import sys
import json
import random
import time
import logging
from datetime import datetime, timezone
from typing import Generator

from opensearchpy import OpenSearch, helpers, ConnectionError, TransportError
from tenacity import retry, stop_after_attempt, wait_exponential, before_log

# ---------------------------------------------------------------------------
# Configuração via variáveis de ambiente
# ---------------------------------------------------------------------------
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
INDEX_PREFIX = os.getenv("INDEX_PREFIX", "telecom-noc")
BULK_SIZE = int(os.getenv("BULK_SIZE", "10"))
INTERVAL_SECONDS = float(os.getenv("INTERVAL_SECONDS", "1.0"))
ANOMALY_EVERY_N = int(os.getenv("ANOMALY_EVERY_N", "20"))

# ---------------------------------------------------------------------------
# Logging estruturado
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("noc-generator")

# ---------------------------------------------------------------------------
# Constantes de geração de dados
# ---------------------------------------------------------------------------
HOSTNAMES = [f"BR-SP-CORE-{i}" for i in range(100, 106)]
INTERFACES = ["GigabitEthernet0/0", "GigabitEthernet0/1", "TenGigE1/0", "TenGigE1/1", "Loopback0"]
REGIONS = ["SP-Capital", "SP-Interior", "RJ-Capital", "MG-Capital", "PR-Capital", "RS-Capital"]
SEVERITIES_NORMAL = ["INFO", "WARNING"]
MESSAGES_NORMAL = [
    "Normal traffic",
    "Routine health check passed",
    "Interface status UP",
    "BGP session established",
    "SNMP poll completed",
]
MESSAGES_CRITICAL = [
    "ANOMALY: Traffic Spike Detected",
    "ANOMALY: High packet loss on trunk",
    "ANOMALY: CPU threshold exceeded",
    "ANOMALY: Memory exhaustion warning",
    "ANOMALY: Link flapping detected",
]


class NOCEventGenerator:
    """Gerador de eventos NOC com anomalias periódicas controladas."""

    def __init__(self, anomaly_every_n: int = ANOMALY_EVERY_N):
        self._counter = 0
        self._anomaly_every_n = anomaly_every_n

    def generate(self) -> dict:
        """Gera um único evento NOC."""
        self._counter += 1
        is_anomaly = self._counter % self._anomaly_every_n == 0

        if is_anomaly:
            utilization = round(random.uniform(88.0, 100.0), 2)
            latency = round(random.uniform(200.0, 800.0), 2)
            packet_loss = round(random.uniform(5.0, 25.0), 2)
            severity = "CRITICAL"
            message = random.choice(MESSAGES_CRITICAL)
        else:
            utilization = round(random.uniform(10.0, 45.0), 2)
            latency = round(random.uniform(1.0, 50.0), 2)
            packet_loss = round(random.uniform(0.0, 0.5), 2)
            severity = random.choice(SEVERITIES_NORMAL)
            message = random.choice(MESSAGES_NORMAL)

        # Timestamp timezone-aware (UTC) — sem DeprecationWarning
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        return {
            "timestamp": timestamp,
            "hostname": random.choice(HOSTNAMES),
            "interface": random.choice(INTERFACES),
            "region": random.choice(REGIONS),
            "severity": severity,
            "message": message,
            "utilization_pct": utilization,
            "latency_ms": latency,
            "packet_loss_pct": packet_loss,
        }

    def generate_batch(self, size: int) -> Generator[dict, None, None]:
        """Gera um batch de ações para bulk indexing."""
        # Índice diário para facilitar rotatividade ISM
        today = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        index_name = f"{INDEX_PREFIX}-{today}"

        for _ in range(size):
            doc = self.generate()
            yield {
                "_index": index_name,
                "_source": doc,
            }


# ---------------------------------------------------------------------------
# Conexão OpenSearch com retentativas
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    before=before_log(logger, logging.WARNING),
    reraise=True,
)
def create_client() -> OpenSearch:
    """Cria e valida conexão com o OpenSearch."""
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        use_ssl=False,
        verify_certs=False,
        timeout=30,
        max_retries=3,
        retry_on_timeout=True,
    )
    # Validar que o cluster está respondendo
    health = client.cluster.health()
    status = health.get("status", "unknown")
    logger.info(
        "Cluster conectado: name=%s, status=%s, nodes=%s",
        health.get("cluster_name"),
        status,
        health.get("number_of_nodes"),
    )
    if status == "red":
        raise ConnectionError("Cluster em estado RED — aguardando recuperação")
    return client


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    before=before_log(logger, logging.WARNING),
    reraise=True,
)
def send_bulk(client: OpenSearch, actions: list) -> dict:
    """Envia batch via Bulk API com retentativas."""
    success, errors = helpers.bulk(
        client,
        actions,
        raise_on_error=False,
        raise_on_exception=False,
        max_retries=3,
        request_timeout=60,
    )
    if errors:
        error_count = len(errors) if isinstance(errors, list) else 0
        logger.error("Bulk parcialmente falhou: %d erros de %d docs", error_count, success + error_count)
        for err in errors[:5]:  # Log apenas primeiros 5 erros
            logger.error("  Erro: %s", json.dumps(err, default=str)[:200])
    return {"success": success, "errors": len(errors) if isinstance(errors, list) else 0}


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("NOC Data Generator — OpenSearch Lab")
    logger.info("=" * 60)
    logger.info("Host: %s:%s | Índice: %s-* | Bulk: %d docs | Intervalo: %.1fs",
                OPENSEARCH_HOST, OPENSEARCH_PORT, INDEX_PREFIX, BULK_SIZE, INTERVAL_SECONDS)

    client = create_client()
    generator = NOCEventGenerator(anomaly_every_n=ANOMALY_EVERY_N)

    total_sent = 0
    total_errors = 0
    start_time = time.monotonic()

    try:
        while True:
            # Gerar batch
            actions = list(generator.generate_batch(BULK_SIZE))

            # Enviar via Bulk API
            result = send_bulk(client, actions)
            total_sent += result["success"]
            total_errors += result["errors"]

            # Estatísticas
            elapsed = time.monotonic() - start_time
            rate = total_sent / elapsed if elapsed > 0 else 0

            # Log com indicador visual de anomalia
            has_anomaly = any(
                a["_source"]["severity"] == "CRITICAL" for a in actions
            )
            marker = " 🔴 ANOMALIA DETECTADA" if has_anomaly else ""

            logger.info(
                "Bulk OK: +%d docs (total: %d | erros: %d | rate: %.1f docs/s)%s",
                result["success"], total_sent, total_errors, rate, marker,
            )

            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        elapsed = time.monotonic() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("Geração encerrada pelo usuário")
        logger.info("Total enviado: %d docs | Erros: %d | Tempo: %.0fs", total_sent, total_errors, elapsed)
        logger.info("=" * 60)
    except Exception as e:
        logger.exception("Erro fatal na geração: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
