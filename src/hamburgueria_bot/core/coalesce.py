
"""Coalescência por janela de inatividade com travas PostgreSQL + lock local.

- Usa pg_try_advisory_lock(hash64(conversation_id)) para garantir exclusão distribuída.
- Espera uma janela de INATIVIDADE (coalesce_window_ms). Se novas mensagens chegarem,
  reinicia o cronômetro (debounce). Limite de espera máx = 3 * coalesce_window_ms.
- Retorna pacote lógico com:
    { "texto_unificado": str, "message_ids": list[int], "max_inbox_id": int }
"""
from __future__ import annotations
import hashlib, time
from typing import Dict, List
from sqlalchemy import select, text
from kink import di
from ..core.settings import Settings
from ..repo.models import InboxMessage
from ..core.logging import get_logger

log = get_logger()

def _hash64(s: str) -> int:
    """Gera inteiro 63-bit para advisory lock (assina em positivo)."""
    h = int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big", signed=False)
    # limitar a signed BIGINT positivo
    return h & 0x7FFF_FFFF_FFFF_FFFF

def _pg_try_advisory_lock(conn, key: int) -> bool:
    return conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()

def _pg_advisory_unlock(conn, key: int) -> None:
    conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})

def coalesce_window(conversation_id: str, last_processed_id: int | None) -> Dict:
    """Agrupa mensagens por janela de inatividade.

    :param conversation_id: id da conversa (usamos wa_id como conversation_id).
    :param last_processed_id: última inbox id já respondida (do snapshot).
    :return: dict com texto_unificado, message_ids e max_inbox_id.
    """
    settings: Settings = di[Settings]
    Session = di["session_factory"]
    key = _hash64(conversation_id)
    window_ms = settings.coalesce_window_ms
    max_wait_ms = window_ms * 3

    with Session() as s:
        with s.begin():
            conn = s.connection()
            if not _pg_try_advisory_lock(conn, key):
                # Outro worker agregando; esperar janela e apenas pegar tudo que chegou.
                time.sleep(window_ms / 1000.0)
            try:
                # Observa crescimento de inbox.id até estabilizar por window_ms
                start = time.time()
                last_seen_id = None
                last_change = time.time()
                # base inicial: maior id > last_processed_id
                q = select(InboxMessage.id).where(InboxMessage.conversation_id == conversation_id)
                if last_processed_id:
                    q = q.where(InboxMessage.id > last_processed_id)
                last_seen_id = s.execute(q.order_by(InboxMessage.id.desc()).limit(1)).scalar()
                last_change = time.time()
                while (time.time() - start) * 1000 < max_wait_ms:
                    q2 = select(InboxMessage.id).where(InboxMessage.conversation_id == conversation_id)
                    if last_processed_id:
                        q2 = q2.where(InboxMessage.id > last_processed_id)
                    max_id = s.execute(q2.order_by(InboxMessage.id.desc()).limit(1)).scalar()
                    if max_id != last_seen_id:
                        last_seen_id = max_id
                        last_change = time.time()
                    # Quiet period?
                    if (time.time() - last_change) * 1000 >= window_ms:
                        break
                    time.sleep(min(0.15, window_ms/1000.0))

                if last_seen_id is None:
                    return {"texto_unificado": "", "message_ids": [], "max_inbox_id": (last_processed_id or 0)}

                # Coletar mensagens novas (id > last_processed_id) até last_seen_id
                q3 = select(InboxMessage).where(
                    (InboxMessage.conversation_id == conversation_id) &
                    (InboxMessage.id <= last_seen_id)
                )
                if last_processed_id:
                    q3 = q3.where(InboxMessage.id > last_processed_id)
                rows = s.execute(q3.order_by(InboxMessage.id.asc())).scalars().all()
                texts = []
                ids = []
                for r in rows:
                    payload = r.payload or {}
                    txt = payload.get("texto", "")
                    if txt:
                        texts.append(txt)
                    ids.append(r.id)

                texto_unificado = " ".join(texts).strip()
                return {"texto_unificado": texto_unificado, "message_ids": ids, "max_inbox_id": last_seen_id}
            finally:
                try:
                    _pg_advisory_unlock(conn, key)
                except Exception:
                    pass
