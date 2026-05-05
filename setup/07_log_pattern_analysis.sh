#!/bin/bash
# ===========================================================================
# 07_log_pattern_analysis.sh — Log Pattern Analysis: índice + alerta
# Cria template para noc-patterns-* e monitor de alerta para novos padrões
# ===========================================================================
set -euo pipefail

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

echo "============================================================"
echo " 🧠 Configurando Log Pattern Analysis"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------
# 1. Index Template para noc-patterns-*
# -----------------------------------------------------------------------
echo "[1/3] 📋 Criando index template: noc-patterns-*..."

curl -sf -X PUT "${OPENSEARCH_URL}/_index_template/noc-patterns-template" \
  -H "Content-Type: application/json" \
  -d '{
  "index_patterns": ["noc-patterns-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "timestamp":        { "type": "date" },
        "pattern":          { "type": "keyword" },
        "hostname":         { "type": "keyword" },
        "severity":         { "type": "keyword" },
        "count":            { "type": "integer" },
        "is_new":           { "type": "boolean" },
        "first_occurrence": { "type": "date" },
        "last_occurrence":  { "type": "date" }
      }
    }
  }
}' > /dev/null && echo "   ✅ Template criado!" || echo "   ⚠️  Verifique manualmente"

echo ""

# -----------------------------------------------------------------------
# 2. Index Template para noc-patterns-known
# -----------------------------------------------------------------------
echo "[2/3] 📋 Criando index template: noc-patterns-known..."

curl -sf -X PUT "${OPENSEARCH_URL}/_index_template/noc-patterns-known-template" \
  -H "Content-Type: application/json" \
  -d '{
  "index_patterns": ["noc-patterns-known"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "pattern":    { "type": "keyword" },
        "first_seen": { "type": "date" }
      }
    }
  }
}' > /dev/null && echo "   ✅ Template criado!" || echo "   ⚠️  Verifique manualmente"

echo ""

# -----------------------------------------------------------------------
# 3. Monitor: Novos Padrões de Log Detectados
# -----------------------------------------------------------------------
echo "[3/3] 🚨 Criando Monitor: Novos Padrões de Log..."

DEST_ID="telegram-webhook"

curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -d "{
  \"name\": \"NOC - Novos Padrões de Log Detectados\",
  \"type\": \"monitor\",
  \"monitor_type\": \"query_level_monitor\",
  \"enabled\": true,
  \"schedule\": {
    \"period\": {
      \"interval\": 5,
      \"unit\": \"MINUTES\"
    }
  },
  \"inputs\": [
    {
      \"search\": {
        \"indices\": [\"noc-patterns-*\"],
        \"query\": {
          \"size\": 0,
          \"query\": {
            \"bool\": {
              \"filter\": [
                { \"term\": { \"is_new\": true } },
                { \"range\": { \"timestamp\": { \"gte\": \"now-10m\" } } }
              ]
            }
          },
          \"aggs\": {
            \"new_pattern_count\": {
              \"cardinality\": { \"field\": \"pattern\" }
            }
          }
        }
      }
    }
  ],
  \"triggers\": [
    {
      \"query_level_trigger\": {
        \"name\": \"Pelo menos 1 novo padrão de log\",
        \"severity\": \"2\",
        \"condition\": {
          \"script\": {
            \"source\": \"ctx.results[0].aggregations.new_pattern_count.value > 0\",
            \"lang\": \"painless\"
          }
        },
        \"actions\": [
          {
            \"name\": \"Enviar Telegram - Novo Padrão\",
            \"destination_id\": \"${DEST_ID}\",
            \"message_template\": {
              \"source\": \"{\\\"monitor_name\\\": \\\"{{ctx.monitor.name}}\\\", \\\"trigger_name\\\": \\\"{{ctx.trigger.name}}\\\", \\\"severity\\\": \\\"WARNING\\\", \\\"period_start\\\": \\\"{{ctx.periodStart}}\\\", \\\"period_end\\\": \\\"{{ctx.periodEnd}}\\\", \\\"message\\\": \\\"{{ctx.results.0.aggregations.new_pattern_count.value}} novo(s) padrao(es) de log detectado(s) nos ultimos 10min — verifique noc-patterns-* no Dashboards\\\"}\"
            },
            \"throttle_enabled\": true,
            \"throttle\": {
              \"value\": 15,
              \"unit\": \"MINUTES\"
            }
          }
        ]
      }
    }
  ]
}" > /dev/null 2>&1 && echo "   ✅ Monitor criado!" || echo "   ⚠️  Verifique manualmente"

echo ""
echo "============================================================"
echo " ✅ Log Pattern Analysis configurado!"
echo ""
echo " Scripts de apoio:"
echo "    scripts/log_pattern_analysis.py"
echo "    → Executa em loop (INTERVAL_SECONDS=60)"
echo "    → Escreve em noc-patterns-YYYY.MM.dd"
echo "    → Detecta padrões novos (is_new=true)"
echo ""
echo " Monitor: verifica novos padrões a cada 5min"
echo " Alerta enviado ao Telegram quando is_new=true"
echo "============================================================"
