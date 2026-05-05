#!/usr/bin/env python3
"""
Log Pattern Analysis — Detecção de Padrões e Novidades em Logs NOC.

Agrupa mensagens de log por template (tokenização simples), conta ocorrências
por hostname/severidade e detecta padrões novos não vistos anteriormente.
Resultados escritos em 'noc-patterns-YYYY.MM.dd' para visualização no dashboard.
"""
import os
import re
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from opensearchpy import OpenSearch, NotFoundError

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "5"))
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "60"))
KNOWN_INDEX = "noc-patterns-known"
PATTERN_PREFIX = "noc-patterns"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("log-pattern-analysis")

_NUMBER_RE = re.compile(r"\b\d+(\.\d+)?\b")
_IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
_HEX_RE = re.compile(r"\b[0-9a-fA-F]{4,}\b")


def normalize(message: str) -> str:
    """Extract a template from a raw log message."""
    s = _IP_RE.sub("{IP}", message)
    s = _HEX_RE.sub("{HEX}", s)
    s = _NUMBER_RE.sub("{N}", s)
    return s.strip()


def create_client():
    return OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        use_ssl=False,
        verify_certs=False,
        timeout=30,
    )


def ensure_known_index(client: OpenSearch):
    if not client.indices.exists(index=KNOWN_INDEX):
        client.indices.create(
            index=KNOWN_INDEX,
            body={
                "mappings": {
                    "properties": {
                        "pattern": {"type": "keyword"},
                        "first_seen": {"type": "date"},
                    }
                }
            },
        )
        logger.info("Created index %s", KNOWN_INDEX)


def load_known_patterns(client: OpenSearch) -> set:
    try:
        resp = client.search(
            index=KNOWN_INDEX,
            body={"size": 10000, "query": {"match_all": {}}, "_source": ["pattern"]},
        )
        return {hit["_source"]["pattern"] for hit in resp["hits"]["hits"]}
    except NotFoundError:
        return set()


def save_known_patterns(client: OpenSearch, new_patterns: set, now: datetime):
    for pattern in new_patterns:
        doc_id = re.sub(r"\W+", "_", pattern)[:200]
        client.index(
            index=KNOWN_INDEX,
            id=doc_id,
            body={"pattern": pattern, "first_seen": now.isoformat()},
        )


def fetch_recent_logs(client: OpenSearch, since: datetime):
    resp = client.search(
        index="telecom-noc-*",
        body={
            "size": 5000,
            "query": {
                "bool": {
                    "must": [
                        {"range": {"timestamp": {"gte": since.isoformat()}}},
                        {"exists": {"field": "message"}},
                    ]
                }
            },
            "_source": ["message", "hostname", "severity", "timestamp"],
        },
    )
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def analyse(docs: list, known: set, now: datetime) -> list:
    """Group docs by (pattern, hostname, severity) and tag new patterns."""
    counts: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    pattern_times: dict = defaultdict(list)

    for doc in docs:
        pattern = normalize(doc.get("message", ""))
        host = doc.get("hostname", "unknown")
        sev = doc.get("severity", "unknown")
        counts[pattern][host][sev] += 1
        pattern_times[pattern].append(doc.get("timestamp", now.isoformat()))

    results = []
    for pattern, hosts in counts.items():
        is_new = pattern not in known
        for host, severities in hosts.items():
            for severity, count in severities.items():
                results.append(
                    {
                        "timestamp": now.isoformat(),
                        "pattern": pattern,
                        "hostname": host,
                        "severity": severity,
                        "count": count,
                        "is_new": is_new,
                        "first_occurrence": min(pattern_times[pattern]),
                        "last_occurrence": max(pattern_times[pattern]),
                    }
                )
    return results


def write_results(client: OpenSearch, results: list, now: datetime):
    if not results:
        return
    index = f"{PATTERN_PREFIX}-{now.strftime('%Y.%m.%d')}"
    actions = [{"_index": index, "_source": doc} for doc in results]
    from opensearchpy import helpers
    ok, errors = helpers.bulk(client, actions, stats_only=False, raise_on_error=False)
    logger.info("Indexed %d pattern docs to %s (%d errors)", ok, index, len(errors))


def run_once(client: OpenSearch):
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=LOOKBACK_MINUTES)

    ensure_known_index(client)
    known = load_known_patterns(client)

    docs = fetch_recent_logs(client, since)
    logger.info("Fetched %d log docs from last %d min", len(docs), LOOKBACK_MINUTES)

    if not docs:
        return

    results = analyse(docs, known, now)

    new_patterns = {r["pattern"] for r in results if r["is_new"]}
    if new_patterns:
        logger.warning("NEW patterns detected: %d", len(new_patterns))
        for p in new_patterns:
            logger.warning("  → %s", p)
        save_known_patterns(client, new_patterns, now)

    write_results(client, results, now)
    logger.info(
        "Cycle done — %d pattern groups, %d new",
        len(results),
        len(new_patterns),
    )


def main():
    client = create_client()
    logger.info(
        "Log Pattern Analysis started (lookback=%dmin, interval=%ds)",
        LOOKBACK_MINUTES,
        INTERVAL_SECONDS,
    )
    while True:
        try:
            run_once(client)
        except Exception as exc:
            logger.error("Cycle error: %s", exc)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
