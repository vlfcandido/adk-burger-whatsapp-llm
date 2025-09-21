
"""Tools tipadas (Pydantic) para carrinho (puras, I/O via serviços)."""
from pydantic import BaseModel, Field, PositiveInt
from ...domain.services import cart_service, menu_service

class AddItemArgs(BaseModel):
    conversation_id: str
    sku: str = Field(min_length=2, max_length=10)
    qty: PositiveInt = 1

class RemoveItemArgs(BaseModel):
    conversation_id: str
    sku: str
    qty: PositiveInt = 1

class CartState(BaseModel):
    items: list[dict]
    subtotal_cents: int

def add_item(args: AddItemArgs) -> CartState:
    """Adiciona item idempotente ao carrinho e retorna estado."""
    sku = args.sku
    menu = {m["sku"]: m for m in menu_service.get_menu()}
    if sku not in menu:
        # SKU inválido: retorna estado atual sem alterações
        items = cart_service.get_items(args.conversation_id)
        return CartState(items=items, subtotal_cents=cart_service.calc_subtotal_cents(args.conversation_id))
    item = menu[sku]
    cart_service.add_item(args.conversation_id, sku=sku, name=item["name"], unit_price_cents=item["price_cents"], qty=args.qty)
    items = cart_service.get_items(args.conversation_id)
    return CartState(items=items, subtotal_cents=cart_service.calc_subtotal_cents(args.conversation_id))

def remove_item(args: RemoveItemArgs) -> CartState:
    """Remove/Decrementa item do carrinho e retorna estado."""
    cart_service.remove_item(args.conversation_id, sku=args.sku, qty=args.qty)
    items = cart_service.get_items(args.conversation_id)
    return CartState(items=items, subtotal_cents=cart_service.calc_subtotal_cents(args.conversation_id))
