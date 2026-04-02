"use client";

import { useState } from "react";
import Link from "next/link";

const BRAZIL_TIME_ZONE = "America/Sao_Paulo";
const DATETIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: BRAZIL_TIME_ZONE,
});

// ── Tipos ────────────────────────────────────────────────────────
type TradeResult = "win" | "loss" | "breakeven";
type TradeStatus = "open" | "closed" | "canceled";
type TradeSide   = "buy" | "sell" | "hold";

interface TradeRow {
  id: string;
  broker_ticket: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  lot: number | null;
  status: TradeStatus;
  opened_at: string | null;
  closed_at: string | null;
  trade_decisions: {
    symbol: string;
    timeframe: string;
    side: TradeSide;
    confidence: number | null;
    risk_pct: number | null;
    rationale: string | null;
    mode: string;
  } | null;
  trade_outcomes: {
    result: TradeResult;
    pnl_money: number | null;
    pnl_points: number | null;
    win_loss_reason: string | null;
  } | null;
}

// ── Helpers visuais ───────────────────────────────────────────────
function SideBadge({ side }: { side: TradeSide }) {
  if (side === "buy")
    return <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-400">COMPRA</span>;
  if (side === "sell")
    return <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold bg-red-500/20 text-red-400">VENDA</span>;
  return <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold bg-slate-700 text-slate-400">HOLD</span>;
}

function ResultBadge({ result }: { result: TradeResult | null | undefined }) {
  if (!result) return <span className="text-xs text-slate-600">—</span>;
  if (result === "win")
    return <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-400">WIN</span>;
  if (result === "loss")
    return <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold bg-red-500/20 text-red-400">LOSS</span>;
  return <span className="rounded px-1.5 py-0.5 text-[10px] font-semibold bg-slate-700 text-slate-400">EMPATE</span>;
}

function PnlCell({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-xs text-slate-600">—</span>;
  const isPos = value > 0;
  return (
    <span className={`text-sm font-medium ${isPos ? "text-emerald-400" : value < 0 ? "text-red-400" : "text-slate-400"}`}>
      {isPos ? "+" : ""}R$ {value.toFixed(2)}
    </span>
  );
}

function formatDt(dt: string | null) {
  if (!dt) return "—";
  return DATETIME_FORMATTER.format(new Date(dt));
}

// ── Linha expandida ───────────────────────────────────────────────
function ExpandedRow({ trade }: { trade: TradeRow }) {
  const d = trade.trade_decisions;
  const o = trade.trade_outcomes;
  return (
    <tr className="bg-slate-800/50">
      <td colSpan={9} className="px-6 py-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-xs text-slate-400">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-1">Decisão da IA</p>
            <p><span className="text-slate-500">Confiança:</span> {d?.confidence != null ? `${(d.confidence * 100).toFixed(1)}%` : "—"}</p>
            <p><span className="text-slate-500">Risco sugerido:</span> {d?.risk_pct != null ? `${d.risk_pct}%` : "—"}</p>
            <p><span className="text-slate-500">Modo:</span> {d?.mode ?? "—"}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-1">Níveis</p>
            <p><span className="text-slate-500">Entrada:</span> {trade.entry_price ?? "—"}</p>
            <p><span className="text-slate-500">Stop Loss:</span> {trade.stop_loss ?? "—"}</p>
            <p><span className="text-slate-500">Take Profit:</span> {trade.take_profit ?? "—"}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-1">Análise</p>
            <p className="text-slate-400 leading-relaxed">{d?.rationale || o?.win_loss_reason || "Sem análise registrada."}</p>
          </div>
        </div>
      </td>
    </tr>
  );
}

// ── Sumário de métricas ───────────────────────────────────────────
function Summary({ trades }: { trades: TradeRow[] }) {
  const closed = trades.filter((t) => t.trade_outcomes);
  const wins   = closed.filter((t) => t.trade_outcomes?.result === "win").length;
  const wr     = closed.length > 0 ? (wins / closed.length) * 100 : null;
  const pnl    = closed.reduce((acc, t) => acc + (t.trade_outcomes?.pnl_money ?? 0), 0);

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-6">
      {[
        { label: "Total de operações", value: trades.length.toString(), accent: "slate" },
        { label: "Encerradas", value: closed.length.toString(), accent: "slate" },
        {
          label: "Win Rate",
          value: wr !== null ? `${wr.toFixed(1)}%` : "—",
          accent: wr === null ? "slate" : wr >= 60 ? "green" : "red",
        },
        {
          label: "PnL total",
          value: pnl === 0 ? "R$ 0,00" : `${pnl > 0 ? "+" : ""}R$ ${pnl.toFixed(2)}`,
          accent: pnl > 0 ? "green" : pnl < 0 ? "red" : "slate",
        },
      ].map((m) => (
        <div key={m.label} className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
          <p className="text-xs text-slate-500 mb-1">{m.label}</p>
          <p className={`text-xl font-bold ${
            m.accent === "green" ? "text-emerald-400"
            : m.accent === "red" ? "text-red-400"
            : "text-slate-200"
          }`}>{m.value}</p>
        </div>
      ))}
    </div>
  );
}

// ── Tabela principal ──────────────────────────────────────────────
export default function OperacoesTable({ trades }: { trades: TradeRow[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "win" | "loss" | "open">("all");

  const filtered = trades.filter((t) => {
    if (filter === "open")  return t.status === "open";
    if (filter === "win")   return t.trade_outcomes?.result === "win";
    if (filter === "loss")  return t.trade_outcomes?.result === "loss";
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto space-y-4">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-slate-100">Operações</h1>
        <div className="flex gap-1.5">
          {(["all", "open", "win", "loss"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                filter === f
                  ? "bg-sky-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {{ all: "Todas", open: "Abertas", win: "WIN", loss: "LOSS" }[f]}
            </button>
          ))}
        </div>
      </div>

      <Summary trades={trades} />

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/50 py-20 text-center">
          <p className="text-sm text-slate-500 mb-1">Nenhuma operação encontrada</p>
          <p className="text-xs text-slate-600">
            {trades.length === 0
              ? "O brain ainda não enviou operações para o banco. Inicie o robô para começar."
              : "Nenhuma operação neste filtro."}
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">Ativo</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">Lado</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">TF</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">Lote</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">Abertura</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">Fechamento</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">Resultado</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500">PnL</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500" />
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <>
                    <tr
                      key={t.id}
                      className="border-b border-slate-800/60 hover:bg-slate-800/40 cursor-pointer transition-colors"
                      onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                    >
                      <td className="px-4 py-3 font-medium text-slate-200">
                        {t.trade_decisions?.symbol ?? "—"}
                      </td>
                      <td className="px-4 py-3">
                        <SideBadge side={t.trade_decisions?.side ?? "hold"} />
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {t.trade_decisions?.timeframe ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {t.lot ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {formatDt(t.opened_at)}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs">
                        {formatDt(t.closed_at)}
                      </td>
                      <td className="px-4 py-3">
                        <ResultBadge result={t.trade_outcomes?.result} />
                      </td>
                      <td className="px-4 py-3">
                        <PnlCell value={t.trade_outcomes?.pnl_money} />
                      </td>
                      <td className="px-4 py-3 text-slate-600 text-xs">
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/app/operacoes/${t.id}`}
                            className="rounded px-2 py-1 text-[10px] font-medium bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition-colors"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Ver
                          </Link>
                          <span>{expanded === t.id ? "▲" : "▼"}</span>
                        </div>
                      </td>
                    </tr>
                    {expanded === t.id && <ExpandedRow key={`e-${t.id}`} trade={t} />}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
