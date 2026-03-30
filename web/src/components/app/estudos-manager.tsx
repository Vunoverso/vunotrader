"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

const STUDY_BUCKET = process.env.NEXT_PUBLIC_SUPABASE_STUDY_BUCKET ?? "training-videos";
const STATUS_POLL_INTERVAL_MS = 15000;

type MaterialType = "video_url" | "pdf" | "note";
type ProcessingStatus = "pending" | "processing" | "processed" | "error";

export interface EstudoItem {
  id: string;
  title: string;
  material_type: MaterialType;
  source_url: string | null;
  storage_path: string | null;
  summary: string | null;
  processing_status: ProcessingStatus | null;
  processing_error: string | null;
  processed_at: string | null;
  created_at: string;
}

function typeLabel(type: MaterialType) {
  if (type === "video_url") return "Video";
  if (type === "pdf") return "PDF";
  return "Nota";
}

function typeClasses(type: MaterialType) {
  if (type === "video_url") return "border-blue-500/40 bg-blue-500/10 text-blue-300";
  if (type === "pdf") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
  return "border-slate-500/40 bg-slate-500/10 text-slate-300";
}

function processingLabel(status: ProcessingStatus | null) {
  if (!status) return "Pendente";
  if (status === "processing") return "Processando";
  if (status === "processed") return "Processado";
  if (status === "error") return "Erro";
  return "Pendente";
}

function processingClasses(status: ProcessingStatus | null) {
  if (status === "processing") return "border-amber-500/40 bg-amber-500/10 text-amber-300";
  if (status === "processed") return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300";
  if (status === "error") return "border-red-500/40 bg-red-500/10 text-red-300";
  return "border-slate-500/40 bg-slate-500/10 text-slate-300";
}

function friendlyProcessingError(message: string | null) {
  if (!message) return null;

  const normalized = message.trim();
  const lower = normalized.toLowerCase();

  if (lower.includes("no element found") || lower.includes("parseerror")) {
    return "Nao foi possivel ler a transcricao deste video agora. Tente novamente mais tarde ou use outro link do YouTube.";
  }
  if (lower.includes("transcricao vazia")) {
    return "Nao encontramos conteudo suficiente na transcricao deste video para processar o material.";
  }
  if (lower.includes("url de video nao suportada")) {
    return "Este link ainda nao e compativel com a transcricao automatica. Use um video publico do YouTube.";
  }
  if (lower.includes("nao foi possivel extrair texto do pdf")) {
    return "Nao conseguimos extrair texto deste PDF. Verifique se o arquivo nao esta vazio, corrompido ou protegido.";
  }

  return normalized;
}

function formatDate(iso: string) {
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function safeFileName(name: string) {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_");
}

export default function EstudosManager({
  userId,
  organizationId,
  initialItems,
}: {
  userId: string;
  organizationId: string | null;
  initialItems: EstudoItem[];
}) {
  const [items, setItems] = useState<EstudoItem[]>(initialItems);
  const [videoTitle, setVideoTitle] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [pdfTitle, setPdfTitle] = useState("");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [busy, setBusy] = useState<"none" | "video" | "pdf">("none");
  const [status, setStatus] = useState<{ kind: "idle" | "ok" | "error"; text: string }>({ kind: "idle", text: "" });
  const [refreshing, setRefreshing] = useState(false);

  const hasOrg = useMemo(() => Boolean(organizationId), [organizationId]);

  const refreshItems = useCallback(async (silent = false) => {
    if (!organizationId) return;

    setRefreshing(true);
    const supabase = createClient();

    const { data, error } = await supabase
      .from("study_materials")
      .select("id, title, material_type, source_url, storage_path, summary, processing_status, processing_error, processed_at, created_at")
      .eq("organization_id", organizationId)
      .order("created_at", { ascending: false })
      .limit(100);

    setRefreshing(false);

    if (error) {
      if (!silent) {
        setStatus({ kind: "error", text: "Falha ao atualizar status dos materiais." });
      }
      return;
    }

    setItems((data ?? []) as EstudoItem[]);
  }, [organizationId]);

  useEffect(() => {
    if (!organizationId) return;

    const hasPendingWork = items.some(
      (item) => !item.processing_status || item.processing_status === "pending" || item.processing_status === "processing",
    );

    if (!hasPendingWork) return;

    const timer = window.setInterval(() => {
      void refreshItems(true);
    }, STATUS_POLL_INTERVAL_MS);

    return () => window.clearInterval(timer);
  }, [items, organizationId, refreshItems]);

  async function addVideo() {
    if (!organizationId) {
      setStatus({ kind: "error", text: "Usuário sem organização vinculada." });
      return;
    }
    if (!videoTitle.trim() || !videoUrl.trim()) {
      setStatus({ kind: "error", text: "Informe título e URL do vídeo." });
      return;
    }

    setBusy("video");
    setStatus({ kind: "idle", text: "" });
    const supabase = createClient();

    const { data, error } = await supabase
      .from("study_materials")
      .insert({
        organization_id: organizationId,
        user_id: userId,
        material_type: "video_url",
        title: videoTitle.trim(),
        source_url: videoUrl.trim(),
        processing_status: "pending",
        processing_error: null,
        processed_at: null,
      })
      .select("id, title, material_type, source_url, storage_path, summary, processing_status, processing_error, processed_at, created_at")
      .single();

    setBusy("none");
    if (error || !data) {
      setStatus({ kind: "error", text: "Falha ao salvar vídeo. Verifique permissões RLS." });
      return;
    }

    setItems((prev) => [data as EstudoItem, ...prev]);
    setVideoTitle("");
    setVideoUrl("");
    setStatus({ kind: "ok", text: "Vídeo salvo com sucesso." });
  }

  async function addPdf() {
    if (!organizationId) {
      setStatus({ kind: "error", text: "Usuário sem organização vinculada." });
      return;
    }
    if (!pdfTitle.trim() || !pdfFile) {
      setStatus({ kind: "error", text: "Informe título e selecione um PDF." });
      return;
    }
    if (pdfFile.type !== "application/pdf") {
      setStatus({ kind: "error", text: "Apenas arquivos PDF são aceitos." });
      return;
    }

    setBusy("pdf");
    setStatus({ kind: "idle", text: "" });
    const supabase = createClient();

    const { data: inserted, error: insertError } = await supabase
      .from("study_materials")
      .insert({
        organization_id: organizationId,
        user_id: userId,
        material_type: "pdf",
        title: pdfTitle.trim(),
        processing_status: "pending",
        processing_error: null,
        processed_at: null,
      })
      .select("id, title, material_type, source_url, storage_path, summary, processing_status, processing_error, processed_at, created_at")
      .single();

    if (insertError || !inserted) {
      setBusy("none");
      setStatus({ kind: "error", text: "Falha ao criar registro do PDF." });
      return;
    }

    const path = `${organizationId}/${inserted.id}/${safeFileName(pdfFile.name)}`;
    const { error: uploadError } = await supabase.storage
      .from(STUDY_BUCKET)
      .upload(path, pdfFile, { upsert: true, contentType: "application/pdf" });

    if (uploadError) {
      await supabase.from("study_materials").delete().eq("id", inserted.id);
      setBusy("none");
      setStatus({
        kind: "error",
        text: `Falha no upload. Crie/verifique o bucket ${STUDY_BUCKET} no Supabase Storage.`,
      });
      return;
    }

    const { data: updated, error: updateError } = await supabase
      .from("study_materials")
      .update({ storage_path: path, processing_status: "pending", processing_error: null, processed_at: null })
      .eq("id", inserted.id)
      .select("id, title, material_type, source_url, storage_path, summary, processing_status, processing_error, processed_at, created_at")
      .single();

    setBusy("none");

    if (updateError || !updated) {
      setStatus({ kind: "error", text: "Upload concluído, mas falhou ao atualizar metadados do PDF." });
      return;
    }

    setItems((prev) => [updated as EstudoItem, ...prev]);
    setPdfTitle("");
    setPdfFile(null);
    setStatus({ kind: "ok", text: "PDF enviado com sucesso." });
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-bold text-slate-100">Estudos</h1>
        <p className="text-sm text-slate-500">
          Adicione vídeos e PDFs para montar sua base de estudo e contexto da IA.
        </p>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => void refreshItems(false)}
          disabled={!hasOrg || refreshing}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-slate-600 hover:text-slate-100 disabled:opacity-50"
        >
          {refreshing ? "Atualizando..." : "Atualizar status"}
        </button>
      </div>

      {!hasOrg && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Este usuário não tem organização vinculada. Sem organization_id não é possível salvar estudos.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Adicionar vídeo (URL)</h2>
          <input
            value={videoTitle}
            onChange={(e) => setVideoTitle(e.target.value)}
            placeholder="Título do material"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
          <input
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="https://..."
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
          <button
            type="button"
            onClick={addVideo}
            disabled={!hasOrg || busy !== "none"}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50"
          >
            {busy === "video" ? "Salvando..." : "Salvar vídeo"}
          </button>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Upload de PDF</h2>
          <input
            value={pdfTitle}
            onChange={(e) => setPdfTitle(e.target.value)}
            placeholder="Título do PDF"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setPdfFile(e.target.files?.[0] ?? null)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 file:mr-3 file:rounded file:border-0 file:bg-slate-700 file:px-3 file:py-1 file:text-xs file:text-slate-100"
          />
          <button
            type="button"
            onClick={addPdf}
            disabled={!hasOrg || busy !== "none"}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {busy === "pdf" ? "Enviando..." : "Enviar PDF"}
          </button>
        </section>
      </div>

      {status.kind !== "idle" && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            status.kind === "ok"
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
              : "border-red-500/40 bg-red-500/10 text-red-300"
          }`}
        >
          {status.text}
        </div>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <div className="border-b border-slate-800 px-5 py-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Materiais cadastrados</h2>
        </div>

        {items.length === 0 ? (
          <div className="px-5 py-12 text-center text-sm text-slate-500">
            Nenhum material cadastrado ainda.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {items.map((item) => (
              <div key={item.id} className="px-5 py-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${typeClasses(item.material_type)}`}>
                      {typeLabel(item.material_type)}
                    </span>
                    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${processingClasses(item.processing_status)}`}>
                      {processingLabel(item.processing_status)}
                    </span>
                    <p className="text-sm font-medium text-slate-100">{item.title}</p>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{formatDate(item.created_at)}</p>
                  {item.processed_at && (
                    <p className="mt-1 text-[11px] text-emerald-300/80">Processado em {formatDate(item.processed_at)}</p>
                  )}
                  {item.processing_status === "error" && item.processing_error && (
                    <p className="mt-1 text-[11px] text-red-300">{friendlyProcessingError(item.processing_error)}</p>
                  )}
                </div>

                <div className="text-xs text-slate-400">
                  {item.material_type === "video_url" && item.source_url && (
                    <a href={item.source_url} target="_blank" rel="noreferrer" className="text-sky-400 hover:text-sky-300">
                      Abrir vídeo
                    </a>
                  )}
                  {item.material_type === "pdf" && item.storage_path && (
                    <span className="text-slate-400">{item.storage_path}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
