interface DashboardRobotLanesProps {
  hasActivePlan: boolean;
  features: Record<string, boolean>;
  motorOnline: boolean;
  instanceName: string | null;
  latestVisual: {
    cycle_id: string;
    visual_shadow_status: string;
    visual_alignment: string;
    visual_conflict_reason: string | null;
    visual_context: { summary?: string } | null;
    chart_image_url: string | null;
    created_at: string;
  } | null;
}

export default function RobotProductDashboardLanes({
  hasActivePlan,
  features,
  motorOnline,
  instanceName,
  latestVisual,
}: DashboardRobotLanesProps) {
  const visualHybridEnabled = Boolean(features["robot.visual_hybrid"] && features["robot.visual_shadow"]);
  const visualBadge = (() => {
    if (!latestVisual) return { label: "Sem ciclo visual", cls: "border-slate-700 bg-slate-900 text-slate-400" };
    if (latestVisual.visual_shadow_status === "skipped_non_chart_symbol") {
      return { label: "Fora do grafico", cls: "border-slate-600 bg-slate-900 text-slate-300" };
    }
    if (latestVisual.visual_alignment === "aligned") {
      return { label: "Shadow alinhado", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" };
    }
    if (latestVisual.visual_alignment === "divergent_high") {
      return { label: "Divergencia alta", cls: "border-rose-500/30 bg-rose-500/10 text-rose-300" };
    }
    if (latestVisual.visual_alignment === "divergent_low") {
      return { label: "Divergencia baixa", cls: "border-amber-500/30 bg-amber-500/10 text-amber-300" };
    }
    if (latestVisual.visual_shadow_status === "error") {
      return { label: "Shadow com erro", cls: "border-rose-500/30 bg-rose-500/10 text-rose-300" };
    }
    return { label: "Shadow pendente", cls: "border-sky-500/30 bg-sky-500/10 text-sky-300" };
  })();

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <article className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-emerald-300">Linha oficial</p>
            <h2 className="mt-1 text-sm font-semibold text-slate-100">Robo Integrado</h2>
          </div>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
            motorOnline
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-slate-700 bg-slate-900 text-slate-400"
          }`}>
            {motorOnline ? "Operando agora" : "Pronto para conectar"}
          </span>
        </div>
        <p className="mt-3 text-sm text-slate-300">
          Fluxo oficial baseado em bridge local, heartbeat, auditoria e comando estruturado.
          {instanceName ? ` Instancia atual: ${instanceName}.` : ""}
        </p>
      </article>

      <article className="rounded-xl border border-sky-500/20 bg-sky-500/5 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-sky-300">Linha visual</p>
            <h2 className="mt-1 text-sm font-semibold text-slate-100">Robo Hibrido Visual</h2>
          </div>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
            visualHybridEnabled
              ? "border-sky-500/30 bg-sky-500/10 text-sky-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300"
          }`}>
            {visualHybridEnabled ? "Liberado no seu plano" : hasActivePlan ? "Upgrade de entitlement" : "Pro+"}
          </span>
        </div>
        <p className="mt-3 text-sm text-slate-300">
          Adiciona screenshot, leitura visual em shadow mode e comparacao entre leitura estruturada e leitura visual.
        </p>
        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${visualBadge.cls}`}>
              {visualBadge.label}
            </span>
            {latestVisual?.cycle_id && (
              <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
                {latestVisual.cycle_id}
              </span>
            )}
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-[140px_minmax(0,1fr)]">
            <div className="overflow-hidden rounded-lg border border-slate-800 bg-slate-950/80">
              {latestVisual?.chart_image_url ? (
                <a href={latestVisual.chart_image_url} target="_blank" rel="noreferrer">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={latestVisual.chart_image_url} alt="Ultimo screenshot do shadow visual" className="h-24 w-full object-cover" />
                </a>
              ) : (
                <div className="flex h-24 items-center justify-center px-3 text-center text-[10px] uppercase tracking-widest text-slate-500">
                  Sem screenshot ainda
                </div>
              )}
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">Resumo do ultimo ciclo</p>
              <p className="mt-1 text-sm leading-relaxed text-slate-300">
                {latestVisual?.visual_context?.summary ?? "O shadow visual ainda nao registrou um ciclo com screenshot para esta instancia."}
              </p>
              {latestVisual?.visual_conflict_reason && (
                <p className="mt-2 text-xs leading-relaxed text-amber-300">
                  {latestVisual.visual_conflict_reason}
                </p>
              )}
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}