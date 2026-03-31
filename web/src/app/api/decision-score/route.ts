/**
 * GET /api/decision-score
 *
 * Retorna o score histórico de uma configuração de trade com base nos
 * registros reais de trade_decisions + trade_outcomes do usuário autenticado.
 *
 * Query params (todos opcionais, melhora granularidade quando fornecidos):
 *   symbol      – ex.: "WINM26"
 *   timeframe   – ex.: "M5"
 *   side        – "buy" | "sell"
 *   regime      – "tendencia" | "lateral" | "volatil"
 *   confidence  – número 0-1 (agrupa em tier automaticamente)
 *
 * Resposta:
 *   {
 *     score:             number,   // win_rate ponderado pelo tamanho da amostra (0-1)
 *     win_rate:          number,
 *     sample_size:       number,
 *     regime_win_rate:   number | null,   // win_rate filtrado pelo regime, se fornecido
 *     confidence_tier:   "low" | "medium" | "high" | null,
 *     filters_applied:   string[],
 *   }
 *
 * Requer sessão autenticada (Supabase Auth via cookie).
 * Retorna 401 se não autenticado, 400 em caso de parâmetros inválidos.
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// ────────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────────

function confidenceTier(conf: number | null): "low" | "medium" | "high" | null {
  if (conf === null) return null;
  if (conf >= 0.70) return "high";
  if (conf >= 0.50) return "medium";
  return "low";
}

/**
 * Calcula win_rate e score ponderado a partir de linhas de trade_decisions
 * que possuem trade_outcomes relacionados.
 *
 * @param rows  Array de objetos com { result: string | null }
 * @returns     { win_rate, sample_size, score }
 */
function computeStats(rows: { result: string | null }[]): {
  win_rate: number;
  sample_size: number;
  score: number;
} {
  const withResult = rows.filter((r) => r.result === "win" || r.result === "loss");
  const wins = withResult.filter((r) => r.result === "win").length;
  const n = withResult.length;

  if (n === 0) {
    return { win_rate: 0, sample_size: 0, score: 0 };
  }

  const win_rate = wins / n;
  // score = win_rate ajustado com fator de confiança estatística (Wilson-like simples)
  // penaliza amostras pequenas: score cresce com sqrt(n), satura em 1.0
  const weight = Math.min(1.0, Math.sqrt(n) / 10);
  const score = parseFloat((win_rate * weight).toFixed(4));

  return { win_rate: parseFloat(win_rate.toFixed(4)), sample_size: n, score };
}

// ────────────────────────────────────────────────────────────────
// Route Handler
// ────────────────────────────────────────────────────────────────
export async function GET(req: NextRequest): Promise<NextResponse> {
  // 1. Auth
  const supabase = await createClient();
  const {
    data: { user },
    error: authError,
  } = await supabase.auth.getUser();

  if (authError || !user) {
    return NextResponse.json({ error: "Não autenticado." }, { status: 401 });
  }

  // 2. Parâmetros de consulta
  const { searchParams } = req.nextUrl;
  const symbol    = searchParams.get("symbol")?.trim()     ?? null;
  const timeframe = searchParams.get("timeframe")?.trim()  ?? null;
  const side      = searchParams.get("side")?.trim()       ?? null;
  const regime    = searchParams.get("regime")?.trim()     ?? null;
  const confRaw   = searchParams.get("confidence");
  const confidence = confRaw !== null ? parseFloat(confRaw) : null;

  if (side && side !== "buy" && side !== "sell") {
    return NextResponse.json(
      { error: "Parâmetro 'side' inválido. Use 'buy' ou 'sell'." },
      { status: 400 }
    );
  }

  if (
    regime &&
    !["tendencia", "lateral", "volatil"].includes(regime)
  ) {
    return NextResponse.json(
      { error: "Parâmetro 'regime' inválido. Use tendencia | lateral | volatil." },
      { status: 400 }
    );
  }

  // 3. Query base: trade_decisions com outcome via FK
  //    Filtra apenas os registros do usuário autenticado (RLS já faz isso,
  //    mas usamos .eq() explícito como defesa em profundidade).
  let query = supabase
    .from("trade_decisions")
    .select("id, symbol, timeframe, side, confidence, regime, trade_outcomes(result)")
    .eq("user_id", user.id)
    .limit(5000);

  const filtersApplied: string[] = [];

  if (symbol) {
    query = query.eq("symbol", symbol);
    filtersApplied.push(`symbol=${symbol}`);
  }
  if (timeframe) {
    query = query.eq("timeframe", timeframe);
    filtersApplied.push(`timeframe=${timeframe}`);
  }
  if (side) {
    query = query.eq("action", side);
    filtersApplied.push(`side=${side}`);
  }

  const { data: rows, error: qErr } = await query;

  if (qErr) {
    console.error("[decision-score] Erro na query:", qErr.message);
    return NextResponse.json({ error: "Erro ao consultar dados." }, { status: 500 });
  }

  // 4. Achata a relação 1-N (trade_decisions → trade_outcomes)
  type FlatRow = { result: string | null; regime: string | null };
  const flat: FlatRow[] = [];
  for (const d of rows ?? []) {
    const outcomes =
      (d as unknown as { trade_outcomes: { result: string }[] | null })
        .trade_outcomes ?? [];
    const dRegime = (d as unknown as { regime: string | null }).regime;
    if (outcomes.length === 0) {
      flat.push({ result: null, regime: dRegime });
    } else {
      for (const o of outcomes) {
        flat.push({ result: o.result, regime: dRegime });
      }
    }
  }

  // 5. Stats gerais
  const general = computeStats(flat);

  // 6. Stats filtradas pelo regime (se fornecido)
  let regimeWinRate: number | null = null;
  if (regime) {
    const regimeRows = flat.filter((r) => r.regime === regime);
    const regimeStats = computeStats(regimeRows);
    regimeWinRate = regimeStats.sample_size > 0 ? regimeStats.win_rate : null;
    filtersApplied.push(`regime=${regime}`);
  }

  // 7. Tier de confiança
  const tier = confidenceTier(confidence);
  if (tier) filtersApplied.push(`confidence_tier=${tier}`);

  return NextResponse.json({
    score:           general.score,
    win_rate:        general.win_rate,
    sample_size:     general.sample_size,
    regime_win_rate: regimeWinRate,
    confidence_tier: tier,
    filters_applied: filtersApplied,
  });
}
