from __future__ import annotations

import argparse
import io
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse

from openai import OpenAI
from pypdf import PdfReader
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.supabase import get_service_supabase


log = logging.getLogger("study-ingestion-worker")


@dataclass
class WorkerConfig:
    bucket: str = os.getenv("STUDY_BUCKET", "training-videos")
    poll_seconds: int = int(os.getenv("STUDY_WORKER_POLL_SECONDS", "30"))
    batch_size: int = int(os.getenv("STUDY_WORKER_BATCH_SIZE", "10"))
    summary_model: str = os.getenv("STUDY_SUMMARY_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("STUDY_EMBEDDING_MODEL", "text-embedding-3-small")
    max_extract_chars: int = int(os.getenv("STUDY_MAX_EXTRACT_CHARS", "40000"))
    chunk_size: int = int(os.getenv("STUDY_CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(os.getenv("STUDY_CHUNK_OVERLAP", "150"))


def _clean_text(value: str) -> str:
    value = value.replace("\u0000", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _extract_pdf_text(pdf_bytes: bytes, max_chars: int) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pieces: list[str] = []
    total = 0

    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""

        text = _clean_text(text)
        if not text:
            continue

        pieces.append(text)
        total += len(text)
        if total >= max_chars:
            break

    return _clean_text("\n".join(pieces))[:max_chars]


def _youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        return parsed.path.strip("/") or None
    if "youtube.com" in host:
        query = parse_qs(parsed.query)
        if "v" in query and query["v"]:
            return query["v"][0]
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"embed", "shorts"}:
            return parts[1]
    return None


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    text = _clean_text(text)
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    length = len(text)
    overlap = max(0, min(overlap, size - 1))

    while start < length:
        end = min(length, start + size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = max(0, end - overlap)

    return chunks


def _is_transient_error(exc: Exception) -> bool:
    """Identifica se o erro eh transitorio e merece retry, ou permanente."""
    message = str(exc).lower()
    exc_type_name = exc.__class__.__name__.lower()
    
    # Erros permanentes (nao merece retry):
    permanent_indicators = [
        "pdf sem storage_path",
        "video sem source_url",
        "url de video nao suportada",
        "tipo de material nao suportado",
        "nao foi possivel extrair texto do pdf",  # PDF corrompido/vazio
        "transcricao vazia",  # Video sem conteudo
    ]
    for indicator in permanent_indicators:
        if indicator in message:
            return False
    
    # Erros transitorios (merece retry):
    transient_indicators = [
        "rate limit",
        "quota exceeded",
        "timeout",
        "connection",
        "temporarily unavailable",
        "service unavailable",
        "500",
        "502",
        "503",
        "no element found",  # API do YouTube demorando/falhando
        "http error",
        "read timed out",
        "broken pipe",
    ]
    for indicator in transient_indicators:
        if indicator in message:
            return True
        if indicator in exc_type_name:
            return True
    
    # Padroes conhecidos de biblioteca
    if "ConnectionError" in exc_type_name or "urllib3" in message:
        return True
    if "socket.timeout" in message or "ConnectTimeout" in exc_type_name:
        return True
    
    # Por padrao, assume transitorio para ser mais resiliente
    return True


def _friendly_processing_error(exc: Exception, material_type: str | None = None) -> str:
    message = _clean_text(str(exc)) or exc.__class__.__name__
    lower_message = message.lower()

    # Erros de transcricao YouTube
    if "no element found" in lower_message or "parseerror" in lower_message:
        return "Nao foi possivel ler a transcricao deste video agora. Tente novamente mais tarde ou use outro link do YouTube."
    if "transcricao vazia" in lower_message:
        return "Nao encontramos conteudo suficiente na transcricao deste video para processar o material."
    
    # Erros de URL/compatibilidade
    if "url de video nao suportada" in lower_message or "invalid video id" in lower_message:
        return "Este link de video ainda nao e compativel com a transcricao automatica. Use um video publico do YouTube."
    if "video privado" in lower_message or "video is unavailable" in lower_message:
        return "Este video este privado ou foi removido. Use outro link do YouTube com conteudo publico."
    if "video sem source_url" in lower_message:
        return "O link do video nao foi encontrado. Edite o material e tente novamente."
    
    # Erros de PDF
    if "pdf sem storage_path" in lower_message:
        return "O arquivo PDF nao foi localizado no armazenamento. Envie o arquivo novamente."
    if "nao foi possivel extrair texto do pdf" in lower_message:
        return "Nao conseguimos extrair texto deste PDF. Verifique se o arquivo nao esta vazio, corrompido ou protegido."
    if "pdf corrompido" in lower_message or "corrupted pdf" in lower_message:
        return "Este arquivo PDF esta corrompido. Tente enviar outro arquivo."
    
    # Erros de storage/acesso
    if "permission" in lower_message or "not authorized" in lower_message or "access denied" in lower_message:
        return "O material nao pode ser processado por falta de permissao de acesso."
    if "storage" in lower_message and "not found" in lower_message:
        return "O arquivo nao foi encontrado no armazenamento. Tente enviar novamente."
    
    # Erros de IA/API
    if "openai_api_key" in lower_message:
        return "A configuracao da IA de estudos ainda nao foi concluida no ambiente."
    if "rate limit" in lower_message or "quota" in lower_message or "exceeded" in lower_message:
        return "O servico de IA atingiu o limite temporariamente. Tente novamente em alguns minutos."
    
    # Erros de conexao/timeout (transitorios)
    if "timeout" in lower_message or "timed out" in lower_message:
        return "O processamento demorou mais do que o esperado. Tente novamente em instantes."
    if "connection" in lower_message or "connectionerror" in lower_message:
        return "Falha de conexao ao processar o material. Tente novamente em poucos minutos."
    if "http error" in lower_message or (lower_message.startswith("5") and lower_message[0].isdigit()):
        return "Um erro temporario ocorreu no servico. Tente novamente em instantes."
    
    # Erros genéricos por tipo
    if material_type == "video_url":
        return "Nao foi possivel processar este video agora. Tente novamente mais tarde."
    if material_type == "pdf":
        return "Nao foi possivel processar este PDF agora. Tente novamente mais tarde."
    return "Nao foi possivel processar este material agora. Tente novamente mais tarde."


class AIService:
    def __init__(self, summary_model: str, embedding_model: str):
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY nao configurada para pipeline de IA de estudos")

        self.client = OpenAI(api_key=api_key)
        self.summary_model = summary_model
        self.embedding_model = embedding_model

    def summarize_and_keywords(self, title: str, text: str) -> tuple[str, list[str], int]:
        prompt = (
            "Voce recebe um material de estudo para robo trader. "
            "Responda APENAS em JSON valido com as chaves: summary (string), keywords (array de ate 10 termos). "
            "Resumo em portugues, focado em sinais, risco, contexto e regras praticas."
        )

        completion = self.client.chat.completions.create(
            model=self.summary_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": f"Titulo: {title}\n\nConteudo:\n{text[:12000]}",
                },
            ],
        )

        raw = completion.choices[0].message.content or "{}"
        data = json.loads(raw)
        summary = _clean_text(str(data.get("summary", "")))
        keywords_raw = data.get("keywords") or []
        keywords = [
            _clean_text(str(k)).lower()
            for k in keywords_raw
            if _clean_text(str(k))
        ][:10]

        usage = completion.usage.total_tokens if completion.usage else 0
        return summary, keywords, usage

    def embed(self, text: str) -> tuple[list[float], int]:
        emb = self.client.embeddings.create(model=self.embedding_model, input=text)
        vector = list(emb.data[0].embedding)
        usage = emb.usage.total_tokens if emb.usage else 0
        return vector, usage


class StudyIngestionWorker:
    def __init__(self, config: WorkerConfig | None = None):
        self.config = config or WorkerConfig()
        self.supabase = get_service_supabase()
        self.ai = AIService(self.config.summary_model, self.config.embedding_model)

    def _set_status(self, material_id: str, status: str, error: str | None = None) -> None:
        payload: dict[str, Any] = {
            "processing_status": status,
            "processing_error": error,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if status == "processed":
            payload["processed_at"] = payload["updated_at"]
            # Tenta resetar retry_count
            try:
                payload["retry_count"] = 0
                payload["next_retry_at"] = None
                payload["last_error_at"] = None
            except Exception:
                pass  # Campos de retry podem nao existir ainda

        self.supabase.table("study_materials").update(payload).eq("id", material_id).execute()
    
    def _schedule_retry(self, material_id: str, retry_count: int, error: str | None = None, is_permanent: bool = False) -> None:
        """Agenda retry com backoff exponencial ou marca como erro permanente."""
        now_dt = time.gmtime()
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", now_dt)
        
        if is_permanent or retry_count >= 5:  # Max 5 retries
            # Erro permanente ou excedeu tentativas
            self._set_status(material_id, "error", error)
            log.warning("Material %s marcado como erro permanente (retry_count=%d)", material_id, retry_count)
            return
        
        # Backoff exponencial: 2^retry_count segundos
        backoff_seconds = 2 ** retry_count
        next_retry_ts = time.gmtime(time.time() + backoff_seconds)
        next_retry_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", next_retry_ts)
        
        payload: dict[str, Any] = {
            "processing_status": "error",  # Fica como erro temporario
            "processing_error": error,
            "updated_at": now_str,
        }
        
        # Tenta adicionar campos de retry (backwards compat)
        try:
            payload["retry_count"] = retry_count + 1
            payload["next_retry_at"] = next_retry_str
            payload["last_error_at"] = now_str
        except Exception:
            pass  # Campos de retry podem nao existir ainda
        
        self.supabase.table("study_materials").update(payload).eq("id", material_id).execute()
        log.info(
            "Material %s agendado para retry (tentativa %d, proximo em %ds)",
            material_id,
            retry_count + 1,
            backoff_seconds,
        )

    def _load_pending(self) -> list[dict[str, Any]]:
        """Carrega materiais pendentes, respeitando retry_count e backoff."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        # Tenta carregar com novos campos de retry; se falhar, carrega sem eles (backwards compat)
        try:
            # Novo formato com suporte a retry
            resp = (
                self.supabase.table("study_materials")
                .select(
                    "id, organization_id, user_id, material_type, title, source_url, storage_path, summary, extracted_text, "
                    "processing_status, retry_count, next_retry_at, last_error_at"
                )
                .in_("processing_status", ["pending", "error"])
                .execute()
            )
            
            items = list(resp.data or [])
            # Filtra apenas itens nao agendados para retry no futuro
            ready = [
                item for item in items
                if not item.get("next_retry_at") or item.get("next_retry_at") <= now
            ]
        except Exception as e:
            # Fallback para versao anterior (sem retry_count/next_retry_at)
            if "does not exist" in str(e) or "retry_count" in str(e):
                log.warning("Retry columns not yet migrated, loading without retry support: %s", e)
                resp = (
                    self.supabase.table("study_materials")
                    .select(
                        "id, organization_id, user_id, material_type, title, source_url, storage_path, summary, extracted_text, processing_status"
                    )
                    .in_("processing_status", ["pending", "error"])
                    .order("created_at", desc=False)
                    .limit(self.config.batch_size)
                    .execute()
                )
                return list(resp.data or [])
            else:
                raise
        
        return sorted(ready, key=lambda x: x.get("created_at", ""))[:self.config.batch_size]

    def _log_ai_usage(self, item: dict[str, Any], tokens: int, task_type: str) -> None:
        self.supabase.table("ai_usage_logs").insert(
            {
                "organization_id": item.get("organization_id"),
                "user_id": item.get("user_id"),
                "provider": "openai",
                "model_name": self.config.summary_model,
                "prompt_tokens": tokens,
                "completion_tokens": 0,
                "total_tokens": tokens,
                "estimated_cost": 0,
                "task_type": task_type,
            }
        ).execute()

    def _process_pdf(self, item: dict[str, Any]) -> str:
        storage_path = item.get("storage_path")
        if not storage_path:
            raise RuntimeError("PDF sem storage_path")

        pdf_bytes = self.supabase.storage.from_(self.config.bucket).download(storage_path)
        extracted = _extract_pdf_text(pdf_bytes, self.config.max_extract_chars)
        if not extracted:
            raise RuntimeError("Nao foi possivel extrair texto do PDF")
        return extracted

    def _process_video(self, item: dict[str, Any]) -> str:
        source_url = item.get("source_url")
        if not source_url:
            raise RuntimeError("Video sem source_url")

        video_id = _youtube_video_id(source_url)
        if not video_id:
            raise RuntimeError("URL de video nao suportada para transcricao automatica (use YouTube)")

        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["pt", "pt-BR", "en"])
        joined = " ".join(part.get("text", "") for part in transcript)
        extracted = _clean_text(joined)
        if not extracted:
            raise RuntimeError("Transcricao vazia para o video")
        return extracted[: self.config.max_extract_chars]

    def _upsert_chunks(self, item: dict[str, Any], text: str, keywords: list[str]) -> int:
        material_id = item["id"]
        org_id = item.get("organization_id")

        self.supabase.table("study_material_chunks").delete().eq("material_id", material_id).execute()

        chunks = _chunk_text(text, self.config.chunk_size, self.config.chunk_overlap)
        total_tokens = 0

        for idx, chunk in enumerate(chunks):
            emb, tokens = self.ai.embed(chunk)
            total_tokens += tokens

            self.supabase.table("study_material_chunks").insert(
                {
                    "organization_id": org_id,
                    "material_id": material_id,
                    "chunk_index": idx,
                    "content": chunk,
                    "summary": chunk[:220],
                    "semantic_keywords": keywords,
                    "embedding": emb,
                    "token_estimate": max(1, len(chunk) // 4),
                }
            ).execute()

        return total_tokens

    def process_one(self, item: dict[str, Any]) -> bool:
        material_id = item["id"]
        material_type = item.get("material_type")
        retry_count = item.get("retry_count", 0)

        try:
            self._set_status(material_id, "processing", None)

            if material_type == "pdf":
                extracted = self._process_pdf(item)
            elif material_type == "video_url":
                extracted = self._process_video(item)
            else:
                raise RuntimeError(f"Tipo de material nao suportado: {material_type}")

            summary, keywords, tokens_summary = self.ai.summarize_and_keywords(
                item.get("title") or "Material sem titulo",
                extracted,
            )

            tokens_embedding = self._upsert_chunks(item, extracted, keywords)

            self.supabase.table("study_materials").update(
                {
                    "extracted_text": extracted,
                    "summary": summary,
                    "processing_error": None,
                    "processing_status": "processed",
                    "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "retry_count": 0,
                    "next_retry_at": None,
                    "last_error_at": None,
                }
            ).eq("id", material_id).execute()

            total_tokens = tokens_summary + tokens_embedding
            self._log_ai_usage(item, total_tokens, "study_ingestion_rag")

            log.info("Material processado via IA: %s (%s)", material_id, material_type)
            return True
        except Exception as exc:
            friendly_msg = _friendly_processing_error(exc, material_type)[:500]
            is_permanent = not _is_transient_error(exc)
            
            self._schedule_retry(material_id, retry_count, friendly_msg, is_permanent=is_permanent)
            log.exception(
                "Falha ao processar material %s (retry_count=%d, permanent=%s): %s",
                material_id,
                retry_count,
                is_permanent,
                exc,
            )
            return False

    def run_once(self) -> int:
        items = self._load_pending()
        if not items:
            log.info("Nenhum material pendente.")
            return 0

        ok = 0
        for item in items:
            if self.process_one(item):
                ok += 1

        log.info("Ciclo concluido. Processados: %s/%s", ok, len(items))
        return ok

    def run_forever(self) -> None:
        log.info(
            "Worker IA iniciado. bucket=%s poll=%ss batch=%s summary_model=%s embedding_model=%s",
            self.config.bucket,
            self.config.poll_seconds,
            self.config.batch_size,
            self.config.summary_model,
            self.config.embedding_model,
        )
        while True:
            self.run_once()
            time.sleep(self.config.poll_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Worker de ingestao de estudos com IA")
    parser.add_argument("--once", action="store_true", help="Executa apenas um ciclo")
    parser.add_argument("--poll", type=int, default=None, help="Intervalo em segundos")
    parser.add_argument("--batch", type=int, default=None, help="Quantidade por ciclo")
    parser.add_argument("--bucket", type=str, default=None, help="Bucket de storage")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    args = parse_args()
    cfg = WorkerConfig()
    if args.poll is not None:
        cfg.poll_seconds = max(5, args.poll)
    if args.batch is not None:
        cfg.batch_size = max(1, args.batch)
    if args.bucket:
        cfg.bucket = args.bucket

    worker = StudyIngestionWorker(cfg)

    if args.once:
        worker.run_once()
        return

    worker.run_forever()


if __name__ == "__main__":
    main()
