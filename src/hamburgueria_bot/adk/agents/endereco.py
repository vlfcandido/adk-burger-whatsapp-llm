
"""Agente de Endereço (LLM-first): captura/valida/normaliza e salva no snapshot.

Tools expostas:
- upsert_address(conversation_id, address_text) -> normaliza e salva
- get_address(conversation_id) -> retorna o endereço salvo
"""
from pydantic import BaseModel, Field
from .llm_agent import AgenteLLM
from ..runtime.toolkit import ToolSpec
from ...repo import repo

class UpsertArgs(BaseModel):
    conversation_id: str
    address_text: str = Field(min_length=5, max_length=280)

class GetArgs(BaseModel):
    conversation_id: str

def _normalize(text: str) -> dict:
    """Normalização simples (MVP): separa campos heurísticos. Em produção, usar um validador externo."""
    # Heurística leve: tentar encontrar número e complemento
    parts = text.strip().replace(",", " ").split()
    numero = next((p for p in parts if p.isdigit()), None)
    normalized = {
        "raw": text,
        "rua": " ".join(p for p in parts if not p.isdigit()).strip(),
        "numero": numero or "",
        "complemento": "",
        "bairro": "",
        "cidade": "",
        "uf": "",
        "cep": "",
    }
    return normalized

def tool_upsert_address(args: UpsertArgs):
    addr = _normalize(args.address_text)
    repo.set_address(args.conversation_id, addr)
    return {"ok": True, "address": addr}

def tool_get_address(args: GetArgs):
    addr = repo.get_address(args.conversation_id)
    return {"address": addr}

AgenteEndereco = AgenteLLM(
    nome="endereco",
    objetivo=(
        "Entender o endereço de entrega do cliente, confirmar os pontos essenciais, "
        "normalizar e salvar no snapshot para uso no pedido."
    ),
    exemplos=[
        {"user":"meu endereço é Rua Exemplo, 123", "plano":"upsert_address e confirmar", "resposta":"confirmar rua e número, pedir complemento se faltar"},
        {"user":"pode ver meu endereço?", "plano":"get_address", "resposta":"ler do snapshot e repetir de forma educada"},
    ],
    tool_policy=("Confirme número e referência quando ausente. Use upsert_address para salvar o texto do cliente."),
)

AgenteEndereco.register_tool(ToolSpec(
    name="upsert_address",
    description="Normaliza e salva o endereço informado",
    args_schema=UpsertArgs,
    func=tool_upsert_address
))
AgenteEndereco.register_tool(ToolSpec(
    name="get_address",
    description="Retorna o endereço salvo para esta conversa",
    args_schema=GetArgs,
    func=tool_get_address
))
