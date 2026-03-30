import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";

// ── Cards de métrica ─────────────────────────────────────────
function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "green" | "red" | "sky" | "slate";
}) {
  const colors = {
    green: "text-emerald-400",
    red: "text-red-400",
    sky: "text-sky-400",
    slate: "text-slate-300",
  };
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 px-5 py-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colors[accent ?? "slate"]}`}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
    </div>
  );
}

// ── Tabela de operações recentes ─────────────────────────────
function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-slate-600">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-6 w-6">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
        </svg>
      </div>
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

// ── Badge status do robô ─────────────────────────────────────
function RobotStatusBadge({ mode }: { mode: "observer" | "demo" | "real" | "inactive" }) {
  const map = {
    observer: { label: "Observador", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
    demo:     { label: "Demo",       color: "bg-sky-500/20 text-sky-400 border-sky-500/30" },
    real:     { label: "Real",       color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    inactive: { label: "Inativo",    color: "bg-slate-700 text-slate-400 border-slate-600" },
  };
  const s = map[mode];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${s.color}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${mode !== "inactive" ? "animate-pulse" : ""} ${
        mode === "observer" ? "bg-yellow-400" :
        mode === "demo"     ? "bg-sky-400" :
        mode === "real"     ? "bg-emerald-400" : "bg-slate-500"
      }`} />
      {s.label}
    </span>
  );
}

// ── Página ────────────────────────────────────────────────────
export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const access = user ? await getSubscriptionAccess(supabase, user.id) : null;

  // Métricas reais virão do banco quando o brain estiver conectado
  // Por ora, estrutura preparada com dados placeholder
  const metrics = {
    totalTrades: 0,
    winRate: null as number | null,
    pnl: 0,
    openTrades: 0,
    robotMode: "inactive" as const,
  };

  const firstName = user?.user_metadata?.full_name?.split(" ")[0] ?? "Trader";

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">
            Olá, {firstName} 👋
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Resumo rápido do seu robô hoje
          </p>
        </div>
        <RobotStatusBadge mode={metrics.robotMode} />
      </div>

      <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">
        Seu robô ainda não começou a operar. Faça a conexão em modo demo para ativar.
        <a href="/app/instalacao" className="ml-2 font-semibold text-sky-300 hover:underline">Abrir instalação</a>
      </div>

      {/* Métricas principais */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Hoje"
          value={metrics.totalTrades.toString()}
          sub="Operações"
          accent="slate"
        />
        <MetricCard
          label="Acerto"
          value={metrics.winRate !== null ? `${metrics.winRate}%` : "—"}
          sub="Taxa atual"
          accent={
            metrics.winRate === null ? "slate"
            : metrics.winRate >= 60 ? "green"
            : "red"
          }
        />
        <MetricCard
          label="Resultado"
          value={
            metrics.pnl === 0
              ? "R$ 0,00"
              : metrics.pnl > 0
              ? `+R$ ${metrics.pnl.toFixed(2)}`
              : `-R$ ${Math.abs(metrics.pnl).toFixed(2)}`
          }
          sub="Dia atual"
          accent={metrics.pnl > 0 ? "green" : metrics.pnl < 0 ? "red" : "slate"}
        />
        <MetricCard
          label="Abertas"
          value={metrics.openTrades.toString()}
          sub="Agora"
          accent={metrics.openTrades > 0 ? "sky" : "slate"}
        />
      </div>

      {/* Seção de operações recentes */}
      <div className="rounded-xl bg-slate-900 border border-slate-800">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-200">
            Operações recentes
          </h2>
          <a
            href="/app/operacoes"
            className="text-xs text-sky-500 hover:text-sky-400 hover:underline"
          >
            Ver todas →
          </a>
        </div>
        <EmptyState message="Ainda não recebemos operações. Finalize a conexão em Instalação para começar." />
      </div>

      {/* Seção de status do sistema */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Brain Python */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-slate-400">Inteligência</p>
            <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-500">Off</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Ainda sem comunicação com a plataforma.
            Conecte em modo demo para ativar.
            <a href="/app/instalacao" className="ml-1 text-sky-500 hover:underline">Ver passo a passo</a>
          </p>
        </div>

        {/* MT5 EA */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-slate-400">MetaTrader</p>
            <span className="rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-500">Off</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            O MT5 ainda não enviou dados.
            Verifique EA no gráfico e AutoTrading ligado.
          </p>
        </div>

        {/* Plano */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-slate-400">Plano atual</p>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] ${access?.hasActivePlan ? "bg-emerald-500/20 border-emerald-500/30 text-emerald-300" : access?.isTrialing ? "bg-amber-500/20 border-amber-500/30 text-amber-300" : "bg-slate-700 border-slate-600 text-slate-400"}`}>
              {access?.hasActivePlan ? "Ativo" : access?.isTrialing ? `Trial (${access.trialDaysLeft}d)` : "Sem plano"}
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {access?.hasActivePlan ? (
              <>
                Ajuste metas e risco em{" "}
                <a href="/app/parametros" className="text-sky-500 hover:underline">
                  Parâmetros
                </a>.
              </>
            ) : (
              <>
                Ative um plano para liberar Operações, Parâmetros, Auditoria e Estudos em{" "}
                <a href="/app/assinatura" className="text-sky-500 hover:underline">
                  Assinatura
                </a>.
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
