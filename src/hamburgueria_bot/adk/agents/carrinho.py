
"""Agente de carrinho (LLM-first): usa tools para consultar/alterar estado.
Inclui add_custom_item para permitir pedidos fora do catálogo.
"""
from pydantic import BaseModel, PositiveInt, Field, conint
from .llm_agent import AgenteLLM
from ..runtime.toolkit import ToolSpec
from ...domain.services import cart_service, menu_service
from kink import di

class GetStateArgs(BaseModel):
    conversation_id: str

class AddBySkuArgs(BaseModel):
    conversation_id: str
    sku: str
    qty: PositiveInt = 1

class AddCustomArgs(BaseModel):
    conversation_id: str
    name: str = Field(min_length=2, max_length=80)
    price_cents: conint(ge=0, le=999_000)
    qty: PositiveInt = 1

class RemArgs(BaseModel):
    conversation_id: str
    sku: str
    qty: PositiveInt = 1

def tool_get_state(args: GetStateArgs):
    items = cart_service.get_items(args.conversation_id)
    subtotal = cart_service.calc_subtotal_cents(args.conversation_id)
    return {"items": items, "subtotal_cents": subtotal}

def tool_add_by_sku(args: AddBySkuArgs):
    catalog = di.get("catalog", {})
    items = [it for c in catalog.get("categories",[]) for it in c.get("items",[])]
    item = next((i for i in items if i.get("sku","").upper()==args.sku.upper()), None)
    if not item:
        return {"ok": False, "reason": "SKU não encontrado no catálogo"}
    cart_service.add_item(args.conversation_id, item["sku"], item["name"], item["price_cents"], args.qty)
    return tool_get_state(GetStateArgs(conversation_id=args.conversation_id)) | {"ok": True}

def tool_add_custom(args: AddCustomArgs):
    cart_service.add_item(args.conversation_id, f"CUSTOM-{abs(hash(args.name))%9999}", args.name, args.price_cents, args.qty)
    return tool_get_state(GetStateArgs(conversation_id=args.conversation_id)) | {"ok": True}

def tool_rem(args: RemArgs):
    cart_service.remove_item(args.conversation_id, args.sku, args.qty)
    return tool_get_state(GetStateArgs(conversation_id=args.conversation_id)) | {"ok": True}

AgenteCarrinho = AgenteLLM(
    nome="carrinho",
    objetivo=("Gerir itens do pedido (listar/adicionar/remover), incluindo personalizações fora do catálogo."),
    exemplos=[
        {"user":"mostra meu carrinho","plano":"get_state","resposta":"listar itens e subtotal"},
        {"user":"adiciona 1 burger com pão único por 20 reais","plano":"add_custom_item","resposta":"confirmar e mostrar subtotal"},
    ],
    tool_policy=("Use add_custom_item para itens fora do catálogo. Valide SKU quando fornecido."),
)
AgenteCarrinho.register_tool(ToolSpec(name="get_cart_state", description="Estado atual do carrinho", args_schema=GetStateArgs, func=tool_get_state))
AgenteCarrinho.register_tool(ToolSpec(name="add_item_by_sku", description="Adiciona item por SKU", args_schema=AddBySkuArgs, func=tool_add_by_sku))
AgenteCarrinho.register_tool(ToolSpec(name="add_custom_item", description="Adiciona item customizado com nome/preço", args_schema=AddCustomArgs, func=tool_add_custom))
AgenteCarrinho.register_tool(ToolSpec(name="remove_from_cart", description="Remove/decrementa item", args_schema=RemArgs, func=tool_rem))
