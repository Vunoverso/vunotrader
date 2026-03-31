import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";
import ReprocessButton from "./reprocess-button";

const STATUS_STYLES: Record<string, string> = {
  pending:    "border-yellow-500/30 bg-yellow-500/20 text-yellow-300",
  processing: "border-sky-500/30 bg-sky-500/20 text-sky-300",
  processed:  "border-emerald-500/30 bg-emerald-500/20 text-emerald-300",
  error:      "border-red-500/30 bg-red-500/20 text-red-300",
};

const STATUS_LABELS: Record<string, string> = {
  pending:    "Pendente",
  processing: "Processando",
  processed:  "Processado",
  error:      "Erro",
};

const TYPE_LABELS: Record<string, string> = {
  pdf:       "PDF",
  video_url: "YouTube",
  note:      "Nota",
};

export default async function EstudoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) return <PlanGateCard moduleName="Estudos" />;

  // Resolve organização do usuário
  const { data: profile } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .single();

  let organizationId: string | null = null;
  if (profile) {
    const { data: member } = await supabase
      .from("organization_members")
      .select("organization_id")
      .eq("profile_id", profile.id)
      .limit(1)
      .single();
    organizationId = member?.organization_id ?? null;
  }

  if (!organizationId) return notFound();

  // Material — verifica pertencer à org do usuário autenticado
  const { data: material } = await supabase
    .from("study_materials")
    .select(
      "id, title, material_type, source_url, summary, processing_status, processing_error, processed_at, created_at"
    )
    .eq("id", id)
    .eq("organization_id", organizationId)
    .single();

  if (!material) return notFound();

  // Chunks de RAG
  const { data: chunksRaw } = await supabase
    .from("study_material_chunks")
    .select("id, chunk_index, content, token_estimate")
    .eq("material_id", id)
    .order("chunk_index", { ascending: true });

  const chunks = chunksRaw ?? [];
  const totalTokens = chunks.reduce(
    (sum, c) => sum + ((c.token_estimate as number | null) ?? 0),
    0
  );

  const statusStyle =
    STATUS_STYLES[material.processing_status ?? ""] ??
    "border-slate-600 bg-slate-700 text-slate-400";
  const statusLabel =
    STATUS_LABELS[material.processing_status ?? ""] ??
    (material.processing_status ?? "—");
  const typeLabel =
    TYPE_LABELS[material.material_type ?? ""] ??
    (material.material_type ?? "—");

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <Link href="/app/estudos" className="hover:text-sky-400 transition-colors">
          Estudos
        </Link>
        <span>/</span>
        <span className="truncate max-w-xs text-slate-300">{material.title}</span>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold text-slate-100">{material.title}</h1>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">
              {typeLabel}
            </span>
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${statusStyle}`}
            >
              {statusLabel}
            </span>
            {material.processed_at && (
              <span className="text-[10px] text-slate-600">
                Processado em{" "}
                {new Date(material.processed_at).toLocaleDateString("pt-BR")}
              </span>
            )}
          </div>
        </div>
        <ReprocessButton materialId={material.id} />
      </div>

      {/* Erro de processamento */}
      {material.processing_error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
          <p className="mb-1 text-xs font-medium text-red-400">
            Erro de processamento
          </p>
          <p className="font-mono text-xs text-red-300/80">
            {material.processing_error}
          </p>
        </div>
      )}

      {/* Fonte */}
      {material.source_url && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-5 py-3">
          <p className="mb-0.5 text-xs text-slate-500">Fonte</p>
          <a
            href={material.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all text-sm text-sky-400 hover:underline"
          >
            {material.source_url}
          </a>
        </div>
      )}

      {/* Resumo */}
      {material.summary ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-5 py-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Resumo gerado pela IA
          </p>
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">
            {material.summary}
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-5 py-4">
          <p className="text-sm text-slate-600">
            Sem resumo. Reprocesse o material para gerar.
          </p>
        </div>
      )}

      {/* Chunks */}
      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-200">
            Fragmentos de conhecimento
          </h2>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span>{chunks.length} fragmentos</span>
            {totalTokens > 0 && <span>~{totalTokens.toLocaleString("pt-BR")} tokens</span>}
          </div>
        </div>

        {chunks.length === 0 ? (
          <div className="px-5 py-8 text-center">
            <p className="text-sm text-slate-600">
              Nenhum fragmento gerado. Reprocesse para criar os chunks de RAG.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {chunks.map((chunk) => (
              <details key={chunk.id} className="group">
                <summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-3 hover:bg-slate-800/40 transition-colors">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-slate-800 text-[10px] font-bold text-slate-500">
                    {(chunk.chunk_index as number) + 1}
                  </span>
                  <p className="flex-1 truncate text-sm text-slate-400">
                    {(chunk.content as string).slice(0, 120)}
                    {(chunk.content as string).length > 120 ? "…" : ""}
                  </p>
                  <span className="shrink-0 text-[10px] text-slate-600">
                    ~{chunk.token_estimate} tokens
                  </span>
                  <svg
                    className="h-3.5 w-3.5 shrink-0 text-slate-600 transition-transform group-open:rotate-180"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </summary>
                <div className="px-5 pb-4 pt-1">
                  <p className="whitespace-pre-line text-sm leading-relaxed text-slate-400">
                    {chunk.content as string}
                  </p>
                </div>
              </details>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
