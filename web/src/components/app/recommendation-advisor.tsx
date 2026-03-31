"use client";

import { useMemo, useState } from "react";
import type { ParametrosData } from "@/components/app/parametros-form";

type Goal = "max_profit" | "consistency" | "low_drawdown";

type RecommendationItem = {
  profile: "conservative" | "balanced" | "aggressive";
  label: string;
  score: number;
  expected_pnl: number;
  total_pnl: number;
  drawdown_pct: number;
  win_rate: number;
  simulated_trades: number;
  patch: Record<string, string | boolean>;
};

type RecommendationResponse = {
  status: "ok" | "insufficient_data";
  message?: string;
  explanation?: string;
  recommendation?: RecommendationItem;
  alternatives?: RecommendationItem[];
  metrics?: {
    data_points: number;
    minimum_required?: number;
    confidence?: number;
    based_on?: string[];
    window_days?: number;
  };
};

const GOALS: { value: Goal; label: string; hint: string }[] = [
  {
    value: "consistency",
    label: "Mais consistência",
    hint: "Prioriza estabilidade e win rate mais confiável.",
  },
  {
    value: "max_profit",
    label: "Mais lucro",
    hint: "Aceita mais oscilação para buscar retorno maior.",
  },
  {
    value: "low_drawdown",
    label: "Mais proteção",
    hint: "Reduz exposição e drawdown esperado.",
  },
];

function formatMoney(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function RecommendationAdvisor({
  form,
  onApply,
}: {
  form: ParametrosData;
  onApply: (patch: Record<string, string | boolean>) => void;
}) {
  const allowedSymbols = useMemo(
    () => form.allowed_symbols.split(",").map((item) => item.trim().toUpperCase()).filter(Boolean),
    [form.allowed_symbols]
  );

  const [symbol, setSymbol] = useState(allowedSymbols[0] ?? "WINM26");
  const [timeframe, setTimeframe] = useState("M5");
  const [goal, setGoal] = useState<Goal>("consistency");
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<RecommendationResponse | null>(null);

  async function handleGenerate() {
    setState("loading");
    setResult(null);

    try {
      const response = await fetch("/api/recommendation/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, timeframe, goal }),
      });
      const data = (await response.json()) as RecommendationResponse;
      setResult(data);
      setState(response.ok ? "done" : "error");
    } catch {
      setResult({ status: "insufficient_data", message: "Falha ao consultar recomendação." });
      setState("error");
    }
  }

  const best = result?.recommendation;

  return (
    <section className="rounded-xl border border-cyan-500/20 bg-slate-900 p-6 space-y-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
            Recommendation Engine
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            O sistema compara perfis com base no seu histórico real e sugere a configuração mais adequada.
            A decisão final continua sendo sua.
          </p>
        </div>
        <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-300">
          Sem chat opinativo. Só ranking com impacto financeiro.
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1.2fr_180px_1.2fr_auto]">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-500">Ativo</span>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            list="advisor-symbols"
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-cyan-500"
          />
          <datalist id="advisor-symbols">
            {allowedSymbols.map((item) => (
              <option key={item} value={item} />
            ))}
          </datalist>
        </label>

        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-500">Timeframe</span>
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-cyan-500"
          >
            {['M1', 'M5', 'M15', 'M30', 'H1'].map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-500">Objetivo</span>
          <select
            value={goal}
            onChange={(e) => setGoal(e.target.value as Goal)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-cyan-500"
          >
            {GOALS.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
          <p className="mt-1 text-[11px] text-slate-600">
            {GOALS.find((item) => item.value === goal)?.hint}
          </p>
        </label>

        <div className="flex items-end">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={state === "loading"}
            className="w-full rounded-lg border border-cyan-600/40 bg-cyan-600/20 px-4 py-2.5 text-sm font-semibold text-cyan-300 transition hover:bg-cyan-600/30 disabled:cursor-wait disabled:opacity-60"
          >
            {state === "loading" ? "Calculando..." : "Gerar sugestão"}
          </button>
        </div>
      </div>

      {result?.status === "insufficient_data" && (
        <div className="rounded-lg border border-amber-800/40 bg-amber-950/30 px-4 py-3 text-sm text-amber-300">
          {result.message ?? "Dados insuficientes para recomendação confiável."}
          {result.metrics && (
            <p className="mt-1 text-xs text-amber-400/80">
              Pontos disponíveis: {result.metrics.data_points} de {result.metrics.minimum_required ?? 50} mínimos.
            </p>
          )}
        </div>
      )}

      {best && result.status === "ok" && (
        <div className="space-y-4">
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-wider text-emerald-300">Perfil recomendado</p>
                <h3 className="mt-1 text-xl font-bold text-white">{best.label}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">
                  {result.explanation}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm sm:min-w-[320px]">
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
                  <p className="text-xs text-slate-500">Lucro esperado</p>
                  <p className="mt-1 font-semibold text-slate-100">{formatMoney(best.expected_pnl)}</p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
                  <p className="text-xs text-slate-500">Drawdown</p>
                  <p className="mt-1 font-semibold text-slate-100">{best.drawdown_pct.toFixed(1)}%</p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
                  <p className="text-xs text-slate-500">Win rate</p>
                  <p className="mt-1 font-semibold text-slate-100">{formatPct(best.win_rate)}</p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
                  <p className="text-xs text-slate-500">Amostras</p>
                  <p className="mt-1 font-semibold text-slate-100">{best.simulated_trades}</p>
                </div>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => onApply(best.patch)}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700"
              >
                Aplicar sugestão ao formulário
              </button>
              <p className="text-xs text-slate-400">
                Isso apenas preenche os campos. Nada é salvo sem sua confirmação.
              </p>
            </div>
          </div>

          {result.metrics && (
            <div className="flex flex-wrap gap-3 text-xs text-slate-400">
              <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1.5">
                Base: {(result.metrics.based_on ?? []).join(" + ")}
              </span>
              <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1.5">
                Janela: {result.metrics.window_days} dias
              </span>
              <span className="rounded-full border border-slate-800 bg-slate-900 px-3 py-1.5">
                Confiança do ranking: {result.metrics.confidence != null ? `${Math.round(result.metrics.confidence * 100)}%` : "—"}
              </span>
            </div>
          )}

          {result.alternatives && result.alternatives.length > 1 && (
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
              <h4 className="text-sm font-semibold text-slate-200">Alternativas comparáveis</h4>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {result.alternatives.map((item) => (
                  <div key={item.profile} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-slate-100">{item.label}</p>
                      <span className="text-xs text-slate-500">Score {item.score.toFixed(2)}</span>
                    </div>
                    <div className="mt-3 space-y-1 text-xs text-slate-400">
                      <p>Lucro esperado: <span className="text-slate-200">{formatMoney(item.expected_pnl)}</span></p>
                      <p>Drawdown: <span className="text-slate-200">{item.drawdown_pct.toFixed(1)}%</span></p>
                      <p>Win rate: <span className="text-slate-200">{formatPct(item.win_rate)}</span></p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
