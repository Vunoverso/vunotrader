"""
Módulo de gestão de risco.
"""

# ...existing code...

def calculate_risk(position_value: float, risk_percentage: float) -> float:
    """Calcula o valor de risco de acordo com o tamanho da posição e porcentagem de risco."""
    return position_value * risk_percentage
