#!/bin/bash
# ===========================================================================
# 02_ism_policy.sh — Index State Management para rotatividade dos dados
# Hot (0-7d) → Warm (7-30d) → Delete (30d+)
# ===========================================================================
set -euo pipefail

OPENSEARCH_URL="${OPENSEARCH_URL:-http://localhost:9200}"

echo "🔧 Criando ISM Policy: telecom-noc-policy..."

curl -sf -X PUT "${OPENSEARCH_URL}/_plugins/_ism/policies/telecom-noc-policy" \
  -H "Content-Type: application/json" \
  -d '{
  "policy": {
    "description": "Política de ciclo de vida para índices telecom-noc-*. Hot → Warm → Delete.",
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [
          {
            "rollover": {
              "min_doc_count": 100000,
              "min_index_age": "1d"
            }
          }
        ],
        "transitions": [
          {
            "state_name": "warm",
            "conditions": {
              "min_index_age": "7d"
            }
          }
        ]
      },
      {
        "name": "warm",
        "actions": [
          {
            "force_merge": {
              "max_num_segments": 1
            }
          },
          {
            "read_only": {}
          }
        ],
        "transitions": [
          {
            "state_name": "delete",
            "conditions": {
              "min_index_age": "30d"
            }
          }
        ]
      },
      {
        "name": "delete",
        "actions": [
          {
            "notification": {
              "destination": {
                "custom_webhook": {
                  "url": "http://localhost:9200"
                }
              },
              "message_template": {
                "source": "Índice {{ctx.index}} será excluído por retenção de 30 dias."
              }
            }
          },
          {
            "delete": {}
          }
        ],
        "transitions": []
      }
    ],
    "ism_template": [
      {
        "index_patterns": ["telecom-noc-*"],
        "priority": 100
      }
    ]
  }
}' && echo ""

echo "✅ ISM Policy criada com sucesso!"
echo ""

# Verificar
echo "📋 Verificando policy..."
curl -sf "${OPENSEARCH_URL}/_plugins/_ism/policies/telecom-noc-policy" | python3 -m json.tool 2>/dev/null || \
  curl -sf "${OPENSEARCH_URL}/_plugins/_ism/policies/telecom-noc-policy"
echo ""
