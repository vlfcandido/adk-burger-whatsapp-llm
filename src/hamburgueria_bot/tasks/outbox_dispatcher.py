
"""Despacho de outbox com preflight e logs detalhados."""
from __future__ import annotations
from sqlalchemy import select
from datetime import datetime
from kink import di
from ..repo.models import OutboxMessage
from ..ports.interfaces import MensagemSaidaDTO
from ..connectors.whatsapp.cloud_api_adapter import WhatsAppCloudAdapter
from ..repo import repo
from ..core.logging import get_logger

log = get_logger()

def dispatch_once() -> int:
    """Envia até 20 mensagens 'queued' e retorna quantas foram enviadas com sucesso."""
    Session = di["session_factory"]
    adapter = WhatsAppCloudAdapter()
    sent = 0
    with Session() as s, s.begin():
        rows = s.execute(select(OutboxMessage).where(OutboxMessage.status=="queued").limit(20)).scalars().all()
        for ob in rows:
            meta = (ob.body or {}).get("_meta", {}) if ob.body else {}
            src_max = meta.get("source_max_inbox_id")
            if isinstance(src_max, int) and repo.has_newer_inbox(ob.conversation_id, src_max):
                ob.status = "cancelled"
                repo.log_event(ob.conversation_id, "dispatch_cancelled_newer", {"outbox_id": ob.id, "since": src_max})
                log.info("dispatch_cancelled", conversation_id=ob.conversation_id, outbox_id=ob.id)
                continue

            dto = MensagemSaidaDTO.model_validate(ob.body)
            res = adapter.send(dto)
            if res.ok:
                ob.status = "sent"
                ob.sent_at = datetime.utcnow()
                ob.provider_message_id = res.provider_message_id
                if isinstance(src_max, int):
                    repo.set_last_processed_inbox_id(ob.conversation_id, src_max)
                repo.log_event(ob.conversation_id, "dispatch_sent", {"outbox_id": ob.id, "provider_message_id": res.provider_message_id})
                log.info("dispatch_sent", conversation_id=ob.conversation_id, outbox_id=ob.id)
                sent += 1
            else:
                ob.attempts += 1
                ob.last_error = res.error_detail
                if ob.attempts >= 5:
                    ob.status = "dead_letter"
                    repo.log_event(ob.conversation_id, "dispatch_dead_letter", {"outbox_id": ob.id, "error": res.error_detail})
                else:
                    repo.log_event(ob.conversation_id, "dispatch_retry", {"outbox_id": ob.id, "attempts": ob.attempts, "error": res.error_detail})
    return sent
