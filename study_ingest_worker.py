#!/usr/bin/env python3
"""
study_ingest_worker.py
======================
Worker standalone para processar materiais de estudo pendentes.

Fluxo:
  1. Busca study_materials onde processing_status = 'pending'
     (respeitando next_retry_at se existir)
  2. Para cada material:
     - video_url  → extrai transcript via youtube_transcript_api
     - pdf        → baixa do Supabase Storage, extrai texto via pypdf
  3. Envia texto para OpenAI (gpt-4o-mini) para:
     a. Gerar summary (~300 palavras)
     b. Dividir em chunks de ~400 tokens para RAG
  4. Salva em study_material_chunks e marca material como 'processed'
  5. Em caso de erro: incrementa retry_count + backoff exponencial

Uso:
  python study_ingest_worker.py                 # processa todos os pending
  python study_ingest_worker.py --id <uuid>     # processa um material específico
  python study_ingest_worker.py --loop          # fica rodando em loop (worker daemon)

Variáveis de ambiente obrigatórias:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY
  OPENAI_API_KEY

Opcional:
  OPENAI_MODEL          (default: gpt-4o-mini)
  INGEST_BATCH_SIZE     (default: 5)
  INGEST_LOOP_INTERVAL  (default: 60 segundos)
"""

import argparse
import io
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

# ── Dependências obrigatórias ─────────────────────────────────────────────────

try:
    from supabase import create_client, Client as SupabaseClient
except ImportError:
    print("ERRO: 'supabase' não instalado. Execute: pip install supabase", file=sys.stderr)
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("ERRO: 'openai' não instalado. Execute: pip install openai", file=sys.stderr)
    sys.exit(1)

try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
except ImportError:
    print("ERRO: 'youtube-transcript-api' não instalado. Execute: pip install youtube-transcript-api", file=sys.stderr)
    sys.exit(1)

try:
    from pypdf import PdfReader
except ImportError:
    print("ERRO: 'pypdf' não instalado. Execute: pip install pypdf", file=sys.stderr)
    sys.exit(1)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("study_ingest")

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL      = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY      = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL      = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
BATCH_SIZE        = int(os.environ.get("INGEST_BATCH_SIZE", "5"))
LOOP_INTERVAL     = int(os.environ.get("INGEST_LOOP_INTERVAL", "60"))
STORAGE_BUCKET    = os.environ.get("SUPABASE_STUDY_BUCKET", "training-videos")

MAX_RETRY         = 5
MAX_CHUNK_CHARS   = 1600   # ~400 tokens a 4 chars/token
SUMMARY_MAX_WORDS = 300


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de extração de texto
# ─────────────────────────────────────────────────────────────────────────────

def extract_youtube_id(url: str) -> Optional[str]:
    """Extrai o ID de vídeo de URLs do YouTube."""
    import re
    patterns = [
        r"(?:v=|youtu\.be/|/embed/|/v/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def get_youtube_transcript(url: str) -> str:
    """Retorna a transcrição de um vídeo YouTube como texto limpo."""
    vid_id = extract_youtube_id(url)
    if not vid_id:
        raise ValueError(f"URL de vídeo não suportada: {url}")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(vid_id, languages=["pt", "pt-BR", "en"])
    except (TranscriptsDisabled, NoTranscriptFound):
        raise ValueError("Transcrição não disponível para este vídeo.")

    text = " ".join(seg["text"] for seg in transcript if seg.get("text"))
    if len(text.strip()) < 100:
        raise ValueError("Transcrição vazia ou muito curta.")
    return text


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extrai texto de um PDF em bytes usando pypdf."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    full = "\n\n".join(pages)
    if len(full.strip()) < 50:
        raise ValueError("Não foi possível extrair texto do PDF.")
    return full


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY não definida.")
    return OpenAI(api_key=OPENAI_API_KEY)


def summarize_text(client: OpenAI, title: str, raw_text: str) -> str:
    """Gera um resumo do material em ~300 palavras adaptado para traders."""
    # Trunca entrada para evitar tokens excessivos (~12k chars ≈ 3k tokens)
    truncated = raw_text[:12_000]
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um especialista em mercado financeiro e trading. "
                    "Resuma o material abaixo em até 300 palavras, "
                    "destacando os conceitos mais relevantes para traders: "
                    "entradas, saídas, gestão de risco, indicadores técnicos e padrões de mercado. "
                    "Seja objetivo e técnico."
                ),
            },
            {
                "role": "user",
                "content": f"Título: {title}\n\n{truncated}",
            },
        ],
        max_tokens=500,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def chunk_text(raw_text: str) -> list[dict]:
    """
    Divide o texto em chunks de ~400 tokens para RAG.
    Retorna lista de {chunk_index, content, token_estimate}.
    """
    # Split por parágrafos, depois agrupa até MAX_CHUNK_CHARS
    paragraphs = [p.strip() for p in raw_text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    chunks     = []
    current    = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > MAX_CHUNK_CHARS and current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += len(para) + 1

    if current:
        chunks.append(" ".join(current))

    return [
        {
            "chunk_index":     i,
            "content":         c,
            "token_estimate":  max(1, len(c) // 4),
        }
        for i, c in enumerate(chunks)
        if c.strip()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline principal de ingestão de um material
# ─────────────────────────────────────────────────────────────────────────────

def process_material(sb: SupabaseClient, ai: OpenAI, material: dict) -> None:
    mat_id   = material["id"]
    org_id   = material["organization_id"]
    title    = material.get("title") or "Sem título"
    mat_type = material.get("material_type", "")
    url      = material.get("source_url")
    path     = material.get("storage_path")

    log.info(f"Processando [{mat_type}] {title!r} (id={mat_id[:8]}…)")

    # Marca como 'processing'
    sb.table("study_materials").update({
        "processing_status": "processing",
        "processing_error":  None,
    }).eq("id", mat_id).execute()

    try:
        # 1. Extração de texto
        if mat_type == "video_url":
            if not url:
                raise ValueError("Campo source_url está vazio para material do tipo video_url.")
            raw_text = get_youtube_transcript(url)

        elif mat_type == "pdf":
            if not path:
                raise ValueError("Campo storage_path está vazio para material do tipo pdf.")
            resp = sb.storage.from_(STORAGE_BUCKET).download(path)
            # resp pode ser bytes diretamente
            pdf_bytes = resp if isinstance(resp, bytes) else bytes(resp)
            raw_text = extract_pdf_text(pdf_bytes)

        else:
            raise ValueError(f"Tipo de material não suportado: {mat_type!r}")

        # 2. Resumo via OpenAI
        summary = summarize_text(ai, title, raw_text)

        # 3. Chunks para RAG
        chunks = chunk_text(raw_text)

        # 4. Salva chunks (apaga os antigos primeiro, caso seja re-processamento)
        sb.table("study_material_chunks").delete().eq("material_id", mat_id).execute()

        chunk_rows = [
            {
                "organization_id": org_id,
                "material_id":     mat_id,
                "chunk_index":     c["chunk_index"],
                "content":         c["content"],
                "token_estimate":  c["token_estimate"],
            }
            for c in chunks
        ]

        if chunk_rows:
            # Insere em lotes de 20 para evitar payload grande
            for i in range(0, len(chunk_rows), 20):
                sb.table("study_material_chunks").insert(chunk_rows[i:i+20]).execute()

        # 5. Atualiza material como processado
        sb.table("study_materials").update({
            "processing_status": "processed",
            "processing_error":  None,
            "processed_at":      datetime.now(timezone.utc).isoformat(),
            "summary":           summary,
            "retry_count":       0,
            "next_retry_at":     None,
            "last_error_at":     None,
            "updated_at":        datetime.now(timezone.utc).isoformat(),
        }).eq("id", mat_id).execute()

        log.info(
            f"✓ Processado: {title!r} — {len(chunks)} chunks | "
            f"summary={len(summary)} chars"
        )

    except Exception as exc:
        # Backoff exponencial: 5min, 10min, 20min, 40min, 80min
        retry_count = int(material.get("retry_count") or 0) + 1
        delay_min   = 5 * (2 ** (retry_count - 1))
        next_retry  = datetime.now(timezone.utc) + timedelta(minutes=delay_min)
        new_status  = "error" if retry_count >= MAX_RETRY else "pending"

        log.warning(f"✗ Erro ao processar {mat_id[:8]}…: {exc}")

        sb.table("study_materials").update({
            "processing_status": new_status,
            "processing_error":  str(exc)[:1000],
            "retry_count":       retry_count,
            "next_retry_at":     next_retry.isoformat() if new_status == "pending" else None,
            "last_error_at":     datetime.now(timezone.utc).isoformat(),
            "updated_at":        datetime.now(timezone.utc).isoformat(),
        }).eq("id", mat_id).execute()

        raise  # propaga para o caller diferenciar sucesso/falha


# ─────────────────────────────────────────────────────────────────────────────
# Runners
# ─────────────────────────────────────────────────────────────────────────────

def run_batch(sb: SupabaseClient, ai: OpenAI) -> int:
    """Processa um batch de materiais pendentes. Retorna quantos foram processados."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Pendentes que ainda não atingiram retry ou não têm next_retry_at
    result = (
        sb.table("study_materials")
        .select(
            "id, organization_id, title, material_type, source_url, storage_path, "
            "retry_count, next_retry_at"
        )
        .in_("processing_status", ["pending"])
        .or_(f"next_retry_at.is.null,next_retry_at.lte.{now_iso}")
        .order("created_at", desc=False)
        .limit(BATCH_SIZE)
        .execute()
    )

    materials = result.data or []
    if not materials:
        log.debug("Nenhum material pending encontrado.")
        return 0

    ok = 0
    for mat in materials:
        try:
            process_material(sb, ai, mat)
            ok += 1
        except Exception:
            pass  # erro já logado e persistido dentro de process_material

    return ok


def run_single(sb: SupabaseClient, ai: OpenAI, material_id: str) -> None:
    """Processa um material específico pelo ID."""
    result = (
        sb.table("study_materials")
        .select(
            "id, organization_id, title, material_type, source_url, storage_path, "
            "retry_count, next_retry_at"
        )
        .eq("id", material_id)
        .single()
        .execute()
    )

    if not result.data:
        log.error(f"Material não encontrado: {material_id}")
        sys.exit(1)

    mat = result.data
    # Força re-processo mesmo se já foi processado antes
    sb.table("study_materials").update({"processing_status": "pending"}).eq("id", material_id).execute()
    mat["processing_status"] = "pending"
    process_material(sb, ai, mat)


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Worker de ingestão de estudos Vuno Trader")
    parser.add_argument("--id",   help="Processa apenas o material com este UUID")
    parser.add_argument("--loop", action="store_true", help="Executa em loop contínuo (daemon)")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórias.")
        sys.exit(1)

    if not OPENAI_API_KEY:
        log.error("OPENAI_API_KEY é obrigatória.")
        sys.exit(1)

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai = build_openai_client()

    if args.id:
        run_single(sb, ai, args.id)
        return

    if args.loop:
        log.info(f"Iniciando worker em loop (intervalo: {LOOP_INTERVAL}s)…")
        while True:
            try:
                processed = run_batch(sb, ai)
                if processed:
                    log.info(f"Batch concluído: {processed} material(is) processado(s).")
            except Exception as e:
                log.error(f"Erro no loop: {e}")
            time.sleep(LOOP_INTERVAL)
    else:
        processed = run_batch(sb, ai)
        log.info(f"Concluído: {processed} material(is) processado(s).")


if __name__ == "__main__":
    main()
