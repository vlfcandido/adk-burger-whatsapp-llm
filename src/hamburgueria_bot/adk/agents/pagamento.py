
"""Agente de Pagamento (PIX mock) — LLM-first.

Objetivo: fechar o pedido via PIX.
- Cria cobrança com subtotal do carrinho (get_cart_state).
- Retorna PIX copia e cola (mock) e instruções.
- Permite checar status e confirmar quando "approved".
"""
from pydantic import BaseModel, PositiveInt
from .llm_agent import AgenteLLM
from ..runtime.toolkit import ToolSpec
from ...repo import repo
from ...domain.services import cart_service

class CreatePixArgs(BaseModel):
    conversation_id: str
    amount_cents: PositiveInt

class CheckPixArgs(BaseModel):
    conversation_id: str
    payment_id: str

class GetCartArgs(BaseModel):
    conversation_id: str

def tool_get_cart_state(args: GetCartArgs):
    items = cart_service.get_items(args.conversation_id)
    subtotal = cart_service.calc_subtotal_cents(args.conversation_id)
    return {"items": items, "subtotal_cents": subtotal}

def tool_create_pix(args: CreatePixArgs):
    intent = repo.create_payment_intent(args.conversation_id, args.amount_cents)
    return intent

def tool_check_pix(args: CheckPixArgs):
    intent = repo.get_payment_intent(args.conversation_id, args.payment_id)
    if not intent:
        return {"ok": False, "reason": "not_found"}
    # MVP: status permanece como está no snapshot; pode ser atualizado por operador
    return {"ok": True, "payment": intent}

AgentePagamento = AgenteLLM(
    nome="pagamento",
    objetivo=(
        "Fechar o pedido via PIX: calcular subtotal do carrinho, criar cobrança PIX (mock), "
        "fornecer o código copia e cola e verificar o status quando solicitado."
    ),
    exemplos=[
        {"user":"quero pagar","plano":"get_cart_state -> create_pix","resposta":"informar total em R$ e entregar o código PIX, com instruções simples"},
        {"user":"pago! confere aí","plano":"check_pix","resposta":"se approved, confirmar; se pending, orientar aguardar; se faltando id, pedir"},
    ],
    tool_policy=(
        "Sempre consulte o subtotal antes de criar a cobrança. Não invente valores. "
        "Após criar, informe o código PIX e peça para o cliente copiar e colar no app do banco."
    ),
)

AgentePagamento.register_tool(ToolSpec(name="get_cart_state", description="Obtém subtotal do carrinho", args_schema=GetCartArgs, func=tool_get_cart_state))
AgentePagamento.register_tool(ToolSpec(name="create_pix_charge", description="Cria cobrança PIX (mock)", args_schema=CreatePixArgs, func=tool_create_pix))
AgentePagamento.register_tool(ToolSpec(name="check_pix_status", description="Consulta status da cobrança PIX", args_schema=CheckPixArgs, func=tool_check_pix))
