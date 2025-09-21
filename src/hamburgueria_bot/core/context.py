
"""Helpers para montar contexto conversacional (últimas mensagens)."""
from __future__ import annotations
from typing import List, Dict, Any
from kink import di
from sqlalchemy import select
from ..repo.models import InboxMessage

def last_messages(conversation_id: str, limit: int = 5) -> Dict[str, Any]:
    """Retorna últimas N mensagens de entrada em ordem cronológica."""
    Session = di["session_factory"]
    with Session() as s:
        rows = s.execute(
            select(InboxMessage).where(InboxMessage.conversation_id==conversation_id).order_by(InboxMessage.id.desc()).limit(limit)
        ).scalars().all()
        texts = []
        for r in reversed(rows):
            payload = r.payload or {}
            t = payload.get("texto")
            if t:
                texts.append(t)
    return {"ultimas": texts}
