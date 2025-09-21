
"""Classe base para agentes."""
from abc import ABC, abstractmethod

class BaseAgente(ABC):
    """Interface comum de agentes."""
    nome: str
    prompt_sistema: str

    @abstractmethod
    def processar(self, mensagem: str, contexto: dict) -> dict:
        """Processa a mensagem e retorna dict serializável com RespostaFinalDTO."""
        raise NotImplementedError
