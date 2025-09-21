
"""Portas hexagonais (interfaces) e DTOs."""
from typing import Protocol
from pydantic import BaseModel

class MensagemEntradaDTO(BaseModel):
    """DTO mínimo normalizado do WhatsApp webhook."""
    wa_id: str
    provider_message_id: str
    texto: str
    timestamp: int
    conversation_id: str

class MensagemSaidaDTO(BaseModel):
    """DTO de mensagem de saída para o provedor."""
    wa_id: str
    texto: str

class EntregaDTO(BaseModel):
    """Resultado padronizado de envio pelo provedor."""
    ok: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_detail: str | None = None

class IngressPort(Protocol):
    def receive(self, raw: dict) -> MensagemEntradaDTO: ...

class EgressPort(Protocol):
    def send(self, msg: MensagemSaidaDTO) -> EntregaDTO: ...

class AckPort(Protocol):
    def ack(self, provider_msg_id: str) -> None: ...

class OutboxRelay(Protocol):
    def dispatch_pending(self) -> int: ...
