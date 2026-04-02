import openai
import os
from typing import Optional

def analyze_loss(symbol: str, side: str, entry: float, sl: float, tp: float, exit_price: float, rationale: str) -> str:
    """
    Analisa tecnicamente por que um trade deu loss usando OpenAI.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "Análise automática indisponível: API Key não configurada."

    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""
    Você é um Analista Senior de Trading de Alta Performance.
    Um sinal do VunoTrader resultou em LOSS. Analise o cenário e forneça uma explicação técnica breve e direta para aprendizado.

    Símbolo: {symbol}
    Lado: {side}
    Ponto de Entrada: {entry}
    Stop Loss (Planejado): {sl}
    Take Profit (Planejado): {tp}
    Preço de Saída (Loss): {exit_price}
    Racional da Entrada (Original): {rationale}

    Explique o provável motivo da falha (ex: Rompimento falso, Reversão de tendência, Alta volatilidade no nível, etc).
    Seja técnico e objetivo em português. Máximo 150 caracteres.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Erro na análise de IA: {str(e)}"
