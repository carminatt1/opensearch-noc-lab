#!/usr/bin/env python3
"""
Webhook Relay: OpenSearch Alerting → Telegram

Recebe POST do OpenSearch Alerting e encaminha para o Telegram via Bot API.
Roda como microserviço leve usando apenas stdlib Python.

Variáveis de ambiente:
    TELEGRAM_BOT_TOKEN — Token recebido do @BotFather (ex: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)
    TELEGRAM_CHAT_ID   — Seu ID de chat (ex: 123456789)
    WEBHOOK_PORT       — Porta do servidor (padrão: 8089)
"""

import http.server
import json
import logging
import os
import sys
import urllib.parse
import urllib.request
import ssl
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8089"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("webhook-telegram")


# ---------------------------------------------------------------------------
# Formatação e Envio
# ---------------------------------------------------------------------------
def format_telegram_message(payload: dict) -> str:
    """Formata o payload em mensagem legível (HTML) para o Telegram."""
    monitor_name = payload.get("monitor_name", payload.get("monitor", {}).get("name", "Monitor"))
    trigger_name = payload.get("trigger_name", payload.get("trigger", {}).get("name", "Trigger"))
    severity = payload.get("severity", "N/A")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Usamos emojis e formatação HTML do Telegram (<b>, <i>, <code>)
    msg_lines = [
        "🚨 <b>ALERTA OpenSearch NOC</b> 🚨",
        "",
        f"📌 <b>Monitor:</b> {monitor_name}",
        f"⚡ <b>Trigger:</b> {trigger_name}",
        f"🔴 <b>Severidade:</b> {severity}",
        f"🕐 <b>Hora:</b> {now}",
    ]

    period_start = payload.get("period_start", "")
    if period_start:
        msg_lines.append(f"📅 <b>Período:</b> {period_start} → {payload.get('period_end', '')}")

    custom_msg = payload.get("message", "")
    if custom_msg:
        msg_lines.append("")
        msg_lines.append(f"💬 <i>{custom_msg}</i>")

    msg_lines.extend([
        "",
        "🔗 <a href='http://localhost:5601/app/dashboards'>Dashboard</a>"
    ])

    return "\n".join(msg_lines)


def send_telegram(message: str) -> bool:
    """Envia mensagem para a API do Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        # Contexto SSL para não falhar caso haja problemas locais de certificado
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            logger.info("Telegram enviado com sucesso! Status: %d", resp.status)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("Erro na API do Telegram (%d): %s", e.code, body)
        return False
    except Exception as e:
        logger.error("Falha ao conectar com Telegram: %s", e)
        return False


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------
class WebhookHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            payload = {"message": raw_body.decode("utf-8", errors="replace")}

        logger.info("Webhook recebido: %s", json.dumps(payload, default=str)[:300])

        message = format_telegram_message(payload)
        success = send_telegram(message)

        status = 200 if success else 502
        response = json.dumps({"success": success})
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode("utf-8"))

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy", "service": "webhook-telegram"}).encode("utf-8"))

    def log_message(self, format, *args):
        logger.info("%s %s", self.address_string(), format % args)


def main():
    logger.info("=" * 50)
    logger.info("Webhook Relay: OpenSearch → Telegram")
    logger.info("=" * 50)
    
    token_display = TELEGRAM_BOT_TOKEN[:10] + "..." if TELEGRAM_BOT_TOKEN else "NÃO CONFIGURADO"
    logger.info("Bot Token: %s", token_display)
    logger.info("Chat ID:   %s", TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else "NÃO CONFIGURADO")
    logger.info("Porta:     %d", WEBHOOK_PORT)
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️  As variáveis TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID não estão configuradas!")
        logger.warning("O relay vai funcionar, mas não conseguirá enviar mensagens.")

    server = http.server.HTTPServer(("0.0.0.0", WEBHOOK_PORT), WebhookHandler)
    logger.info("Servidor ouvindo em http://0.0.0.0:%d", WEBHOOK_PORT)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Encerrando...")
        server.server_close()

if __name__ == "__main__":
    main()
