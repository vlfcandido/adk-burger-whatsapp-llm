
"""Repositório: Inbox/Outbox/State + Coalescência + Handoff (pausa por contato)."""
from __future__ import annotations
from typing import Dict, Any
from sqlalchemy import select
from kink import di
from ..repo.models import InboxMessage, OutboxMessage, ConversationState, ConversationEvent
from ..core.logging import get_logger

log = get_logger()

def save_inbox(dto) -> int:
    """Insere na Inbox com chave de idempotência (conversation_id, provider_message_id)."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        im = InboxMessage(
            conversation_id=dto.conversation_id,
            provider_message_id=dto.provider_message_id,
            wa_id=dto.wa_id,
            payload=dto.model_dump(mode="json"),
        )
        s.add(im)
    log.info("inbox_saved", conversation_id=dto.conversation_id, provider_message_id=dto.provider_message_id)
    return im.id

def get_last_processed_inbox_id(conversation_id: str) -> int | None:
    """Obtém do snapshot a última inbox id já processada/enviada."""
    Session = di["session_factory"]
    with Session() as s:
        st = s.get(ConversationState, conversation_id)
        if not st or not st.snapshot:
            return None
        return st.snapshot.get("last_processed_inbox_id")

def set_last_processed_inbox_id(conversation_id: str, inbox_id: int) -> None:
    """Atualiza snapshot com a última inbox id processada (após envio)."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        st = s.get(ConversationState, conversation_id)
        if not st:
            st = ConversationState(conversation_id=conversation_id, memory_summary=None, snapshot={})
            s.add(st)
        snap = dict(st.snapshot or {})
        snap["last_processed_inbox_id"] = inbox_id
        st.snapshot = snap
    log.info("snapshot_advanced", conversation_id=conversation_id, last_processed_inbox_id=inbox_id)

def get_handoff(conversation_id: str) -> bool:
    """Retorna se a conversa está pausada para atendimento humano (handoff)."""
    Session = di["session_factory"]
    with Session() as s:
        st = s.get(ConversationState, conversation_id)
        return bool((st.snapshot or {}).get("handoff_paused")) if st else False

def set_handoff(conversation_id: str, paused: bool, reason: str | None = None) -> None:
    """Liga/desliga o modo pausado para LLM (transbordo humano)."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        st = s.get(ConversationState, conversation_id)
        if not st:
            st = ConversationState(conversation_id=conversation_id, memory_summary=None, snapshot={})
            s.add(st)
        snap = dict(st.snapshot or {})
        snap["handoff_paused"] = paused
        if reason:
            snap["handoff_reason"] = reason
        st.snapshot = snap
    log.info("handoff_set", conversation_id=conversation_id, paused=paused, reason=reason)

def load_context(conversation_id: str) -> dict:
    """Obtém memory_summary e snapshot atuais da conversa."""
    Session = di["session_factory"]
    with Session() as s:
        st = s.get(ConversationState, conversation_id)
        return {
            "memory_summary": (st.memory_summary if st else None),
            "snapshot": (st.snapshot if st else {}),
        }

def enqueue_outbox(conversation_id: str, body: dict, source_max_inbox_id: int | None = None) -> int:
    """Enfileira mensagem de saída no Outbox com metadados de preflight."""
    if source_max_inbox_id is not None:
        body = dict(body)
        meta = dict(body.get("_meta", {}))
        meta["source_max_inbox_id"] = source_max_inbox_id
        body["_meta"] = meta
    Session = di["session_factory"]
    with Session() as s, s.begin():
        ob = OutboxMessage(conversation_id=conversation_id, body=body)
        s.add(ob)
        s.flush()
        ob_id = ob.id
    log.info("outbox_enqueued", conversation_id=conversation_id, outbox_id=ob_id)
    return ob_id

def has_newer_inbox(conversation_id: str, since_inbox_id: int) -> bool:
    """Retorna True se existir InboxMessage com id > since_inbox_id para a conversa."""
    Session = di["session_factory"]
    with Session() as s:
        row = s.execute(
            select(InboxMessage.id)
            .where(InboxMessage.conversation_id == conversation_id, InboxMessage.id > since_inbox_id)
            .order_by(InboxMessage.id.desc())
            .limit(1)
        ).scalar()
        return row is not None

def log_event(conversation_id: str, kind: str, data: dict) -> None:
    """Registra um evento de auditoria em conversation_events."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        ev = ConversationEvent(conversation_id=conversation_id, kind=kind, data=data, ts=int(__import__("time").time()*1000))
        s.add(ev)
    log.info("conv_event", conversation_id=conversation_id, kind=kind)


# ---------- Address helpers (snapshot) ----------
def get_address(conversation_id: str) -> dict | None:
    """Retorna endereço salvo no snapshot (se existir)."""
    Session = di["session_factory"]
    with Session() as s:
        st = s.get(ConversationState, conversation_id)
        if not st or not st.snapshot:
            return None
        return st.snapshot.get("address")

def set_address(conversation_id: str, address: dict) -> None:
    """Atualiza endereço no snapshot (normalizado/validado)."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        st = s.get(ConversationState, conversation_id)
        if not st:
            st = ConversationState(conversation_id=conversation_id, memory_summary=None, snapshot={})
            s.add(st)
        snap = dict(st.snapshot or {})
        snap["address"] = address
        st.snapshot = snap
    log.info("address_upsert", conversation_id=conversation_id)

# ---------- Payment helpers (snapshot PIX-mock) ----------
def _gen_payment_id() -> str:
    """Gera um ID simples para intents de pagamento."""
    return f"pix_{int(time.time()*1000)}_{random.randint(1000,9999)}"

def create_payment_intent(conversation_id: str, amount_cents: int) -> dict:
    """Cria uma intenção de pagamento PIX (mock) no snapshot."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        st = s.get(ConversationState, conversation_id)
        if not st:
            st = ConversationState(conversation_id=conversation_id, memory_summary=None, snapshot={})
            s.add(st)
        snap = dict(st.snapshot or {})
        payments = list(snap.get("payments", []))
        pid = _gen_payment_id()
        intent = {
            "id": pid,
            "amount_cents": amount_cents,
            "status": "pending",
            "pix_code": f"000201BR.GOV.BCB.PIX|ADK|{pid}|{amount_cents}",  # string mock
            "created_ts": int(time.time()*1000),
        }
        payments.append(intent)
        snap["payments"] = payments
        st.snapshot = snap
    log.info("payment_created", conversation_id=conversation_id, payment_id=pid, amount_cents=amount_cents)
    return intent

def get_payment_intent(conversation_id: str, payment_id: str) -> dict | None:
    """Recupera uma intenção de pagamento do snapshot."""
    Session = di["session_factory"]
    with Session() as s:
        st = s.get(ConversationState, conversation_id)
        if not st or not st.snapshot:
            return None
        for p in st.snapshot.get("payments", []):
            if p.get("id") == payment_id:
                return p
    return None

def update_payment_status(conversation_id: str, payment_id: str, status: str) -> dict | None:
    """Atualiza status de pagamento (pending|approved|expired|cancelled)."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        st = s.get(ConversationState, conversation_id)
        if not st or not st.snapshot:
            return None
        payments = list(st.snapshot.get("payments", []))
        updated = None
        for p in payments:
            if p.get("id") == payment_id:
                p["status"] = status
                updated = p
                break
        snap = dict(st.snapshot or {})
        snap["payments"] = payments
        st.snapshot = snap
    log.info("payment_status", conversation_id=conversation_id, payment_id=payment_id, status=status)
    return updated
