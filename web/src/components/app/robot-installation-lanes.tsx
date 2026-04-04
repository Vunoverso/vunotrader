interface InstallationAccess {
  hasActivePlan: boolean;
  isTrialing: boolean;
  trialDaysLeft: number;
  planCode: string | null;
  features: Record<string, boolean>;
}

export default function RobotInstallationLanes({ access }: { access: InstallationAccess | null }) {
  const planCode = access?.planCode ?? null;
  const visualHybridEnabled = Boolean(
    access?.features?.["robot.visual_hybrid"] && access?.features?.["robot.visual_shadow"]
  );

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Linhas de robo</h2>
          <p className="mt-2 text-sm text-slate-400">
            O produto passa a se organizar em duas linhas: a operacional oficial e a linha visual assistida.
          </p>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-[11px] font-semibold text-slate-300">
          {access?.hasActivePlan
            ? `Plano ${planCode?.toUpperCase() ?? "ATIVO"}`
            : access?.isTrialing
            ? `Trial ${access.trialDaysLeft}d`
            : "Sem plano ativo"}
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <article className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-100">Robo Integrado</h3>
            <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
              Disponivel hoje
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-300">
            Linha oficial com bridge local, heartbeat, auditoria e execucao baseada em snapshot estruturado.
          </p>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-400" />Pacote por instancia</li>
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-400" />Bridge local entre MT5 e backend</li>
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-400" />Trilha operacional oficial</li>
          </ul>
        </article>

        <article className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-100">Robo Hibrido Visual</h3>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
              visualHybridEnabled
                ? "border-sky-500/30 bg-sky-500/10 text-sky-300"
                : "border-amber-500/30 bg-amber-500/10 text-amber-300"
            }`}>
              {visualHybridEnabled ? "Liberado no seu plano" : "Requer entitlement visual"}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-300">
            Usa a mesma base do Robo Integrado, adicionando screenshot, leitura visual e shadow mode para auditoria e experiencia.
          </p>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />Leitura visual lado a lado com a estruturada</li>
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />Shadow mode antes de qualquer influencia operacional</li>
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-sky-400" />Rollout controlado no plano Pro+</li>
          </ul>
        </article>

        <article className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-100">Laboratorio Python</h3>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] font-semibold text-slate-400">
              Avancado
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-300">
            Caminho tecnico para testes locais, scanner multiativos e experimentacao. Nao e a linha principal do produto.
          </p>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-500" />Uso manual por CMD</li>
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-500" />Valido para homologacao tecnica</li>
            <li className="flex items-start gap-2"><span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-500" />Fora do onboarding padrao do cliente</li>
          </ul>
        </article>
      </div>
    </section>
  );
}
