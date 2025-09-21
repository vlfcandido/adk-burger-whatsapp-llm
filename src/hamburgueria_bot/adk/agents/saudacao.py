
"""Agente de saudação com examples (few-shot)."""
from .llm_agent import AgenteLLM

AgenteSaudacao = AgenteLLM(
    nome="saudacao",
    objetivo=("Dar boas-vindas, entender rapidamente o que o cliente deseja e oferecer próximos passos claros."),
    exemplos=[
        {"user":"oi","resposta":"boas-vindas + CTA para ver cardápio ou dizer o que deseja"},
        {"user":"tá aberto?","resposta":"responder horário e oferecer cardápio"},
    ],
    tool_policy=("Use tools apenas se precisar consultar estado ou dados. Caso contrário, responda direto."),
)
