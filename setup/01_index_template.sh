#!/bin/bash
# ===========================================================================
# 01_index_template.sh — Index Template para telecom-noc-*
# Tipagem estrita com mappings otimizados para agregações e Data Science
# ===========================================================================
set -euo pipefail

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

echo "🔧 Criando Index Template: telecom-noc-template..."

curl -sf -X PUT "${OPENSEARCH_URL}/_index_template/telecom-noc-template" \
  -H "Content-Type: application/json" \
  -d '{
  "index_patterns": ["telecom-noc-*"],
  "priority": 100,
  "template": {
    "settings": {
      "index": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "refresh_interval": "5s",
        "codec": "best_compression",
        "translog": {
          "durability": "async",
          "sync_interval": "5s",
          "flush_threshold_size": "512mb"
        },
        "merge": {
          "scheduler": {
            "max_thread_count": 1
          }
        }
      }
    },
    "mappings": {
      "dynamic": "strict",
      "properties": {
        "timestamp": {
          "type": "date",
          "format": "strict_date_optional_time||epoch_millis"
        },
        "hostname": {
          "type": "keyword",
          "doc_values": true
        },
        "interface": {
          "type": "keyword",
          "doc_values": true
        },
        "region": {
          "type": "keyword",
          "doc_values": true
        },
        "severity": {
          "type": "keyword",
          "doc_values": true
        },
        "message": {
          "type": "text",
          "analyzer": "standard",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "utilization_pct": {
          "type": "float",
          "doc_values": true
        },
        "latency_ms": {
          "type": "float",
          "doc_values": true
        },
        "packet_loss_pct": {
          "type": "float",
          "doc_values": true
        }
      }
    }
  }
}' && echo ""

echo "✅ Index Template criado com sucesso!"
echo ""

# Verificar
echo "📋 Verificando template..."
curl -sf "${OPENSEARCH_URL}/_index_template/telecom-noc-template" | python3 -m json.tool 2>/dev/null || \
  curl -sf "${OPENSEARCH_URL}/_index_template/telecom-noc-template"
echo ""
