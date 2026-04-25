# OpenSearch NOC Lab 📡

Uma prova de conceito (PoC) de um pipeline de dados fim-a-fim utilizando **OpenSearch 2.13.0** para monitoramento avançado de Network Operations Center (NOC).

## Funcionalidades
1. **Ingestão em Massa (Bulk API):** Script em Python puro com `tenacity` que injeta telemetria simulada de rede de alta densidade de forma assíncrona.
2. **Machine Learning (RCF):** Modelos de *Random Cut Forest* detectando picos de utilização de rede e surto de logs críticos.
3. **Index State Management (ISM):** Políticas de ciclo de vida ativas (`Hot → Warm → Delete`).
4. **Alerta & Webhooks:** Notificações disparadas para a API oficial do **Telegram** através de um microserviço Python super leve.
5. **Dashboard Executivo:** Painel detalhado de monitoramento (latência, packet loss, top hosts críticos, visões de Discovery).

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
