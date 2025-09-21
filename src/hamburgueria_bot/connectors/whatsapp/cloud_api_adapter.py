
"""Adapter oficial do WhatsApp Cloud API para envio/recebimento."""
from __future__ import annotations
import hmac, hashlib
import httpx
from kink import di
from ...core.settings import Settings
from ...ports.interfaces import MensagemEntradaDTO, MensagemSaidaDTO, EntregaDTO

class WhatsAppCloudAdapter:
    """Adapter para WhatsApp Cloud API."""
    def __init__(self, settings: Settings | None = None):
        self.s = settings or di[Settings]

    # --- Ingress helpers ---
    def verify_signature(self, body_bytes: bytes, header_signature: str | None) -> bool:
        """Valida assinatura HMAC enviada pela Meta via X-Hub-Signature-256."""
        if not header_signature:
            return False
        try:
            algo, signature = header_signature.split("=", 1)
            if algo.lower() != "sha256":
                return False
        except ValueError:
            return False
        mac = hmac.new(self.s.app_secret.encode(), msg=body_bytes, digestmod=hashlib.sha256)
        return hmac.compare_digest(mac.hexdigest(), signature)

    def normalize_incoming(self, raw: dict) -> MensagemEntradaDTO:
        """Normaliza payload do webhook em MensagemEntradaDTO."""
        entry = raw["entry"][0]["changes"][0]["value"]["messages"][0]
        wa_id = raw["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        return MensagemEntradaDTO(
            wa_id=wa_id,
            provider_message_id=entry["id"],
            texto=entry.get("text", {}).get("body", ""),
            timestamp=int(entry["timestamp"]),
            conversation_id=wa_id,
        )

    # --- Egress ---
    def send(self, msg: MensagemSaidaDTO) -> EntregaDTO:
        """Envia mensagem de texto simples via Graph API."""
        url = f"https://graph.facebook.com/v20.0/{self.s.whatsapp_phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": msg.wa_id,
            "type": "text",
            "text": {"body": msg.texto},
        }
        headers = {"Authorization": f"Bearer {self.s.whatsapp_token}"}
        with httpx.Client(timeout=10) as cli:
            r = cli.post(url, json=payload, headers=headers)
            if r.status_code // 100 == 2:
                j = r.json()
                provider_id = j.get("messages", [{}])[0].get("id")
                return EntregaDTO(ok=True, provider_message_id=provider_id)
            else:
                j = {}
                ctype = r.headers.get("content-type", "")
                if "application/json" in ctype:
                    j = r.json()
                err = j.get("error", {})
                return EntregaDTO(ok=False, error_code=str(err.get("code")), error_detail=err.get("message"))
