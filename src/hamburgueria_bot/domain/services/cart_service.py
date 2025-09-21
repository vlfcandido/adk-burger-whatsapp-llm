
"""Serviço de carrinho: operações idempotentes por conversa."""
from __future__ import annotations
from kink import di
from sqlalchemy import select, delete
from ...repo.models import CartItem

def add_item(conversation_id: str, sku: str, name: str, unit_price_cents: int, qty: int = 1) -> None:
    """Adiciona (ou incrementa) item no carrinho."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        row = s.execute(select(CartItem).where(CartItem.conversation_id==conversation_id, CartItem.sku==sku)).scalars().first()
        if row:
            row.qty += qty
        else:
            s.add(CartItem(conversation_id=conversation_id, sku=sku, name=name, qty=qty, unit_price_cents=unit_price_cents))

def remove_item(conversation_id: str, sku: str, qty: int = 1) -> None:
    """Decrementa item e remove se zerar."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        row = s.execute(select(CartItem).where(CartItem.conversation_id==conversation_id, CartItem.sku==sku)).scalars().first()
        if row:
            row.qty -= qty
            if row.qty <= 0:
                s.delete(row)

def clear_cart(conversation_id: str) -> None:
    """Esvazia carrinho."""
    Session = di["session_factory"]
    with Session() as s, s.begin():
        s.execute(delete(CartItem).where(CartItem.conversation_id==conversation_id))

def get_items(conversation_id: str) -> list[dict]:
    """Lista itens atuais do carrinho."""
    Session = di["session_factory"]
    with Session() as s:
        rows = s.execute(select(CartItem).where(CartItem.conversation_id==conversation_id)).scalars().all()
        return [{"sku":r.sku,"name":r.name,"qty":r.qty,"unit_price_cents":r.unit_price_cents} for r in rows]

def calc_subtotal_cents(conversation_id: str) -> int:
    """Calcula subtotal em centavos."""
    items = get_items(conversation_id)
    return sum(i["qty"] * i["unit_price_cents"] for i in items)
