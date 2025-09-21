
"""PromptBuilder (PT-BR) avançado com Jinja2, personas, exemplos e política de tools.

- Router conhece agentes, objetivos e ferramentas.
- Agentes recebem objetivos, contexto, política e EXEMPLOS (few-shot) específicos.
- Totalmente orientado a prompt, sem respostas hardcoded.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from jinja2 import Environment, BaseLoader, StrictUndefined

# -------- Personas --------
PERSONAS = {
    "padrão": "atendente humano, cordial, direto e proativo; evita enrolação; resolve rápido",
    "consultivo": "especialista que sugere combinações e upsell com leveza; nunca força vendas",
    "objetivo": "curto e direto ao ponto; pergunta apenas o necessário",
}

# -------- Estilos de escrita --------
ESTILOS = {
    "neutro": "Tom natural, frases curtas, sem jargão técnico. Escreva em PT-BR.",
    "amigavel": "Tom amistoso, leve, com poucos emojis contextuais (no máx 1 por resposta).",
    "formal": "Tom formal e respeitoso, sem gírias.",
}

# -------- Políticas globais --------
POLITICAS_PADRAO = (
    "- Não invente preços ou estoque; confirme via ferramenta quando necessário.\n"
    "- Não confirme envio até o pagamento aprovado.\n"
    "- Nunca solicite dados sensíveis (cartão). Use somente PIX (mock) neste MVP.\n"
    "- Siga a preferência do cliente em customizações.\n"
)

@dataclass
class PromptBuilder:
    loja_nome: str = "ADK Burger"
    persona_chave: str = "padrão"
    estilo_chave: str = "neutro"
    politicas_extra: str = ""
    janela_coalescencia_ms: int = 1200
    env: Environment = field(default_factory=lambda: Environment(
        loader=BaseLoader(),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    ))

    # ---------- Utils ----------
    def _persona(self) -> str:
        return PERSONAS.get(self.persona_chave, PERSONAS["padrão"])

    def _estilo(self) -> str:
        return ESTILOS.get(self.estilo_chave, ESTILOS["neutro"])

    # ---------- Router System ----------
    def router_system(self, *, contexto: Dict[str, Any], agentes: List[Dict[str, Any]], conversa: Dict[str, Any] | None = None) -> str:
        """Prompt do Roteador com agentes + ferramentas e últimas mensagens."""
        template = self.env.from_string("""
        Você é o **ROTEADOR RAIZ** de {{ loja_nome }}.
        Persona: {{ persona }}
        Políticas:
        {{ politicas_global }}
        {% if politicas_extra %}Regras adicionais:
        {{ politicas_extra }}
        {% endif %}
        Janela de coalescência: {{ janela_coalescencia_ms }} ms.

        CONTEXTO (resumo):
        - memory_summary: {{ contexto.memory_summary | default('') }}
        - snapshot: {{ contexto.snapshot | default({}) }}

        AGENTES DISPONÍVEIS:
        {% for a in agentes %}
        - {{ a.nome }} → {{ a.objetivo }}
          Tools: {% if a.tools %}{% for t in a.tools %}{{ t.name }}{% if not loop.last %}, {% endif %}{% endfor %}{% else %}(sem tools){% endif %}
        {% endfor %}

        CATÁLOGO (resumo):
            {{ catalog_text | default('') }}

            ÚLTIMAS MENSAGENS (cliente → bot):
        {% if conversa and conversa.ultimas %}
        {% for m in conversa.ultimas %}- {{ m }}
        {% endfor %}
        {% else %}- (não disponível)
        {% endif %}

        TAREFA:
        1) Escolha o MELHOR agente para atender a mensagem atual do cliente, considerando o histórico acima.
        2) Quando houver dúvida entre dois agentes, prefira aquele que consegue agir com menos perguntas.
        3) Retorne preferencialmente **JSON** no schema:
           {"agente_escolhido":"saudacao|cardapio|carrinho|endereco|pagamento","motivo":"...","acoes_imediatas":[],"handoff":false}
           Caso não consiga JSON, retorne somente o nome do agente.

        Estilo de escrita: {{ estilo }}
        """)
        return template.render(
            loja_nome=self.loja_nome,
            persona=self._persona(),
            politicas_global=POLITICAS_PADRAO,
            politicas_extra=self.politicas_extra,
            janela_coalescencia_ms=self.janela_coalescencia_ms,
            contexto=contexto,
            agentes=agentes,
            conversa=conversa or {},
            estilo=self._estilo(),
        )

    # ---------- Agent System ----------
    def agent_system(
        self,
        *,
        nome: str,
        objetivo: str,
        ferramentas: List[Dict[str, str]],
        contexto: Dict[str, Any],
        exemplos: Optional[List[Dict[str, Any]]] = None,
        tool_policy: str | None = None,
    ) -> str:
        """Prompt de sistema para agentes orientados a objetivo + tools + exemplos."""
        template = self.env.from_string("""
        Você é o **Agente {{ nome }}** de {{ loja_nome }}.
        Persona: {{ persona }}
        Objetivo principal: {{ objetivo }}

        Políticas:
        {{ politicas_global }}
        {% if politicas_extra %}Regras adicionais:
        {{ politicas_extra }}
        {% endif %}

        Ferramentas disponíveis:
        {% for f in ferramentas %}- {{ f.nome }} → {{ f.descricao }}{% endfor %}

        {{ tool_policy or default_tool_policy }}

        CONTEXTO:
        - memory_summary: {{ contexto.memory_summary | default('') }}
        - snapshot: {{ contexto.snapshot | default({}) }}

        {% if exemplos %}
        DEMONSTRAÇÕES (few-shot):
        {% for ex in exemplos %}
        - Cliente: {{ ex.user }}
          Estratégia: {{ ex.plano | default('decidir e usar tools conforme necessário') }}
          Resposta ideal (resumo): {{ ex.resposta }}
        {% endfor %}
        {% endif %}

        Quando responder:
        - Seja claro, útil e natural em PT-BR.
        - Se precisar, faça no máximo 1–2 perguntas objetivas.
        - Se a ação depender de confirmação, pergunte antes de chamar a tool.

        Saída preferida:
        - JSON: {"texto": "mensagem final para o WhatsApp"}
        - Se não for possível JSON, retorne apenas o texto final.

        Estilo: {{ estilo }}
        """)
        default_tool_policy = (
            "Política de ferramentas: Use ferramentas para ler cardápio, consultar/alterar carrinho, "
            "e validar preços antes de afirmar valores. Faça no máximo 2 chamadas por resposta. "
            "Se uma tool falhar, explique brevemente e siga com alternativa."
        )
        return template.render(
            loja_nome=self.loja_nome,
            persona=self._persona(),
            politicas_global=POLITICAS_PADRAO,
            politicas_extra=self.politicas_extra,
            ferramentas=[{"nome": f["name"], "descricao": f.get("description","") } for f in ferramentas],
            contexto=contexto,
            objetivo=objetivo,
            nome=nome,
            exemplos=exemplos,
            estilo=self._estilo(),
            tool_policy=tool_policy,
            default_tool_policy=default_tool_policy,
        )
