import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import { TerminalFeed } from "@/components/app/terminal-feed";
import { DashboardRefresher } from "@/components/app/dashboard-refresher";
import { PremiumMetricCard } from "@/components/app/premium-metric-card";
import { DashboardQuickActions } from "@/components/app/dashboard-quick-actions";
import { signVisualStoragePaths } from "@/lib/mt5/visual-shadow";
import RobotProductDashboardLanes from "@/components/app/robot-product-dashboard-lanes";

// ── Tooltip Helper ───────────────────────────────────────────
function InfoTooltip({ text }: { text: string }) {
  return (
    <div className="group relative inline-block ml-1 cursor-help">
      <span className="inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-slate-600 text-[9px] text-slate-500 group-hover:border-sky-500 group-hover:text-sky-400">?</span>
      <div className="absolute bottom-full left-1/2 mb-2 w-48 -translate-x-1/2 scale-0 rounded-lg bg-slate-800 p-2 text-[10px] leading-tight text-slate-200 shadow-xl transition-all group-hover:scale-100 z-50">
        {text}
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-800" />
      </div>
    </div>
  );
}

// ── Cards de métrica ─────────────────────────────────────────
// MetricCard is replaced by PremiumMetricCard

// Helper de formatação de moeda seguro (evita erro de hidratação #418)
function formatCurrency(val: number) {
  return "R$ " + val.toFixed(2).replace(".", ",").replace(/\B(?=(\d{3})+(?!\d))/g, ".");
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

type DecisionOutcomeStatus = "pending" | "executing" | "win" | "loss" | "neutral" | "breakeven" | null;

type TradeOutcomeResult = "win" | "loss" | "breakeven" | null;

type ExecutedTradeRow = {
  id: string;
  status: string;
  opened_at: string | null;
  closed_at: string | null;
  trade_outcomes: Array<{ result: TradeOutcomeResult; pnl_money: number | null }>;
};

type TradeDecisionRow = {
  id: string;
  symbol: string;
  timeframe: string;
  side: string;
  mode: string;
  created_at: string;
  outcome_status?: DecisionOutcomeStatus;
  outcome_profit?: number | null;
  closed_at?: string | null;
  executed_trades: ExecutedTradeRow[];
};

type LearningStatRow = {
  outcome_status: DecisionOutcomeStatus;
};

type RecentOutcomeRow = {
  side: string;
  outcome_status: DecisionOutcomeStatus;
  executed_trades?: Array<{
    trade_outcomes?: Array<{ result?: TradeOutcomeResult }>;
  }>;
};

type LatestVisualRow = {
  cycle_id: string;
  chart_image_storage_path: string | null;
  visual_shadow_status: string;
  visual_alignment: string;
  visual_conflict_reason: string | null;
  visual_context: {
    summary?: string;
  } | null;
  created_at: string;
};

// ── Página ────────────────────────────────────────────────────
export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  const access = user ? await getSubscriptionAccess(supabase, user.id) : null;

  // Última decisão do motor
  const { data: lastDecisionArr } = user
    ? await supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, confidence, risk_pct, mode, rationale, created_at")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(1)
    : { data: null };
  const lastDecision = lastDecisionArr?.[0] ?? null;

  // Estado real do motor: última vez que enviou heartbeat (last_seen_at)
  const { data: profile } = user
    ? await supabase
        .from("user_profiles")
        .select("id")
        .eq("auth_user_id", user.id)
        .limit(1)
        .maybeSingle()
    : { data: null };
  const profileId = profile?.id ?? "";

  const { data: robotInstance } = user && profileId
    ? await supabase
        .from("robot_instances")
        .select("id, name, status, last_seen_at, allowed_modes, real_trading_enabled, current_balance, initial_balance")
        .eq("profile_id", profileId)
        .eq("status", "active")
        .order("last_seen_at", { ascending: false, nullsFirst: false })
        .limit(1)
        .maybeSingle()
    : { data: null };

  const { data: robotInstanceWithBalance } = user && profileId
    ? await supabase
        .from("robot_instances")
        .select("initial_balance, current_balance")
        .eq("profile_id", profileId)
        .gt("current_balance", 0)
        .order("last_seen_at", { ascending: false, nullsFirst: false })
        .limit(1)
        .maybeSingle()
    : { data: null };

  const hasLiveBalance = (robotInstance?.initial_balance ?? 0) > 0 || (robotInstance?.current_balance ?? 0) > 0;
  const balanceSource = hasLiveBalance ? robotInstance : (robotInstanceWithBalance ?? robotInstance);

  // Calcular minutosDesde o último heartbeat
  const nowMs = new Date().getTime();
  const motorOnline = (() => {
    if (!robotInstance?.last_seen_at) return false;
    const diffMs = nowMs - new Date(robotInstance.last_seen_at).getTime();
    return diffMs < 5 * 60 * 1000; // ativo se heartbeat < 5 min
  })();
  const motorLastSeenLabel = (() => {
    if (!robotInstance?.last_seen_at) return null;
    const diffMin = Math.floor((nowMs - new Date(robotInstance.last_seen_at).getTime()) / 60000);
    if (diffMin < 1) return "agora";
    if (diffMin < 60) return `há ${diffMin} min`;
    const h = Math.floor(diffMin / 60);
    return `há ${h}h`;
  })();

  const { data: latestVisualRaw } = user && robotInstance?.id
    ? await supabase
        .from("trade_visual_contexts")
        .select("cycle_id, chart_image_storage_path, visual_shadow_status, visual_alignment, visual_conflict_reason, visual_context, created_at")
        .eq("robot_instance_id", robotInstance.id)
        .order("created_at", { ascending: false })
        .limit(1)
        .maybeSingle()
    : { data: null };

  const latestVisualUrlMap = latestVisualRaw
    ? await signVisualStoragePaths([latestVisualRaw.chart_image_storage_path])
    : {};

  const latestVisual = latestVisualRaw
    ? {
        ...(latestVisualRaw as LatestVisualRow),
        chart_image_url: latestVisualRaw.chart_image_storage_path
          ? latestVisualUrlMap[latestVisualRaw.chart_image_storage_path] ?? null
          : null,
      }
    : null;

  // Custo de IA acumulado hoje
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const { data: aiLogs } = user
    ? await supabase
        .from("ai_usage_logs")
        .select("estimated_cost")
        .eq("user_id", user.id)
        .gte("created_at", todayStart.toISOString())
    : { data: null };
  const todayAiCost = (aiLogs ?? []).reduce(
    (sum: number, r: { estimated_cost?: number | null }) => sum + (r.estimated_cost ?? 0),
    0
  );

  // ── Ciclo de Aprendizado: Taxa de acerto global (Real + Virtual) ──
  const { data: learningStats } = user
    ? await supabase
        .from("trade_decisions")
        .select("outcome_status")
        .eq("user_id", user.id)
        .neq("side", "hold")
        .neq("outcome_status", "pending")
        .order("created_at", { ascending: false })
        .limit(100)
    : { data: null };

  const iaAccuracy = (() => {
    const rows = (learningStats ?? []) as LearningStatRow[];
    if (rows.length < 5) return null;
    const wins = rows.filter(r => r.outcome_status === "win").length;
    return Math.round((wins / rows.length) * 100);
  })();

  // Consistência: % de decisões BUY/SELL que resultaram em WIN nos últimos 20 trades
  const { data: recentOutcomes } = user
    ? await supabase
        .from("trade_decisions")
        .select("side, outcome_status, executed_trades(trade_outcomes(result))")
        .eq("user_id", user.id)
        .neq("side", "hold")
        .order("created_at", { ascending: false })
        .limit(20)
    : { data: null };

  const consistencyScore = (() => {
    const rows = (recentOutcomes ?? []) as RecentOutcomeRow[];
    const withResult = rows.filter(r => r.outcome_status !== "pending" || r.executed_trades?.[0]?.trade_outcomes?.[0]?.result);
    if (withResult.length < 5) return null;
    const wins = withResult.filter(r => 
      r.outcome_status === "win" || 
      r.executed_trades?.[0]?.trade_outcomes?.[0]?.result === "win"
    ).length;
    return Math.round((wins / withResult.length) * 100);
  })();

  // Regime de mercado atual (da última decisão)
  const regimeFromRationale = (() => {
    if (!lastDecision?.rationale) return null;
    const m = lastDecision.rationale.match(/^\[(TENDENCIA|LATERAL|VOLATIL)\]/i);
    return m ? m[1].toLowerCase() : null;
  })();

  // Comparativo demo vs real (últimas 50 decisões executadas com resultado)
  const { data: modeComparison } = user
    ? await supabase
        .from("trade_decisions")
        .select("mode, side, executed_trades(trade_outcomes(result))")
        .eq("user_id", user.id)
        .neq("side", "hold")
        .order("created_at", { ascending: false })
        .limit(50)
    : { data: null };

  const modeStats = (() => {
    const rows = (modeComparison ?? []) as Array<{
      mode: string;
      executed_trades?: Array<{ trade_outcomes?: Array<{ result?: string }> }>;
    }>;
    const compute = (mode: string) => {
      const filtered = rows.filter(r => r.mode === mode && r.executed_trades?.[0]?.trade_outcomes?.[0]?.result);
      const wins = filtered.filter(r => r.executed_trades?.[0]?.trade_outcomes?.[0]?.result === "win");
      return { total: filtered.length, wins: wins.length };
    };
    return { demo: compute("demo"), real: compute("real") };
  })();
  const showComparativo = modeStats.demo.total >= 3 || modeStats.real.total >= 3;

  // ── KPIs de hoje ─────────────────────────────────────────────
  const { data: todayDecRaw } = user
    ? await supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, mode, created_at, outcome_status, outcome_profit, executed_trades(id, status, opened_at, closed_at, trade_outcomes(result, pnl_money))")
        .eq("user_id", user.id)
        .gte("created_at", todayStart.toISOString())
        .order("created_at", { ascending: false })
    : { data: null };

  const todayDec = (todayDecRaw as TradeDecisionRow[] | null) ?? [];
  
  // Mudar contagem para usar a nova estrutura simplificada de Auditoria
  const todayExecuted = todayDec.filter(d => 
    d.executed_trades?.length > 0 || 
    d.outcome_status === "executing" || 
    d.outcome_status === "win" || 
    d.outcome_status === "loss"
  );
  
  const todayTotalTrades = todayExecuted.length;
  const todayOpenTrades  = todayDec.filter(d => d.outcome_status === "executing").length;
  
  // PnL: Prioriza outcome_profit (novo) e cai para trade_outcomes (antigo)
  const todayPnl = todayDec.reduce((sum, d) => {
    const realProfit = d.outcome_profit ?? 0;
    const oldProfit = d.executed_trades?.[0]?.trade_outcomes?.[0]?.pnl_money ?? 0;
    return sum + (realProfit !== 0 ? realProfit : oldProfit);
  }, 0);

  // Lucro total (Vitalício)
  const totalProfit = (balanceSource?.current_balance ?? 0) - (balanceSource?.initial_balance ?? 0);

  // Win rate global para o card principal (prioriza Ciclo de Aprendizado)
  const winRateCalc = iaAccuracy ?? consistencyScore;

  // Últimas 5 operações fechadas para a tabela do dashboard
  const { data: recentClosedRaw } = user
    ? await supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, mode, created_at, outcome_status, outcome_profit, executed_trades(id, status, opened_at, closed_at, trade_outcomes(result, pnl_money))")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(30)
    : { data: null };

  const recentClosed = ((recentClosedRaw as TradeDecisionRow[] | null) ?? [])
    .map((d) => {
      const et = d.executed_trades?.[0];
      const outcomeStatus = d.outcome_status;
      const outcomeResult: TradeOutcomeResult =
        outcomeStatus === "neutral"
          ? "breakeven"
          : outcomeStatus === "win" || outcomeStatus === "loss" || outcomeStatus === "breakeven"
          ? outcomeStatus
          : null;

      const out = et?.trade_outcomes?.[0] ?? (outcomeResult
        ? {
            result: outcomeResult,
            pnl_money: d.outcome_profit ?? null,
          }
        : null);

      const hasClosedTrade = et?.status === "closed" || outcomeResult !== null;
      const tradeId = et?.id ?? d.id;
      const closedAt = et?.closed_at ?? d.closed_at ?? null;

      return { d, tradeId, out, closedAt, hasClosedTrade };
    })
    .filter((item) => item.hasClosedTrade)
    .slice(0, 5);

  const activeMode = ((robotInstance?.allowed_modes ?? []).includes("real") && robotInstance?.real_trading_enabled)
    ? "real"
    : (lastDecision?.mode ?? "inactive");

  const metrics = {
    totalTrades: todayTotalTrades,
    winRate: winRateCalc,
    pnl: todayPnl,
    openTrades: todayOpenTrades,
    robotMode: motorOnline
      ? (activeMode as "observer" | "demo" | "real" | "inactive")
      : "inactive",
  };

  const firstName = user?.user_metadata?.full_name?.split(" ")[0] ?? "Trader";

  // ── Terminal Feed: busca server-side para passar como initialLogs ──
  const { data: terminalLogsRaw } = user
    ? await supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, confidence, risk_pct, mode, rationale, created_at")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(25)
    : { data: null };

  // Ordenados do mais antigo ao mais novo (do topo para baixo no terminal)
  const terminalLogs = ((terminalLogsRaw ?? []) as Array<{
    id: string; symbol: string; timeframe: string; side: string;
    confidence: number; risk_pct: number; mode: string; rationale: string; created_at: string;
  }>).reverse();

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Cabeçalho */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
            Olá, {firstName} 👋
          </h1>
          <p className="text-sm font-medium text-slate-500 mt-1 uppercase tracking-widest">
            Monitoramento Premium Vuno
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
           <DashboardQuickActions />
           <RobotStatusBadge mode={metrics.robotMode} />
        </div>
      </div>

      {!motorOnline && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">
          Motor desconectado. Inicie o agent-local da instância e valide a bridge no MT5 para ativar.
          <a href="/app/instalacao" className="ml-2 font-semibold text-sky-300 hover:underline">Abrir instalação</a>
        </div>
      )}

      {/* Barra de estado do sistema (quando online) */}
      {motorOnline && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex items-center gap-3 glass-card border-emerald-500/20 bg-emerald-500/5 px-4 py-3 rounded-xl glow-emerald">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-emerald-300">Motor operacional</p>
              <p className="text-xs font-bold text-slate-300">{robotInstance?.name ?? "Instância Ativa"} · {motorLastSeenLabel}</p>
            </div>
          </div>
          {regimeFromRationale && (
            <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${
              regimeFromRationale === "tendencia" ? "border-violet-500/20 bg-violet-500/5" :
              regimeFromRationale === "volatil"   ? "border-orange-500/20 bg-orange-500/5" :
                                                    "border-slate-600/30 bg-slate-800/30"
            }`}>
              <span className={`text-lg shrink-0 ${
                regimeFromRationale === "tendencia" ? "text-violet-400" :
                regimeFromRationale === "volatil"   ? "text-orange-400" : "text-slate-400"
              }`}>
                {regimeFromRationale === "tendencia" ? "↗" : regimeFromRationale === "volatil" ? "⚡" : "↔"}
              </span>
              <div>
                <p className={`text-xs font-semibold capitalize ${
                  regimeFromRationale === "tendencia" ? "text-violet-300" :
                  regimeFromRationale === "volatil"   ? "text-orange-300" : "text-slate-300"
                }`}>
                  Mercado: {regimeFromRationale}
                </p>
                <p className="text-[10px] text-slate-500">Último sinal analisado</p>
              </div>
            </div>
          )}
          {consistencyScore !== null && (
            <div className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${
              consistencyScore >= 60 ? "border-emerald-500/20 bg-emerald-500/5" :
              consistencyScore >= 45 ? "border-amber-500/20 bg-amber-500/5" :
                                       "border-red-500/20 bg-red-500/5"
            }`}>
              <span className={`text-2xl font-bold shrink-0 ${
                consistencyScore >= 60 ? "text-emerald-400" :
                consistencyScore >= 45 ? "text-amber-400" : "text-red-400"
              }`}>{consistencyScore}%</span>
              <div>
                <div className="flex items-center gap-1">
                   <p className="text-xs font-semibold text-slate-300">Consistência</p>
                   <InfoTooltip text="Frequência de acerto nos últimos 20 sinais. Indica a saúde da IA no curto prazo." />
                </div>
                <p className="text-[10px] text-slate-500">Últimos 20 trades ativos</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Métricas de Conta (Vitalício) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 mb-6">
        <PremiumMetricCard
          label="Banca Inicial"
          value={
            balanceSource?.initial_balance != null
              ? formatCurrency(balanceSource.initial_balance)
              : "R$ 0,00"
          }
          subtitle="Capital de referência"
          accent="slate"
        />
        <PremiumMetricCard
          label="Banca Atual"
          value={
            balanceSource?.current_balance != null
              ? formatCurrency(balanceSource.current_balance)
              : "R$ 0,00"
          }
          subtitle="Saldo em tempo real"
          accent="sky"
        />
        <PremiumMetricCard
          label="Lucro Total"
          value={
            totalProfit === 0
              ? "R$ 0,00"
              : totalProfit > 0
              ? `+${formatCurrency(totalProfit)}`
              : `-${formatCurrency(Math.abs(totalProfit))}`
          }
          subtitle="Acumulado Vitalício"
          accent={totalProfit > 0 ? "emerald" : totalProfit < 0 ? "rose" : "slate"}
        />
      </div>

      {/* Métricas de Performance (Hoje) */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <PremiumMetricCard
          label="Hoje"
          value={todayTotalTrades.toString()}
          subtitle="Operações"
          accent="slate"
        />
        <PremiumMetricCard
          label="Acerto IA"
          value={winRateCalc !== null ? `${winRateCalc}%` : "---"}
          subtitle={winRateCalc !== null ? "Meta: 68%" : "Em calibração"}
          accent={
            winRateCalc === null ? "slate"
            : winRateCalc >= 68 ? "emerald"
            : winRateCalc >= 50 ? "sky" : "rose"
          }
        />
        <PremiumMetricCard
          label="Resultado HOJE"
          value={
            todayPnl === 0
              ? "R$ 0,00"
              : todayPnl > 0
              ? `+${formatCurrency(todayPnl)}`
              : `-${formatCurrency(Math.abs(todayPnl))}`
          }
          subtitle="Lucro/Prejuízo"
          accent={todayPnl > 0 ? "emerald" : todayPnl < 0 ? "rose" : "slate"}
        />
        <PremiumMetricCard
          label="Abertas"
          value={todayOpenTrades.toString()}
          subtitle="Monitoramento"
          accent={todayOpenTrades > 0 ? "sky" : "slate"}
        />
      </div>

      <DashboardRefresher />

      {/* Terminal do motor */}
      {motorOnline && user?.id && (
        <TerminalFeed userId={user.id} robotId={robotInstance?.id} initialLogs={terminalLogs} />
      )}

      {/* Painel Motor de Decisão */}
      <div className="glass-card overflow-hidden rounded-2xl relative">
        <div className="absolute top-0 right-0 p-4 opacity-5 bg-gradient-to-br from-sky-500 to-transparent w-full h-full pointer-events-none" />
        
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/5">
          <h2 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400">Última decisão do motor</h2>
          {todayAiCost > 0 && (
            <span className="text-[10px] font-bold text-sky-400 tracking-wider">
              INTELIGÊNCIA ATIVA: USD {todayAiCost.toFixed(4)}
            </span>
          )}
        </div>
        {lastDecision ? (
          <div className="px-6 py-6 flex flex-col gap-5 sm:flex-row sm:items-center sm:gap-10">
            {/* Score Visualizer */}
            <div className="flex flex-col items-center justify-center relative">
              <div className="h-16 w-16 rounded-full border-4 border-slate-800 flex items-center justify-center relative overflow-hidden">
                 <div className="absolute inset-0 bg-sky-500/10 animate-pulse" />
                 <span className="text-2xl font-black text-sky-400 relative z-10">
                   {lastDecision.confidence != null ? Math.round(lastDecision.confidence * 100) : "—"}
                 </span>
              </div>
              <p className="text-[9px] font-black text-slate-500 mt-2 uppercase tracking-widest">COGNITION</p>
            </div>

            <div className="flex-1 space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-lg font-black text-white">{lastDecision.symbol}</span>
                <span className={`rounded-md px-2 py-1 text-[10px] font-black tracking-widest uppercase ${
                  lastDecision.side === "buy" ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 glow-emerald"
                  : lastDecision.side === "sell" ? "bg-rose-500/20 text-rose-300 border border-rose-500/30 glow-rose"
                  : "bg-slate-700 text-slate-300"
                }`}>{lastDecision.side}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-400 border border-slate-700">{lastDecision.timeframe}</span>
                <span className={`rounded-full border px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                  lastDecision.mode === "real" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : lastDecision.mode === "demo" ? "border-sky-500/30 bg-sky-500/10 text-sky-300 shadow-[0_0_10px_rgba(14,165,233,0.1)]"
                  : "border-slate-600 bg-slate-700 text-slate-400"
                }`}>{lastDecision.mode}</span>
              </div>
              
              <div className="p-3 rounded-lg bg-black/40 border border-white/5">
                <p className="text-xs text-slate-300 leading-relaxed italic">
                  {lastDecision.rationale ? lastDecision.rationale : "Sem justificativa técnica disponível."}
                </p>
              </div>
              
              <p className="text-[10px] font-medium text-slate-500 flex items-center gap-2">
                <span className="h-1 w-1 rounded-full bg-slate-600" />
                {new Date(lastDecision.created_at).toLocaleString("pt-BR", {
                  day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
                })}
                <Link href="/app/auditoria" className="ml-2 text-sky-400 font-bold hover:text-sky-300 transition-colors uppercase tracking-widest text-[9px]">Ver Auditoria completa →</Link>
              </p>
            </div>
          </div>
        ) : (
          <EmptyState message="Fila de decisão vazia. Aguardando sinal do motor Vuno." />
        )}
      </div>

      {/* Seção de operações recentes */}
      <div className="rounded-xl bg-slate-900 border border-slate-800">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-200">
            Operações recentes
          </h2>
          <Link
            href="/app/operacoes"
            className="text-xs text-sky-500 hover:text-sky-400 hover:underline"
          >
            Ver todas →
          </Link>
        </div>
        {recentClosed.length === 0 ? (
          <EmptyState message="Ainda não recebemos operações fechadas. Finalize a conexão em Instalação para começar." />
        ) : (
          <div className="divide-y divide-slate-800">
            {recentClosed.map((item) => {
              const d = item.d;
              const out = item.out;
              const isWin = out?.result === "win";
              const isLoss = out?.result === "loss";
              return (
                <Link
                  key={item.tradeId}
                  href={`/app/operacoes/${item.tradeId}`}
                  className="flex items-center justify-between px-5 py-3 hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold shrink-0 ${
                      isWin ? "bg-emerald-500/20 text-emerald-400" :
                      isLoss ? "bg-red-500/20 text-red-400" : "bg-slate-700 text-slate-400"
                    }`}>
                      {isWin ? "W" : isLoss ? "L" : "—"}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-slate-200">
                        {d.symbol}
                        <span className="ml-1.5 text-xs font-normal text-slate-500">{d.timeframe}</span>
                      </p>
                      <p className="text-[10px] text-slate-600">
                        {d.side?.toUpperCase()} · {d.mode}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {out?.pnl_money != null && (
                      <p className={`text-sm font-semibold tabular-nums ${
                        out.pnl_money > 0 ? "text-emerald-400" :
                        out.pnl_money < 0 ? "text-red-400" : "text-slate-400"
                      }`}>
                        {out.pnl_money > 0 ? "+" : ""}{formatCurrency(out.pnl_money)}
                      </p>
                    )}
                    <p className="text-[10px] text-slate-600">
                      {item.closedAt ? new Date(item.closedAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "—"}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {/* Comparativo Demo vs Real */}
      {showComparativo && (
        <div className="rounded-xl bg-slate-900 border border-slate-800">
          <div className="px-5 py-4 border-b border-slate-800">
            <h2 className="text-sm font-semibold text-slate-200">Demo vs Real</h2>
            <p className="text-xs text-slate-500 mt-0.5">Consistência do motor em cada ambiente</p>
          </div>
          <div className="grid grid-cols-2 divide-x divide-slate-800 px-0">
            {(["demo", "real"] as const).map((mode) => {
              const s = modeStats[mode];
              const wr = s.total > 0 ? Math.round((s.wins / s.total) * 100) : null;
              return (
                <div key={mode} className="px-5 py-4">
                  <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${
                    mode === "demo" ? "text-sky-400" : "text-emerald-400"
                  }`}>{mode}</p>
                  {s.total === 0 ? (
                    <p className="text-xs text-slate-600">Sem dados ainda</p>
                  ) : (
                    <>
                      <p className={`text-2xl font-bold ${
                        wr === null ? "text-slate-400" :
                        wr >= 60 ? "text-emerald-400" :
                        wr >= 45 ? "text-amber-400" : "text-red-400"
                      }`}>{wr !== null ? `${wr}%` : "—"}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">{s.wins}/{s.total} acertos</p>
                      {wr !== null && (
                        <div className="mt-2 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${
                            wr >= 60 ? "bg-emerald-500" : wr >= 45 ? "bg-amber-500" : "bg-red-500"
                          }`} style={{ width: `${wr}%` }} />
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
          {modeStats.demo.total >= 5 && modeStats.real.total >= 5 && (() => {
            const demoWr = Math.round((modeStats.demo.wins / modeStats.demo.total) * 100);
            const realWr = Math.round((modeStats.real.wins / modeStats.real.total) * 100);
            const diff = Math.abs(demoWr - realWr);
            return (
              <div className="border-t border-slate-800 px-5 py-3">
                <p className="text-xs text-slate-500">
                  {diff <= 10
                    ? `✅ Diferença de ${diff}% entre demo e real — dentro do esperado.`
                    : `⚠️ Diferença de ${diff}% entre demo e real — revise parâmetros antes de operar no real.`
                  }
                </p>
              </div>
            );
          })()}
        </div>
      )}

      {/* Seção de status do sistema */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Motor do robo */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-slate-400">Motor de decisão</p>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
              motorOnline
                ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-300"
                : "bg-slate-700 text-slate-500"
            }`}>
              {motorOnline ? "Online" : "Off"}
            </span>
          </div>
          <p className="text-xs leading-relaxed">
            {motorOnline ? (
              <span className="text-slate-300">
                Motor ativo · {robotInstance?.name ?? "instância"}
              </span>
            ) : (
              <span className="text-slate-600">
                Motor desconectado. Conecte a instância pelo fluxo bridge para ativar.
                {" "}<a href="/app/instalacao" className="text-sky-500 hover:underline">Ver passo a passo</a>
              </span>
            )}
          </p>
        </div>

        {/* MT5 EA */}
        <div className="rounded-xl bg-slate-900 border border-slate-800 px-5 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-slate-400">MetaTrader</p>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
              motorOnline
                ? "border border-emerald-500/30 bg-emerald-500/20 text-emerald-300"
                : "bg-slate-700 text-slate-500"
            }`}>
              {motorOnline ? "Online" : "Off"}
            </span>
          </div>
          <p className="text-xs leading-relaxed">
            {motorOnline ? (
              <span className="text-slate-300">EA conectado e enviando sinais.</span>
            ) : (
              <span className="text-slate-600">
                O MT5 ainda não enviou dados. Verifique EA no gráfico e AutoTrading ligado.
              </span>
            )}
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
                Gerencie pacote, bridge e validação operacional em{" "}
                <a href="/app/instalacao" className="text-sky-500 hover:underline">
                  Instalação
                </a>.
              </>
            ) : (
              <>
                Ative um plano para liberar Operações, Auditoria e Estudos em{" "}
                <a href="/app/assinatura" className="text-sky-500 hover:underline">
                  Assinatura
                </a>.
              </>
            )}
          </p>
        </div>
      </div>

      <RobotProductDashboardLanes
        hasActivePlan={access?.hasActivePlan ?? false}
        features={access?.features ?? {}}
        motorOnline={motorOnline}
        instanceName={robotInstance?.name ?? null}
        latestVisual={latestVisual}
      />
    </div>
  );
}
