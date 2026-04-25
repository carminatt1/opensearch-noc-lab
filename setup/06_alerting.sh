#!/bin/bash
# ===========================================================================
# 06_alerting.sh — Alertas OpenSearch → Telegram
# ===========================================================================
set -euo pipefail

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"
WEBHOOK_RELAY_URL="${WEBHOOK_RELAY_URL:-http://webhook-telegram:8089}"

echo "============================================================"
echo " 📱 Configurando Alertas → Telegram"
echo "============================================================"
echo ""

# -----------------------------------------------------------------------
# 1. Criar Destination (Notifications API)
# -----------------------------------------------------------------------
echo "[1/3] 📡 Criando Notification Config: Telegram Webhook..."

DEST_RESP=$(curl -s -X POST "${OPENSEARCH_URL}/_plugins/_notifications/configs" \
  -H "Content-Type: application/json" \
  -d "{
  \"config_id\": \"telegram-webhook\",
  \"config\": {
    \"name\": \"Telegram Webhook\",
    \"description\": \"Alertas via Telegram\",
    \"config_type\": \"webhook\",
    \"is_enabled\": true,
    \"webhook\": {
      \"url\": \"${WEBHOOK_RELAY_URL}/\"
    }
  }
}" 2>&1)

DEST_ID=$(echo "$DEST_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('config_id',''))" 2>/dev/null || echo "")
if [ -n "$DEST_ID" ] && [ "$DEST_ID" != "" ]; then
  echo "   ✅ Notification Config criada: ${DEST_ID}"
else
  echo "   ⚠️  Resposta: $(echo "$DEST_RESP" | head -c 300)"
  # Se já existir, forçar o ID para telegram-webhook
  DEST_ID="telegram-webhook"
fi
echo ""

# -----------------------------------------------------------------------
# 2. Monitor: Utilização Crítica (>85%)
# -----------------------------------------------------------------------
echo "[2/3] 🔴 Criando Monitor: Utilização Crítica..."

curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -d "{
  \"name\": \"NOC - Utilização Crítica (>85%)\",
  \"type\": \"monitor\",
  \"monitor_type\": \"query_level_monitor\",
  \"enabled\": true,
  \"schedule\": {
    \"period\": {
      \"interval\": 1,
      \"unit\": \"MINUTES\"
    }
  },
  \"inputs\": [
    {
      \"search\": {
        \"indices\": [\"telecom-noc-*\"],
        \"query\": {
          \"size\": 0,
          \"query\": {
            \"bool\": {
              \"filter\": [
                {
                  \"range\": {
                    \"timestamp\": {
                      \"gte\": \"now-2m\",
                      \"lte\": \"now\"
                    }
                  }
                }
              ]
            }
          },
          \"aggs\": {
            \"avg_utilization\": {
              \"avg\": {
                \"field\": \"utilization_pct\"
              }
            },
            \"max_utilization\": {
              \"max\": {
                \"field\": \"utilization_pct\"
              }
            }
          }
        }
      }
    }
  ],
  \"triggers\": [
    {
      \"query_level_trigger\": {
        \"name\": \"Utilização acima de 85%\",
        \"severity\": \"1\",
        \"condition\": {
          \"script\": {
            \"source\": \"ctx.results[0].aggregations.avg_utilization.value > 85\",
            \"lang\": \"painless\"
          }
        },
        \"actions\": [
          {
            \"name\": \"Enviar Telegram\",
            \"destination_id\": \"${DEST_ID}\",
            \"message_template\": {
              \"source\": \"{\\\"monitor_name\\\": \\\"{{ctx.monitor.name}}\\\", \\\"trigger_name\\\": \\\"{{ctx.trigger.name}}\\\", \\\"severity\\\": \\\"{{ctx.trigger.severity}}\\\", \\\"period_start\\\": \\\"{{ctx.periodStart}}\\\", \\\"period_end\\\": \\\"{{ctx.periodEnd}}\\\", \\\"message\\\": \\\"Utilização média: {{ctx.results.0.aggregations.avg_utilization.value}}% | Máx: {{ctx.results.0.aggregations.max_utilization.value}}%\\\"}\"
            },
            \"throttle_enabled\": true,
            \"throttle\": {
              \"value\": 5,
              \"unit\": \"MINUTES\"
            }
          }
        ]
      }
    }
  ]
}" > /dev/null 2>&1 && echo "   ✅ Monitor criado!" || echo "   ⚠️  Verifique manualmente"

echo ""

# -----------------------------------------------------------------------
# 3. Monitor: Surto de Eventos CRITICAL
# -----------------------------------------------------------------------
echo "[3/3] 🚨 Criando Monitor: Surto de Eventos CRITICAL..."

curl -s -X POST "${OPENSEARCH_URL}/_plugins/_alerting/monitors" \
  -H "Content-Type: application/json" \
  -d "{
  \"name\": \"NOC - Surto de Eventos CRITICAL\",
  \"type\": \"monitor\",
  \"monitor_type\": \"query_level_monitor\",
  \"enabled\": true,
  \"schedule\": {
    \"period\": {
      \"interval\": 2,
      \"unit\": \"MINUTES\"
    }
  },
  \"inputs\": [
    {
      \"search\": {
        \"indices\": [\"telecom-noc-*\"],
        \"query\": {
          \"size\": 0,
          \"query\": {
            \"bool\": {
              \"filter\": [
                {
                  \"term\": {
                    \"severity\": \"CRITICAL\"
                  }
                },
                {
                  \"range\": {
                    \"timestamp\": {
                      \"gte\": \"now-5m\",
                      \"lte\": \"now\"
                    }
                  }
                }
              ]
            }
          },
          \"aggs\": {
            \"critical_count\": {
              \"value_count\": {
                \"field\": \"severity\"
              }
            },
            \"avg_packet_loss\": {
              \"avg\": {
                \"field\": \"packet_loss_pct\"
              }
            }
          }
        }
      }
    }
  ],
  \"triggers\": [
    {
      \"query_level_trigger\": {
        \"name\": \"Mais de 10 eventos CRITICAL em 5min\",
        \"severity\": \"1\",
        \"condition\": {
          \"script\": {
            \"source\": \"ctx.results[0].aggregations.critical_count.value > 10\",
            \"lang\": \"painless\"
          }
        },
        \"actions\": [
          {
            \"name\": \"Enviar Telegram CRITICAL\",
            \"destination_id\": \"${DEST_ID}\",
            \"message_template\": {
              \"source\": \"{\\\"monitor_name\\\": \\\"{{ctx.monitor.name}}\\\", \\\"trigger_name\\\": \\\"{{ctx.trigger.name}}\\\", \\\"severity\\\": \\\"CRITICAL\\\", \\\"period_start\\\": \\\"{{ctx.periodStart}}\\\", \\\"period_end\\\": \\\"{{ctx.periodEnd}}\\\", \\\"message\\\": \\\"{{ctx.results.0.aggregations.critical_count.value}} eventos CRITICAL nos ultimos 5min | Packet Loss medio: {{ctx.results.0.aggregations.avg_packet_loss.value}}%\\\"}\"
            },
            \"throttle_enabled\": true,
            \"throttle\": {
              \"value\": 10,
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
echo " ✅ Alertas configurados!"
echo "============================================================"
echo ""
echo " 📱 Monitors criados:"
echo "    1. Utilização Crítica (>85%) — verifica a cada 1min"
echo "    2. Surto CRITICAL (>10 em 5min) — verifica a cada 2min"
echo ""
echo " ⏱️  Throttle: máx 1 alerta a cada 5-10min para não lotar"
echo ""
echo " 🔗 Gerenciar alertas:"
echo "    http://localhost:5601/app/alerting"
echo "============================================================"
