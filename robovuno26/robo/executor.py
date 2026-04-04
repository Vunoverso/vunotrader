"""
Módulo de execução de ordens (Order Management System).
"""

# ...existing code...

def execute_order(signal: int, symbol: str, quantity: float) -> bool:
    """Executa ordem de mercado com base no sinal."""
    if signal == 1:
        print(f"Enviando ordem de compra de {quantity} {symbol}")
        # Lógica de compra
    elif signal == -1:
        print(f"Enviando ordem de venda de {quantity} {symbol}")
        # Lógica de venda
    else:
        print("Nenhuma ordem executada")
    return True
