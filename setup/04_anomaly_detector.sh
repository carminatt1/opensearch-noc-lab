#!/bin/bash
# ===========================================================================
# 04_anomaly_detector.sh — Anomaly Detection com Random Cut Forest
# Cria 2 detectores para métricas vitais do NOC
# ===========================================================================
set -euo pipefail

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

echo "============================================================"
echo " Configurando Anomaly Detectors (Random Cut Forest)"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------
# Detector 1: Pico de Utilização por Hostname
# -----------------------------------------------------------------------
echo "🔧 [1/2] Criando detector: Pico de Utilização..."

DETECTOR1_RESPONSE=$(curl -sf -X POST "${OPENSEARCH_URL}/_plugins/_anomaly_detection/detectors" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "noc-utilization-spike",
  "description": "Detecta picos anômalos de utilização de rede por hostname usando Random Cut Forest",
  "time_field": "timestamp",
  "indices": ["telecom-noc-*"],
  "feature_attributes": [
    {
      "feature_name": "avg_utilization",
      "feature_enabled": true,
      "aggregation_query": {
        "avg_utilization": {
          "avg": {
            "field": "utilization_pct"
          }
        }
      }
    },
    {
      "feature_name": "max_utilization",
      "feature_enabled": true,
      "aggregation_query": {
        "max_utilization": {
          "max": {
            "field": "utilization_pct"
          }
        }
      }
    },
    {
      "feature_name": "avg_latency",
      "feature_enabled": true,
      "aggregation_query": {
        "avg_latency": {
          "avg": {
            "field": "latency_ms"
          }
        }
      }
    }
  ],
  "detection_interval": {
    "period": {
      "interval": 1,
      "unit": "Minutes"
    }
  },
  "window_delay": {
    "period": {
      "interval": 1,
      "unit": "Minutes"
    }
  },
  "shingle_size": 8,
  "category_field": ["hostname"],
  "result_index": "opensearch-ad-plugin-result-noc-utilization"
}')

echo "$DETECTOR1_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DETECTOR1_RESPONSE"
DETECTOR1_ID=$(echo "$DETECTOR1_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['_id'])" 2>/dev/null || echo "")

if [ -n "$DETECTOR1_ID" ]; then
  echo "   ID: $DETECTOR1_ID"
  echo "   Iniciando detector..."
  curl -sf -X POST "${OPENSEARCH_URL}/_plugins/_anomaly_detection/detectors/${DETECTOR1_ID}/_start" \
    -H "Content-Type: application/json" && echo ""
  echo "✅ Detector 1 ativo!"
else
  echo "⚠️  Não foi possível extrair o ID do detector 1. Verifique manualmente."
fi

echo ""

# -----------------------------------------------------------------------
# Detector 2: Surto de Eventos Críticos
# -----------------------------------------------------------------------
echo "🔧 [2/2] Criando detector: Surto de Erros Críticos..."

DETECTOR2_RESPONSE=$(curl -sf -X POST "${OPENSEARCH_URL}/_plugins/_anomaly_detection/detectors" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "noc-critical-surge",
  "description": "Detecta surtos anômalos de eventos CRITICAL usando Random Cut Forest",
  "time_field": "timestamp",
  "indices": ["telecom-noc-*"],
  "feature_attributes": [
    {
      "feature_name": "critical_count",
      "feature_enabled": true,
      "aggregation_query": {
        "critical_count": {
          "filter": {
            "term": {
              "severity": "CRITICAL"
            }
          }
        }
      }
    },
    {
      "feature_name": "avg_packet_loss",
      "feature_enabled": true,
      "aggregation_query": {
        "avg_packet_loss": {
          "avg": {
            "field": "packet_loss_pct"
          }
        }
      }
    }
  ],
  "filter_query": {
    "match_all": {}
  },
  "detection_interval": {
    "period": {
      "interval": 2,
      "unit": "Minutes"
    }
  },
  "window_delay": {
    "period": {
      "interval": 1,
      "unit": "Minutes"
    }
  },
  "shingle_size": 4,
  "result_index": "opensearch-ad-plugin-result-noc-critical"
}')

echo "$DETECTOR2_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DETECTOR2_RESPONSE"
DETECTOR2_ID=$(echo "$DETECTOR2_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['_id'])" 2>/dev/null || echo "")

if [ -n "$DETECTOR2_ID" ]; then
  echo "   ID: $DETECTOR2_ID"
  echo "   Iniciando detector..."
  curl -sf -X POST "${OPENSEARCH_URL}/_plugins/_anomaly_detection/detectors/${DETECTOR2_ID}/_start" \
    -H "Content-Type: application/json" && echo ""
  echo "✅ Detector 2 ativo!"
else
  echo "⚠️  Não foi possível extrair o ID do detector 2. Verifique manualmente."
fi

echo ""
echo "============================================================"
echo " Anomaly Detection configurada!"
echo " Acesse: http://localhost:5601 → Anomaly Detection"
echo "============================================================"
