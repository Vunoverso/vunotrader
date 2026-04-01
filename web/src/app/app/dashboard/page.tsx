import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import { TerminalFeed } from "@/components/app/terminal-feed";

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
  const { data: robotInstance } = user
    ? await supabase
        .from("robot_instances")
        .select("id, name, status, last_seen_at, allowed_modes, real_trading_enabled")
        .eq("profile_id",
            (await supabase.from("user_profiles").select("id").eq("auth_user_id", user.id).limit(1).single())
              .data?.id ?? ""
        )
        .eq("status", "active")
        .order("last_seen_at", { ascending: false, nullsFirst: false })
        .limit(1)
        .maybeSingle()
    : { data: null };

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

  // Consistência: % de decisões BUY/SELL que resultaram em WIN nos últimos 20 trades
  const { data: recentOutcomes } = user
    ? await supabase
        .from("trade_decisions")
        .select("side, executed_trades(trade_outcomes(result))")
        .eq("user_id", user.id)
        .neq("side", "hold")
        .order("created_at", { ascending: false })
        .limit(20)
    : { data: null };
  const consistencyScore = (() => {
    const rows = (recentOutcomes ?? []) as Array<{
      side: string;
      executed_trades?: Array<{ trade_outcomes?: Array<{ result?: string }> }>;
    }>;
    const withResult = rows.filter(r => r.executed_trades?.[0]?.trade_outcomes?.[0]?.result);
    if (withResult.length < 5) return null;
    const wins = withResult.filter(r => r.executed_trades?.[0]?.trade_outcomes?.[0]?.result === "win");
    return Math.round((wins.length / withResult.length) * 100);
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
  type TradeDecRow = {
    id: string; symbol: string; timeframe: string; side: string; mode: string; created_at: string;
    executed_trades: Array<{
      id: string; status: string; opened_at: string | null; closed_at: string | null;
      trade_outcomes: Array<{ result: string | null; pnl_money: number | null }>;
    }>;
  };

  const { data: todayDecRaw } = user
    ? await supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, mode, created_at, executed_trades(id, status, opened_at, closed_at, trade_outcomes(result, pnl_money))")
        .eq("user_id", user.id)
        .gte("created_at", todayStart.toISOString())
        .order("created_at", { ascending: false })
    : { data: null };

  const todayDec = (todayDecRaw as unknown as TradeDecRow[] | null) ?? [];
  const todayWithExec = todayDec.filter(d => (d.executed_trades ?? []).length > 0);
  const todayTotalTrades = todayWithExec.length;
  const todayOpenTrades  = todayWithExec.filter(d => d.executed_trades[0]?.status === "open").length;
  const todayPnl = todayWithExec.reduce(
    (sum, d) => sum + (d.executed_trades[0]?.trade_outcomes[0]?.pnl_money ?? 0), 0
  );

  // Win rate dos últimos 20 trades (reutiliza recentOutcomes)
  const roRows = (recentOutcomes as unknown as Array<{
    side: string;
    executed_trades?: Array<{ trade_outcomes?: Array<{ result?: string }> }>;
  }> | null) ?? [];
  const roWithResult = roRows.filter(r => r.executed_trades?.[0]?.trade_outcomes?.[0]?.result);
  const winRateCalc = roWithResult.length >= 5
    ? Math.round(
        (roWithResult.filter(r => r.executed_trades?.[0]?.trade_outcomes?.[0]?.result === "win").length
          / roWithResult.length) * 100
      )
    : null;

  // Últimas 5 operações fechadas para a tabela do dashboard
  const { data: recentClosedRaw } = user
    ? await supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, mode, created_at, executed_trades(id, status, opened_at, closed_at, trade_outcomes(result, pnl_money))")
        .eq("user_id", user.id)
        .order("created_at", { ascending: false })
        .limit(30)
    : { data: null };

  const recentClosed = ((recentClosedRaw as unknown as TradeDecRow[] | null) ?? [])
    .filter(d => (d.executed_trades ?? []).length > 0 && d.executed_trades[0]?.status === "closed")
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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">
            Olá, {firstName} 👋
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Painel de controle operacional
          </p>
        </div>
        <RobotStatusBadge mode={metrics.robotMode} />
      </div>

      {!motorOnline && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">
          Motor desconectado. Inicie o brain Python e configure o EA para ativar.
          <a href="/app/instalacao" className="ml-2 font-semibold text-sky-300 hover:underline">Abrir instalação</a>
        </div>
      )}

      {/* Barra de estado do sistema (quando online) */}
      {motorOnline && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
            <div>
              <p className="text-xs font-semibold text-emerald-300">Motor ativo</p>
              <p className="text-[10px] text-slate-500">{robotInstance?.name ?? "Instância"} · {motorLastSeenLabel}</p>
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
                <p className="text-xs font-semibold text-slate-300">Consistência</p>
                <p className="text-[10px] text-slate-500">Últimos 20 trades ativos</p>
              </div>
            </div>
          )}
        </div>
      )}

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

      {/* Terminal Hacker de Pensamentos do Motor */}
      {motorOnline && user?.id && (
        <TerminalFeed userId={user.id} robotId={robotInstance?.id} initialLogs={terminalLogs} />
      )}

      {/* Painel Motor de Decisão */}
      <div className="rounded-xl bg-slate-900 border border-slate-800">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-200">Última decisão do motor</h2>
          {todayAiCost > 0 && (
            <span className="text-xs text-slate-500">
              Custo IA hoje:{" "}
              <span className="font-semibold text-slate-300">
                USD {todayAiCost.toFixed(4)}
              </span>
            </span>
          )}
        </div>
        {lastDecision ? (
          <div className="px-5 py-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-6">
            {/* Score */}
            <div className="flex flex-col items-center justify-center min-w-[72px]">
              <p className="text-3xl font-bold text-sky-400">
                {lastDecision.confidence != null
                  ? Math.round(lastDecision.confidence * 100)
                  : "—"}
              </p>
              <p className="text-[10px] text-slate-500 mt-0.5">score</p>
            </div>
            <div className="flex-1 space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold text-slate-100">{lastDecision.symbol}</span>
                <span className={`rounded px-2 py-0.5 text-[10px] font-semibold ${
                  lastDecision.side === "buy" ? "bg-emerald-500/20 text-emerald-300"
                  : lastDecision.side === "sell" ? "bg-red-500/20 text-red-300"
                  : "bg-slate-700 text-slate-300"
                }`}>{lastDecision.side?.toUpperCase()}</span>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">{lastDecision.timeframe}</span>
                <span className={`rounded-full border px-2 py-0.5 text-[10px] ${
                  lastDecision.mode === "real" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : lastDecision.mode === "demo" ? "border-sky-500/30 bg-sky-500/10 text-sky-300"
                  : "border-slate-600 bg-slate-700 text-slate-400"
                }`}>{lastDecision.mode}</span>
                {lastDecision.risk_pct != null && (
                  <span className="text-[10px] text-slate-500">risco {lastDecision.risk_pct}%</span>
                )}
              </div>
              {lastDecision.rationale ? (
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-2">{lastDecision.rationale}</p>
              ) : (
                <p className="text-xs text-slate-600">Sem justificativa registrada.</p>
              )}
              <p className="text-[10px] text-slate-600">
                {new Date(lastDecision.created_at).toLocaleString("pt-BR", {
                  day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
                })}
                {" · "}
                <a href="/app/auditoria" className="text-sky-500 hover:underline">Ver trilha completa →</a>
              </p>
            </div>
          </div>
        ) : (
          <EmptyState message="Nenhuma decisão ainda. O motor gera um registro para cada sinal analisado — inclusive HOLDs." />
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
            {recentClosed.map((d) => {
              const et = d.executed_trades[0];
              const out = et?.trade_outcomes[0];
              const isWin = out?.result === "win";
              const isLoss = out?.result === "loss";
              return (
                <Link
                  key={d.id}
                  href={`/app/operacoes/${et.id}`}
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
                        {out.pnl_money > 0 ? "+" : ""}R$ {out.pnl_money.toFixed(2)}
                      </p>
                    )}
                    <p className="text-[10px] text-slate-600">
                      {et.closed_at ? new Date(et.closed_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "—"}
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
        {/* Brain Python */}
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
                Brain ativo · {robotInstance?.name ?? "instância"}
                {motorLastSeenLabel ? ` · ${motorLastSeenLabel}` : ""}
              </span>
            ) : (
              <span className="text-slate-600">
                Motor desconectado. Conecte em modo demo para ativar.
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
