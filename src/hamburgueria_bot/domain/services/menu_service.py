
"""Serviço de cardápio (estático no MVP)."""
from typing import List, Dict

def get_menu() -> List[Dict]:
    """Retorna cardápio simples com SKUs e preços em centavos (idempotente)."""
    return [
        {"sku":"BX1","name":"Burger Clássico","price_cents":2500},
        {"sku":"BX2","name":"Cheese Burger","price_cents":2800},
        {"sku":"BX3","name":"Duplo Bacon","price_cents":3400},
        {"sku":"AC1","name":"Batata Média","price_cents":1200},
        {"sku":"RV1","name":"Refrigerante Lata","price_cents":800},
    ]
