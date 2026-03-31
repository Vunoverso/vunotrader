"use client";

/**
 * TradeScoreCard — Client Component
 * Chama GET /api/decision-score com os parâmetros da operação
 * e exibe o score histórico daquela configuração.
 */

import { useEffect, useState } from "react";

type ScoreData = {
  score: number;
  win_rate: number;
  sample_size: number;
  regime_win_rate: number | null;
  confidence_tier: "low" | "medium" | "high" | null;
  filters_applied: string[];
};

function ScoreBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 55 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${Math.min(pct, 100)}%` }}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="text-center">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-0.5 text-lg font-bold text-slate-100">{value}</p>
      {sub && <p className="text-[10px] text-slate-600">{sub}</p>}
    </div>
  );
}

export default function TradeScoreCard({
  symbol,
  timeframe,
  side,
  regime,
  confidence,
}: {
  symbol: string | null;
  timeframe: string | null;
  side: string | null;
  regime: string | null;
  confidence: number | null;
}) {
  const [data, setData] = useState<ScoreData | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (symbol)    params.set("symbol", symbol);
    if (timeframe) params.set("timeframe", timeframe);
    if (side)      params.set("side", side);
    if (regime)    params.set("regime", regime);
    if (confidence != null) params.set("confidence", String(confidence));

    fetch(`/api/decision-score?${params.toString()}`)
      .then((r) => {
        if (!r.ok) throw new Error("status " + r.status);
        return r.json();
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setErr(String(e)); setLoading(false); });
  }, [symbol, timeframe, side, regime, confidence]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 animate-pulse">
        <div className="h-2.5 w-32 rounded bg-slate-800" />
        <div className="mt-4 h-2 rounded bg-slate-800" />
      </div>
    );
  }

  if (err || !data) {
    return null; // falha silenciosa — não quebra a página de detalhe
  }

  const winPct     = Math.round(data.win_rate * 100);
  const scorePct   = Math.round(data.score * 100);
  const regimePct  = data.regime_win_rate != null
    ? Math.round(data.regime_win_rate * 100)
    : null;

  const tierLabel  = { high: "Alta", medium: "Média", low: "Baixa" }[data.confidence_tier ?? "low"] ?? "—";
  const tierColor  = {
    high:   "text-emerald-400",
    medium: "text-amber-400",
    low:    "text-slate-500",
  }[data.confidence_tier ?? "low"] ?? "text-slate-500";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
      <div className="border-b border-slate-800 px-5 py-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Score histórico desta configuração
        </h2>
        {data.sample_size === 0 && (
          <span className="text-xs text-slate-600">Sem dados suficientes</span>
        )}
      </div>

      {data.sample_size === 0 ? (
        <div className="px-5 py-5 text-sm text-slate-600">
          Ainda não há operações encerradas com esta combinação de símbolo, timeframe e direção.
          O score será calculado automaticamente à medida que o histórico crescer.
        </div>
      ) : (
        <div className="px-5 py-5 space-y-5">
          {/* Score principal */}
          <div>
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-slate-500">Score ponderado</span>
              <span className="font-semibold text-slate-200">{scorePct}%</span>
            </div>
            <ScoreBar value={data.score} />
            <p className="mt-1.5 text-[10px] text-slate-600">
              Baseado em {data.sample_size} operação{data.sample_size !== 1 ? "ões" : ""} encerrada{data.sample_size !== 1 ? "s" : ""}.
              Penaliza amostras pequenas.
            </p>
          </div>

          {/* Métricas em grid */}
          <div className="grid grid-cols-3 gap-2 rounded-lg border border-slate-800 bg-slate-800/40 p-4">
            <Stat label="Win Rate" value={`${winPct}%`} sub={`${data.sample_size} trades`} />
            <Stat
              label="Regime"
              value={regimePct != null ? `${regimePct}%` : "—"}
              sub={regime ?? undefined}
            />
            <Stat
              label="Confiança IA"
              value={tierLabel}
              sub={<span className={tierColor}>{tierLabel}</span> as unknown as string}
            />
          </div>

          {/* Filtros aplicados */}
          {data.filters_applied.length > 0 && (
            <p className="text-[10px] text-slate-700">
              Filtros: {data.filters_applied.join(" · ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
