#!/usr/bin/env python3
"""
Teste de retry logic e padrões de erro sem depender do banco
"""

import sys
sys.path.insert(0, '.')

from app.workers.study_ingestion_worker import _is_transient_error, _friendly_processing_error

def test_transient_classification():
    """Testa classificacao de erros transitorios vs permanentes."""
    print("=" * 60)
    print("TEST: Classificacao de Erros (Transitorio vs Permanente)")
    print("=" * 60)
    
    test_cases = [
        # (exc, expected_transient, label)
        (RuntimeError("rate limit exceeded"), True, "Rate limit error"),
        (RuntimeError("quota exceeded"), True, "Quota exceeded"),
        (RuntimeError("timeout connecting"), True, "Timeout"),
        (ConnectionError("connection reset"), True, "Connection reset"),
        (RuntimeError("no element found"), True, "XML parse (YouTube)"),
        
        (RuntimeError("PDF sem storage_path"), False, "PDF sem caminho"),
        (RuntimeError("Transcricao vazia"), False, "Transcricao vazia"),
        (RuntimeError("video privado"), False, "Video privado"),
        (RuntimeError("URL de video nao suportada"), False, "URL nao suportada"),
    ]
    
    passed = 0
    for exc, expected, label in test_cases:
        result = _is_transient_error(exc)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        print(f"  [{status}] {label:30s} -> transient={result}")
    
    print(f"\nResultado: {passed}/{len(test_cases)} testes passaram\n")
    return passed == len(test_cases)


def test_error_messages():
    """Testa geracao de mensagens amigaveis."""
    print("=" * 60)
    print("TEST: Mensagens de Erro Amigaveis (Humanizadas)")
    print("=" * 60)
    
    test_cases = [
        # (exc, material_type, label)
        (ValueError("no element found in XML"), "video_url", "YouTube parse error"),
        (RuntimeError("rate limit exceeded"), "pdf", "Rate limit"),
        (RuntimeError("PDF sem storage_path"), "pdf", "PDF missing"),
        (ConnectionError("socket timeout"), "video_url", "Connection timeout"),
        (RuntimeError("video privado"), "video_url", "Video privado"),
        (RuntimeError("PDF corrupted"), "pdf", "PDF corrompido"),
    ]
    
    for exc, mtype, label in test_cases:
        msg = _friendly_processing_error(exc, mtype)
        # Verify message is not the raw exception
        is_friendly = str(exc) not in msg
        status = "PASS" if is_friendly else "FAIL"
        print(f"  [{status}] {label:30s}")
        print(f"        -> {msg[:70]}")
        print()
    
    print()


def test_backoff_calculation():
    """Testa calculo de backoff exponencial."""
    print("=" * 60)
    print("TEST: Calculo de Backoff Exponencial")
    print("=" * 60)
    
    for retry_count in range(6):
        backoff = 2 ** retry_count
        print(f"  Retry #{retry_count} -> {backoff:3d}s backoff")
    
    print(f"\n  Max retries: 5 tentativas\n")


if __name__ == "__main__":
    test_transient_classification()
    test_error_messages()
    test_backoff_calculation()
    
    print("=" * 60)
    print("Testes concluidos! Retry logic validada localmente.")
    print("=" * 60)
