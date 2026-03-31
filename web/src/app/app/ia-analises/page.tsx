import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";

// ── Tipos ─────────────────────────────────────────────────────────
type LessonRow = {
  id: string;
  title: string;
  summary: string | null;
  description: string | null;
  category: string | null;
  regime: string | null;
  total_trades: number | null;
  win_rate_pct: number | null;
  avg_confidence: number | null;
  total_pnl: number | null;
  generated_by: string | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
};

// ── Helpers visuais ───────────────────────────────────────────────
function categoryConfig(cat: string | null) {
  const configs: Record<string, { label: string; cls: string }> = {
    "high consistency":  { label: "Alta consistência", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" },
    "warning":          { label: "Atenção",           cls: "border-red-500/30 bg-red-500/10 text-red-400" },
    "general":          { label: "Geral",             cls: "border-slate-700 bg-slate-800 text-slate-400" },
    "entry_timing":     { label: "Timing de entrada", cls: "border-sky-500/30 bg-sky-500/10 text-sky-400" },
    "risk_management":  { label: "Gestão de risco",   cls: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
    "regime_mismatch":  { label: "Regime incorreto",  cls: "border-violet-500/30 bg-violet-500/10 text-violet-400" },
    "overconfidence":   { label: "Excesso de conf.",  cls: "border-orange-500/30 bg-orange-500/10 text-orange-400" },
    "neutral":          { label: "Neutro",            cls: "border-slate-700 bg-slate-800 text-slate-400" },
  };
  const key = (cat ?? "general").toLowerCase();
  return configs[key] ?? { label: cat ?? "Geral", cls: "border-slate-700 bg-slate-800 text-slate-400" };
}

function regimeLabel(regime: string | null) {
  const map: Record<string, string> = {
    "tendencia": "Tendência",
    "lateral":   "Lateral",
    "volatil":   "Volátil",
    "mixed":     "Misto",
  };
  return map[regime ?? ""] ?? regime ?? "—";
}

function formatPct(v: number | null) {
  if (v == null) return "—";
  return `${v.toFixed(1)}%`;
}

function formatPnl(v: number | null) {
  if (v == null) return "—";
  return `${v > 0 ? "+" : ""}R$ ${v.toFixed(2)}`;
}

function dateFmt(dt: string | null) {
  if (!dt) return "—";
  return new Date(dt).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
}

function WinRateBar({ value }: { value: number | null }) {
  if (value == null) return null;
  const color = value >= 60 ? "bg-emerald-500" : value >= 45 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="mt-2 flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="text-xs font-medium tabular-nums" style={{ minWidth: "3rem", textAlign: "right" }}>
        {formatPct(value)}
      </span>
    </div>
  );
}

function LessonCard({ lesson }: { lesson: LessonRow }) {
  const cat = categoryConfig(lesson.category);
  const content = lesson.summary || lesson.description || "Sem resumo.";
  const pnlColor = (lesson.total_pnl ?? 0) > 0 ? "text-emerald-400" : (lesson.total_pnl ?? 0) < 0 ? "text-red-400" : "text-slate-400";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-3 hover:border-slate-700 transition-colors">
      {/* Cabeçalho */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${cat.cls}`}>
            {cat.label}
          </span>
          {lesson.regime && (
            <span className="rounded-full border border-sky-500/20 bg-sky-500/10 px-2.5 py-0.5 text-[11px] font-medium text-sky-400">
              {regimeLabel(lesson.regime)}
            </span>
          )}
          {lesson.generated_by === "brain_auto" && (
            <span className="rounded-full border border-violet-500/20 bg-violet-500/10 px-2.5 py-0.5 text-[11px] font-medium text-violet-400">
              Auto
            </span>
          )}
        </div>
        <span className="text-xs text-slate-600">{dateFmt(lesson.created_at)}</span>
      </div>

      {/* Título */}
      <h3 className="font-semibold text-slate-200 leading-snug">{lesson.title}</h3>

      {/* Resumo */}
      <p className="text-sm text-slate-400 leading-relaxed">{content}</p>

      {/* Métricas */}
      <div className="border-t border-slate-800/60 pt-3 grid grid-cols-3 gap-3">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-0.5">Trades</p>
          <p className="text-sm font-medium text-slate-300">{lesson.total_trades ?? "—"}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-0.5">PnL</p>
          <p className={`text-sm font-medium tabular-nums ${pnlColor}`}>{formatPnl(lesson.total_pnl)}</p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-0.5">Conf. média</p>
          <p className="text-sm font-medium text-slate-300">{formatPct(lesson.avg_confidence != null ? lesson.avg_confidence * 100 : null)}</p>
        </div>
      </div>

      {/* Win rate bar */}
      {lesson.win_rate_pct != null && (
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-1">Win rate do período</p>
          <WinRateBar value={lesson.win_rate_pct} />
        </div>
      )}

      {/* Período */}
      {lesson.period_start && lesson.period_end && (
        <p className="text-[11px] text-slate-600">
          Período: {dateFmt(lesson.period_start)} → {dateFmt(lesson.period_end)}
        </p>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────
export default async function IAAnalisesPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="IA Análises" />;
  }

  // Busca lições do usuário — usa profile_id (coluna gravada pelo brain)
  const { data: lessons } = await supabase
    .from("lessons_learned")
    .select(
      "id, title, summary, description, category, regime, " +
      "total_trades, win_rate_pct, avg_confidence, total_pnl, " +
      "generated_by, period_start, period_end, created_at"
    )
    .eq("profile_id", user.id)
    .order("created_at", { ascending: false })
    .limit(50);

  const rows: LessonRow[] = (lessons as unknown as LessonRow[] | null) ?? [];

  // Estatísticas rápidas
  const totalLessons = rows.length;
  const autoGenerated = rows.filter((l) => l.generated_by === "brain_auto").length;
  const avgWinRate = rows.filter((l) => l.win_rate_pct != null).length > 0
    ? rows.reduce((acc, l) => acc + (l.win_rate_pct ?? 0), 0) / rows.filter((l) => l.win_rate_pct != null).length
    : null;
  const positiveCount = rows.filter((l) => (l.total_pnl ?? 0) > 0).length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-xl font-bold text-slate-100">IA Análises</h1>
        <p className="mt-1 text-sm text-slate-500">
          Lições geradas automaticamente pelo motor após cada bloco de operações analisadas.
        </p>
      </div>

      {/* Stats rápidas */}
      {totalLessons > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Total de lições", value: totalLessons.toString(), accent: "slate" },
            { label: "Geradas pelo motor", value: autoGenerated.toString(), accent: "violet" },
            { label: "Win rate médio", value: avgWinRate != null ? `${avgWinRate.toFixed(1)}%` : "—",
              accent: avgWinRate == null ? "slate" : avgWinRate >= 60 ? "emerald" : avgWinRate >= 45 ? "amber" : "red" },
            { label: "Períodos com lucro", value: positiveCount.toString(), accent: positiveCount > 0 ? "emerald" : "slate" },
          ].map((s) => (
            <div key={s.label} className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
              <p className="text-xs text-slate-500 mb-1">{s.label}</p>
              <p className={`text-2xl font-bold ${
                s.accent === "emerald" ? "text-emerald-400"
                : s.accent === "red" ? "text-red-400"
                : s.accent === "amber" ? "text-amber-400"
                : s.accent === "violet" ? "text-violet-400"
                : "text-slate-200"
              }`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Lista de lições */}
      {rows.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/50 py-20 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-800 text-slate-600">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-7 w-7">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
            </svg>
          </div>
          <p className="text-sm text-slate-500">Nenhuma lição gerada ainda</p>
          <p className="mt-1 text-xs text-slate-600 max-w-xs">
            O motor gera lições automaticamente após cada 50 operações analisadas. Continue operando para acumular dados.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {rows.map((lesson) => (
            <LessonCard key={lesson.id} lesson={lesson} />
          ))}
        </div>
      )}
    </div>
  );
}
