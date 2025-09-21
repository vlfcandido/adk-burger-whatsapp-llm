
"""Agente de cardápio (LLM-first): catálogo vem no prompt; tools apenas executam.
- add_item_by_sku (opcional): usa catálogo carregado (se houver) para validar e adicionar.
- add_custom_item: adiciona item customizado com nome/preço informados pelo LLM/cliente.
"""
from pydantic import BaseModel, Field, PositiveInt, conint
from .llm_agent import AgenteLLM
from ..runtime.toolkit import ToolSpec
from ...domain.services import cart_service
from kink import di

class AddBySkuArgs(BaseModel):
    conversation_id: str
    sku: str = Field(min_length=2, max_length=20)
    qty: PositiveInt = 1

class AddCustomArgs(BaseModel):
    conversation_id: str
    name: str = Field(min_length=2, max_length=80)
    price_cents: conint(ge=0, le=999_000)  # MVP: preço informado
    qty: PositiveInt = 1

def tool_add_by_sku(args: AddBySkuArgs):
    catalog = di.get("catalog", {})
    items = [it for c in catalog.get("categories",[]) for it in c.get("items",[])]
    item = next((i for i in items if i.get("sku","").upper()==args.sku.upper()), None)
    if not item:
        return {"ok": False, "reason": "SKU não encontrado no catálogo"}
    cart_service.add_item(args.conversation_id, item["sku"], item["name"], item["price_cents"], args.qty)
    return {"ok": True, "added":{"sku": item["sku"], "name": item["name"], "qty": args.qty, "unit_price_cents": item["price_cents"]},
            "subtotal_cents": cart_service.calc_subtotal_cents(args.conversation_id)}

def tool_add_custom(args: AddCustomArgs):
    """Permite itens fora do catálogo (LLM-first de verdade)."""
    cart_service.add_item(args.conversation_id, f"CUSTOM-{abs(hash(args.name))%9999}", args.name, args.price_cents, args.qty)
    return {"ok": True, "added":{"name": args.name, "qty": args.qty, "unit_price_cents": args.price_cents},
            "subtotal_cents": cart_service.calc_subtotal_cents(args.conversation_id)}

AgenteCardapio = AgenteLLM(
    nome="cardapio",
    objetivo=("Apresentar opções com base no catálogo do prompt e permitir adicionar por SKU ou item customizado."),
    exemplos=[
        {"user":"quero 2 BX2","plano":"validar SKU e adicionar","resposta":"confirmação + subtotal"},
        {"user":"quero burger só com um pão","plano":"item customizado","resposta":"perguntas mínimas e adiciona custom com preço informado"},
    ],
    tool_policy=("Prefira validar SKU; se for pedido fora do catálogo, use add_custom_item com preço informado."),
)
AgenteCardapio.register_tool(ToolSpec(name="add_item_by_sku", description="Adiciona item por SKU do catálogo", args_schema=AddBySkuArgs, func=tool_add_by_sku))
AgenteCardapio.register_tool(ToolSpec(name="add_custom_item", description="Adiciona item customizado com nome/preço", args_schema=AddCustomArgs, func=tool_add_custom))
