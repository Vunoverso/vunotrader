import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

type Goal = "max_profit" | "consistency" | "low_drawdown";
type Regime = "tendencia" | "lateral" | "volatil" | "unknown";
type StopLossMode = "atr" | "fixed_points";

type TradeSample = {
  created_at: string;
  day: string;
  confidence: number;
  risk_pct: number;
  pnl_money: number;
  result: "win" | "loss" | "breakeven";
  regime: Regime;
  side: "buy" | "sell";
};

type ProfilePreset = {
  profile: "conservative" | "balanced" | "aggressive";
  label: string;
  risk_pct: number;
  max_drawdown_pct: number;
  drawdown_pause_pct: number;
  max_consecutive_losses: number;
  max_trades_per_day: number;
  auto_reduce_risk: boolean;
  per_trade_stop_loss_mode: StopLossMode;
  per_trade_stop_loss_value: number;
  per_trade_take_profit_rr: number;
  allowed_regimes: Regime[];
};

type SimulationResult = {
  profile: ProfilePreset["profile"];
  label: string;
  eligible_trades: number;
  simulated_trades: number;
  expected_pnl: number;
  total_pnl: number;
  drawdown_pct: number;
  win_rate: number;
  consistency_score: number;
  avg_win: number;
  avg_loss: number;
  global_bias: number;
  patch: Record<string, string | boolean>;
  explanation_hint: string;
};

const MIN_POINTS = 50;
const WINDOW_DAYS = 90;
const GLOBAL_MIN_SAMPLES = 20;

const PRESETS: ProfilePreset[] = [
  {
    profile: "conservative",
    label: "Conservador",
    risk_pct: 0.5,
    max_drawdown_pct: 3,
    drawdown_pause_pct: 2.5,
    max_consecutive_losses: 2,
    max_trades_per_day: 3,
    auto_reduce_risk: true,
    per_trade_stop_loss_mode: "atr",
    per_trade_stop_loss_value: 1.8,
    per_trade_take_profit_rr: 1.5,
    allowed_regimes: ["tendencia"],
  },
  {
    profile: "balanced",
    label: "Equilibrado",
    risk_pct: 1.0,
    max_drawdown_pct: 5,
    drawdown_pause_pct: 5,
    max_consecutive_losses: 3,
    max_trades_per_day: 5,
    auto_reduce_risk: true,
    per_trade_stop_loss_mode: "atr",
    per_trade_stop_loss_value: 2.0,
    per_trade_take_profit_rr: 2.0,
    allowed_regimes: ["tendencia", "lateral"],
  },
  {
    profile: "aggressive",
    label: "Agressivo",
    risk_pct: 2.0,
    max_drawdown_pct: 8,
    drawdown_pause_pct: 8,
    max_consecutive_losses: 5,
    max_trades_per_day: 8,
    auto_reduce_risk: false,
    per_trade_stop_loss_mode: "atr",
    per_trade_stop_loss_value: 2.2,
    per_trade_take_profit_rr: 2.5,
    allowed_regimes: ["tendencia", "lateral", "volatil", "unknown"],
  },
];

function parseRegimeFromRationale(rationale: string | null | undefined): Regime {
  const match = rationale?.match(/^\[(TENDENCIA|LATERAL|VOLATIL)\]/i);
  if (!match) return "unknown";
  const value = match[1].toLowerCase();
  if (value === "tendencia" || value === "lateral" || value === "volatil") return value;
  return "unknown";
}

function clamp(value: number, min = 0, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function normalize(value: number, min: number, max: number) {
  if (max <= min) return 1;
  return clamp((value - min) / (max - min));
}

function safeNumber(value: unknown, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function stdDev(values: number[]) {
  if (values.length <= 1) return 0;
  const mean = values.reduce((sum, item) => sum + item, 0) / values.length;
  const variance = values.reduce((sum, item) => sum + (item - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function buildPatch(profile: ProfilePreset) {
  return {
    risk_per_trade_pct: String(profile.risk_pct),
    max_drawdown_pct: String(profile.max_drawdown_pct),
    drawdown_pause_pct: String(profile.drawdown_pause_pct),
    max_consecutive_losses: String(profile.max_consecutive_losses),
    max_trades_per_day: String(profile.max_trades_per_day),
    auto_reduce_risk: profile.auto_reduce_risk,
    per_trade_stop_loss_mode: profile.per_trade_stop_loss_mode,
    per_trade_stop_loss_value: String(profile.per_trade_stop_loss_value),
    per_trade_take_profit_rr: String(profile.per_trade_take_profit_rr),
  };
}

function simulateProfile(
  trades: TradeSample[],
  profile: ProfilePreset,
  capitalUsd: number,
  globalBias: number
): SimulationResult {
  const eligible = trades.filter((trade) => profile.allowed_regimes.includes(trade.regime));
  const byDay = new Map<string, TradeSample[]>();
  for (const trade of eligible) {
    const list = byDay.get(trade.day) ?? [];
    list.push(trade);
    byDay.set(trade.day, list);
  }

  const selected: TradeSample[] = [];
  for (const list of byDay.values()) {
    const ordered = [...list].sort((a, b) => b.confidence - a.confidence);
    selected.push(...ordered.slice(0, profile.max_trades_per_day));
  }

  const scaledPnls = selected.map((trade) => {
    const baseRisk = trade.risk_pct > 0 ? trade.risk_pct : 1;
    return trade.pnl_money * (profile.risk_pct / baseRisk);
  });

  let peak = 0;
  let equity = 0;
  let maxDrawdownMoney = 0;
  for (const pnl of scaledPnls) {
    equity += pnl;
    peak = Math.max(peak, equity);
    maxDrawdownMoney = Math.max(maxDrawdownMoney, peak - equity);
  }

  const wins = scaledPnls.filter((pnl) => pnl > 0);
  const losses = scaledPnls.filter((pnl) => pnl < 0);
  const totalPnl = scaledPnls.reduce((sum, pnl) => sum + pnl, 0);
  const simulatedTrades = scaledPnls.length;
  const winRate = simulatedTrades > 0 ? wins.length / simulatedTrades : 0;
  const avgWin = wins.length > 0 ? wins.reduce((sum, pnl) => sum + pnl, 0) / wins.length : 0;
  const avgLoss = losses.length > 0 ? Math.abs(losses.reduce((sum, pnl) => sum + pnl, 0) / losses.length) : 0;
  const lossRate = simulatedTrades > 0 ? losses.length / simulatedTrades : 0;
  const expectedValue = (winRate * avgWin) - (lossRate * avgLoss);
  const volatilityPenalty = stdDev(scaledPnls) / Math.max(1, Math.abs(totalPnl / Math.max(simulatedTrades, 1)) || 1);
  const consistencyScore = winRate - Math.min(1, volatilityPenalty / 10);
  const drawdownPct = capitalUsd > 0 ? (maxDrawdownMoney / capitalUsd) * 100 : 0;

  return {
    profile: profile.profile,
    label: profile.label,
    eligible_trades: eligible.length,
    simulated_trades: simulatedTrades,
    expected_pnl: Number(expectedValue.toFixed(2)),
    total_pnl: Number(totalPnl.toFixed(2)),
    drawdown_pct: Number(drawdownPct.toFixed(2)),
    win_rate: Number(winRate.toFixed(4)),
    consistency_score: Number(consistencyScore.toFixed(4)),
    avg_win: Number(avgWin.toFixed(2)),
    avg_loss: Number(avgLoss.toFixed(2)),
    global_bias: Number(globalBias.toFixed(4)),
    patch: buildPatch(profile),
    explanation_hint: `${profile.label}: risco ${profile.risk_pct}% e até ${profile.max_trades_per_day} trades/dia.`,
  };
}

function scoreProfiles(results: SimulationResult[], goal: Goal) {
  const expectedValues = results.map((r) => r.expected_pnl);
  const totalPnls = results.map((r) => r.total_pnl);
  const consistencyScores = results.map((r) => r.consistency_score);
  const drawdowns = results.map((r) => r.drawdown_pct);
  const globalBiases = results.map((r) => r.global_bias);

  const ranges = {
    expectedMin: Math.min(...expectedValues),
    expectedMax: Math.max(...expectedValues),
    totalMin: Math.min(...totalPnls),
    totalMax: Math.max(...totalPnls),
    consistencyMin: Math.min(...consistencyScores),
    consistencyMax: Math.max(...consistencyScores),
    drawdownMin: Math.min(...drawdowns),
    drawdownMax: Math.max(...drawdowns),
    globalMin: Math.min(...globalBiases),
    globalMax: Math.max(...globalBiases),
  };

  return results
    .map((result) => {
      const expectedNorm = normalize(result.expected_pnl, ranges.expectedMin, ranges.expectedMax);
      const totalNorm = normalize(result.total_pnl, ranges.totalMin, ranges.totalMax);
      const consistencyNorm = normalize(result.consistency_score, ranges.consistencyMin, ranges.consistencyMax);
      const drawdownInv = 1 - normalize(result.drawdown_pct, ranges.drawdownMin, ranges.drawdownMax);
      const globalNorm = normalize(result.global_bias, ranges.globalMin, ranges.globalMax);

      let score = 0;
      if (goal === "max_profit") {
        score = expectedNorm * 0.55 + totalNorm * 0.25 + drawdownInv * 0.1 + globalNorm * 0.1;
      } else if (goal === "consistency") {
        score = consistencyNorm * 0.5 + drawdownInv * 0.3 + expectedNorm * 0.1 + globalNorm * 0.1;
      } else {
        score = drawdownInv * 0.6 + consistencyNorm * 0.25 + globalNorm * 0.1 + expectedNorm * 0.05;
      }

      return { ...result, score: Number(score.toFixed(4)) };
    })
    .sort((a, b) => b.score - a.score);
}

function buildExplanation(best: ReturnType<typeof scoreProfiles>[number], goal: Goal, points: number) {
  const goalLabel =
    goal === "max_profit"
      ? "maior potencial de lucro"
      : goal === "consistency"
      ? "mais consistência"
      : "menor drawdown";

  return [
    `O perfil ${best.label.toUpperCase()} foi o melhor para ${goalLabel}.`,
    `Ele simulou ${best.simulated_trades} operações com win rate de ${(best.win_rate * 100).toFixed(1)}% e drawdown estimado de ${best.drawdown_pct.toFixed(1)}%.`,
    `O lucro esperado por operação ficou em R$ ${best.expected_pnl.toFixed(2)} e o resultado total estimado em R$ ${best.total_pnl.toFixed(2)}.`,
    `Baseado em ${points} decisões reais dos últimos ${WINDOW_DAYS} dias.`,
  ].join(" ");
}

async function fetchGlobalBias(symbol: string, timeframe: string) {
  try {
    const admin = createAdminClient();
    const { data, error } = await admin
      .from("global_memory_signals")
      .select("regime, win_rate, sample_size")
      .eq("symbol", symbol)
      .eq("timeframe", timeframe)
      .gte("sample_size", GLOBAL_MIN_SAMPLES)
      .limit(200);

    if (error || !data || data.length === 0) {
      return { used: false, byRegime: new Map<Regime, number>() };
    }

    const bucket = new Map<Regime, { sum: number; count: number }>();
    for (const row of data) {
      const regime = ["tendencia", "lateral", "volatil"].includes(String(row.regime))
        ? (row.regime as Regime)
        : "unknown";
      const current = bucket.get(regime) ?? { sum: 0, count: 0 };
      current.sum += safeNumber(row.win_rate, 0);
      current.count += 1;
      bucket.set(regime, current);
    }

    const byRegime = new Map<Regime, number>();
    for (const [regime, values] of bucket.entries()) {
      byRegime.set(regime, values.count > 0 ? values.sum / values.count : 0);
    }

    return { used: true, byRegime };
  } catch {
    return { used: false, byRegime: new Map<Regime, number>() };
  }
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return NextResponse.json({ error: "Não autenticado." }, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  const symbol = String(body?.symbol ?? "").trim().toUpperCase();
  const timeframe = String(body?.timeframe ?? "").trim().toUpperCase();
  const goal = String(body?.goal ?? "consistency").trim() as Goal;

  if (!symbol || !timeframe) {
    return NextResponse.json({ error: "Informe ativo e timeframe." }, { status: 400 });
  }

  if (!["max_profit", "consistency", "low_drawdown"].includes(goal)) {
    return NextResponse.json({ error: "Objetivo inválido." }, { status: 400 });
  }

  const since = new Date(Date.now() - WINDOW_DAYS * 24 * 60 * 60 * 1000).toISOString();

  const [paramsResult, tradesResult, globalBias] = await Promise.all([
    supabase
      .from("user_parameters")
      .select("capital_usd")
      .eq("user_id", user.id)
      .limit(1)
      .single(),
    supabase
      .from("trade_decisions")
      .select(`
        id,
        created_at,
        symbol,
        timeframe,
        side,
        confidence,
        risk_pct,
        rationale,
        executed_trades (
          trade_outcomes (
            result,
            pnl_money
          )
        )
      `)
      .eq("user_id", user.id)
      .eq("symbol", symbol)
      .eq("timeframe", timeframe)
      .gte("created_at", since)
      .order("created_at", { ascending: false })
      .limit(1000),
    fetchGlobalBias(symbol, timeframe),
  ]);

  if (tradesResult.error) {
    return NextResponse.json({ error: "Erro ao consultar histórico." }, { status: 500 });
  }

  const capitalUsd = safeNumber(paramsResult.data?.capital_usd, 10000);
  const samples: TradeSample[] = [];

  for (const row of tradesResult.data ?? []) {
    const side = String(row.side ?? "hold").toLowerCase();
    if (side !== "buy" && side !== "sell") continue;

    const executed = Array.isArray(row.executed_trades) ? row.executed_trades : [];
    const firstTrade = executed[0];
    const outcomes = Array.isArray(firstTrade?.trade_outcomes) ? firstTrade.trade_outcomes : [];
    const outcome = outcomes[0];
    const result = String(outcome?.result ?? "").toLowerCase();
    if (result !== "win" && result !== "loss" && result !== "breakeven") continue;

    samples.push({
      created_at: row.created_at,
      day: row.created_at.slice(0, 10),
      confidence: safeNumber(row.confidence, 0),
      risk_pct: safeNumber(row.risk_pct, 1),
      pnl_money: safeNumber(outcome?.pnl_money, 0),
      result: result as TradeSample["result"],
      regime: parseRegimeFromRationale(row.rationale),
      side: side as TradeSample["side"],
    });
  }

  if (samples.length < MIN_POINTS) {
    return NextResponse.json(
      {
        status: "insufficient_data",
        message: "Dados insuficientes para recomendação confiável.",
        metrics: {
          data_points: samples.length,
          minimum_required: MIN_POINTS,
          based_on: ["local_history"],
        },
      },
      { status: 200 }
    );
  }

  const simulated = PRESETS.map((preset) => {
    const biasValues = samples
      .map((sample) => globalBias.byRegime.get(sample.regime) ?? null)
      .filter((value): value is number => value !== null);
    const bias = biasValues.length > 0
      ? biasValues.reduce((sum, value) => sum + value, 0) / biasValues.length
      : 0;
    return simulateProfile(samples, preset, capitalUsd, bias);
  }).filter((item) => item.simulated_trades > 0);

  if (simulated.length === 0) {
    return NextResponse.json(
      {
        status: "insufficient_data",
        message: "Não há operações suficientes dentro dos perfis sugeridos.",
        metrics: {
          data_points: samples.length,
          minimum_required: MIN_POINTS,
          based_on: ["local_history"],
        },
      },
      { status: 200 }
    );
  }

  const ranked = scoreProfiles(simulated, goal);
  const best = ranked[0];
  const basedOn = ["local_history", ...(globalBias.used ? ["global_memory"] : [])];
  const confidence = clamp(Math.sqrt(samples.length) / 12 + (globalBias.used ? 0.1 : 0), 0.45, 0.95);

  return NextResponse.json({
    status: "ok",
    recommended_profile: best.profile,
    recommendation: best,
    alternatives: ranked.slice(0, 3),
    explanation: buildExplanation(best, goal, samples.length),
    metrics: {
      data_points: samples.length,
      confidence: Number(confidence.toFixed(2)),
      based_on: basedOn,
      window_days: WINDOW_DAYS,
    },
  });
}
