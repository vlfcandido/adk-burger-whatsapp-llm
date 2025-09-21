
"""Agente genérico orientado a prompt (PT-BR) com examples e política de tools."""
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ...ports.interfaces import MensagemSaidaDTO
from ...core.llm_client import LLMClient
from ..runtime.toolkit import ToolRegistry, ToolSpec
from ...core.prompting import PromptBuilder
from kink import di
import json

class RespostaFinal(BaseModel):
    texto: str

class AgenteLLM:
    def __init__(self, nome: str, objetivo: str, exemplos: Optional[List[Dict[str, Any]]] = None, tool_policy: str | None = None):
        self.nome = nome
        self.objetivo = objetivo
        self.exemplos = exemplos or []
        self.tool_policy = tool_policy
        self.tools = ToolRegistry()
        self.llm = di[LLMClient]
        self.builder: PromptBuilder = di[PromptBuilder]

    def register_tool(self, spec: ToolSpec) -> None:
        self.tools.register(spec)

    def list_tools(self) -> list[dict]:
        return self.tools.openai_tools()

    def processar(self, mensagem: str, contexto: dict) -> dict:
        system = self.builder.agent_system(
            nome=self.nome,
            objetivo=self.objetivo,
            ferramentas=self.list_tools(),
            contexto=contexto,
            exemplos=self.exemplos,
            tool_policy=self.tool_policy,
        )
        user = (
            "Mensagem do cliente:\n" + (mensagem or "") +
            "\n\nInstruções: responda de forma natural em PT-BR. Se precisar, chame ferramentas."
        )
        msg = self.llm.complete_with_tools_loop(system=system, user=user, tools_registry=self.tools, max_steps=4)
        content = msg.get("content", "") or ""
        texto = None
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "texto" in data:
                texto = str(data["texto"])[:4000]
        except Exception:
            pass
        if texto is None:
            texto = str(content)[:4000]
        wa_id = contexto.get("wa_id")
        return MensagemSaidaDTO(wa_id=wa_id, texto=texto).model_dump()
