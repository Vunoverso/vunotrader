"use client";

import * as XLSX from "xlsx";
import { useState } from "react";

type AuditOutcome = {
  result: "win" | "loss" | "breakeven";
  pnl_money: number | null;
  win_loss_reason: string | null;
  post_analysis: string | null;
};

type AuditTrade = {
  id: string;
  status: "open" | "closed" | "canceled";
  opened_at: string | null;
  closed_at: string | null;
  trade_outcomes: AuditOutcome[];
};

export type AuditRow = {
  id: string;
  symbol: string;
  timeframe: string;
  side: "buy" | "sell" | "hold";
  confidence: number | null;
  risk_pct: number | null;
  mode: string;
  rationale: string | null;
  created_at: string;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  outcome_status: string | null;
  outcome_profit: number | null;
  outcome_pips: number | null;
  closed_at: string | null;
  duration_seconds: number | null;
  post_analysis: string | null;
  executed_trades: AuditTrade[];
};

type ResultFilter = "all" | "win" | "loss" | "breakeven" | "pending" | "alta_conv_loss";
type ModeFilter = "all" | "observer" | "demo" | "real";
type PeriodFilter = "all" | "today" | "7d" | "30d";
type SortField = "created_at" | "pnl_money" | "confidence";
type SortDirection = "desc" | "asc";

function convictionBadge(confidence: number | null) {
  if (confidence == null) return null;
  const pct = confidence * 100;
  if (pct >= 75) return { label: `Alta ${pct.toFixed(0)}%`, cls: "bg-emerald-500/20 text-emerald-300" };
  if (pct >= 55) return { label: `Média ${pct.toFixed(0)}%`, cls: "bg-amber-500/20 text-amber-300" };
  return { label: `Baixa ${pct.toFixed(0)}%`, cls: "bg-slate-700 text-slate-400" };
}

function sideBadge(side: string) {
  if (side === "buy") return "bg-emerald-500/20 text-emerald-300";
  if (side === "sell") return "bg-red-500/20 text-red-300";
  return "bg-slate-700 text-slate-300";
}

function resultBadge(result?: string | null) {
  if (!result) return "bg-slate-700 text-slate-300";
  if (result === "win") return "bg-emerald-500/20 text-emerald-300";
  if (result === "loss") return "bg-red-500/20 text-red-300";
  return "bg-amber-500/20 text-amber-300";
}

function fmtDt(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDuration(seconds: number | null) {
  if (seconds == null || seconds <= 0) return "—";
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  const parts = [];
  if (hrs > 0) parts.push(`${hrs}h`);
  if (mins > 0) parts.push(`${mins}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);
  
  return parts.join(" ");
}

function csvEscape(value: string | number | null | undefined) {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function getOutcome(row: AuditRow) {
  // Prioridade 1: resultado real de executed_trades → trade_outcomes (Dual History)
  const realOutcome = row.executed_trades?.[0]?.trade_outcomes?.[0];
  if (realOutcome) {
    return {
      result: realOutcome.result,
      pnl_money: realOutcome.pnl_money,
      pnl_pips: null,
      win_loss_reason: realOutcome.win_loss_reason,
      post_analysis: realOutcome.post_analysis ?? row.post_analysis,
    };
  }
  // Prioridade 2: se trade está em execução (trade aberto mas ainda sem outcome)
  const openTrade = row.executed_trades?.[0];
  if (openTrade && openTrade.status === "open") {
    return {
      result: "executing" as const,
      pnl_money: null,
      pnl_pips: null,
      win_loss_reason: "Em execução no MT5",
      post_analysis: null,
    };
  }
  // Prioridade 3: colunas legadas de trade_decisions (compatibilidade retroativa)
  if (row.outcome_status && row.outcome_status !== "pending") {
    return {
      result: row.outcome_status as "win" | "loss" | "breakeven" | "executing",
      pnl_money: row.outcome_profit,
      pnl_pips: row.outcome_pips,
      win_loss_reason:
        row.outcome_status === "executing"
          ? "Em execução no MT5"
          : row.outcome_profit != null
          ? "Finalizado"
          : "Resultado Virtual",
      post_analysis: row.post_analysis,
    };
  }
  return null;
}

function getTrade(row: AuditRow) {
  return row.executed_trades?.[0];
}

function getSortablePnl(row: AuditRow) {
  const pnl = getOutcome(row)?.pnl_money;
  return pnl == null ? null : pnl;
}

function stripTechSuffix(rationale: string) {
  if (!rationale) return "";
  return rationale
    .replace(/\s*\|\s*SHADOW:.*$/i, "")
    .replace(/\s*\|\s*(tech|score|vpe|ADX|Stoch|factors):.*$/i, "")
    .replace(/^\[(BULLISH|BEARISH|LATERAL|TENDENCIA|VOLATIL)\]\s*/i, "")
    .replace(/^(BUY|SELL|HOLD)\|/i, "") 
    .trim();
}

function vpeBadges(rationale: string) {
  if (!rationale || !rationale.includes("factors=")) return [];
  const factorsPart = rationale.split("factors=")[1];
  const factors = factorsPart.split("|")[0].split(",");
  
  const b = [];
  if (factors.includes("ZONE_SUPPORT")) b.push({ label: "SUPORTE ATIVO", cls: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" });
  if (factors.includes("ZONE_RESISTANCE")) b.push({ label: "RESISTÊNCIA", cls: "bg-rose-500/20 text-rose-400 border border-rose-500/30" });
  if (factors.includes("INSIDE_BAR")) b.push({ label: "COMPRESSÃO", cls: "bg-blue-500/20 text-blue-400 border border-blue-500/30" });
  if (factors.includes("PIN_BAR_BULLISH") || factors.includes("PIN_BAR_BEARISH")) b.push({ label: "PIN BAR", cls: "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30" });
  if (factors.includes("ENGULFING_BULLISH") || factors.includes("ENGULFING_BEARISH")) b.push({ label: "ENGOLFO", cls: "bg-violet-500/20 text-violet-300 border border-violet-500/30" });
  if (factors.includes("STRUCTURE_BULLISH") || factors.includes("STRUCTURE_BEARISH")) b.push({ label: "ESTRUTURA OK", cls: "bg-orange-500/20 text-orange-300 border border-orange-500/30" });
  
  return b;
}

export default function AuditoriaTable({ rows, currentDateIso }: { rows: AuditRow[]; currentDateIso: string }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"trades" | "screener">("trades");
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");
  const [modeFilter, setModeFilter] = useState<ModeFilter>("all");
  const [periodFilter, setPeriodFilter] = useState<PeriodFilter>("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [symbolQuery, setSymbolQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("created_at");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [currentPage, setCurrentPage] = useState(1);

  const itemsPerPage = 10;

  const currentDate = new Date(currentDateIso);
  const now = currentDate.getTime();
  const filtered = rows.filter((row) => {
    // Se estivermos em modo "Trades", removemos os HOLDS e focamos no que teve intenção de trade
    if (viewMode === "trades" && row.side === "hold") return false;

    const outcome = getOutcome(row);
    const query = symbolQuery.trim().toLowerCase();

    if (query && !row.symbol.toLowerCase().includes(query)) return false;
    if (modeFilter !== "all" && row.mode !== modeFilter) return false;

    if (resultFilter === "win" && outcome?.result !== "win") return false;
    if (resultFilter === "loss" && outcome?.result !== "loss") return false;
    if (resultFilter === "breakeven" && outcome?.result !== "breakeven") return false;
    if (resultFilter === "pending" && outcome) return false;
    if (resultFilter === "alta_conv_loss") {
      if (outcome?.result !== "loss") return false;
      if (row.confidence == null || row.confidence < 0.65) return false;
    }

    if (periodFilter !== "all") {
      const createdAt = new Date(row.created_at).getTime();
      const diffDays = (now - createdAt) / (1000 * 60 * 60 * 24);
      if (periodFilter === "today") {
        const created = new Date(row.created_at);
        const today = currentDate;
        if (
          created.getDate() !== today.getDate() ||
          created.getMonth() !== today.getMonth() ||
          created.getFullYear() !== today.getFullYear()
        ) return false;
      }
      if (periodFilter === "7d" && diffDays > 7) return false;
      if (periodFilter === "30d" && diffDays > 30) return false;
    }

    if (startDate) {
      const start = new Date(startDate).getTime();
      const created = new Date(row.created_at).getTime();
      if (created < start) return false;
    }
    if (endDate) {
      const end = new Date(endDate).getTime();
      const created = new Date(row.created_at).getTime();
      // Adiciona um dia ao end date para cobrir o dia completo
      const endOfDay = end + (24 * 60 * 60 * 1000);
      if (created > endOfDay) return false;
    }

    return true;
  });

  const sorted = [...filtered].sort((left, right) => {
    if (sortField === "created_at") {
      const leftValue = new Date(left.created_at).getTime();
      const rightValue = new Date(right.created_at).getTime();
      return sortDirection === "desc" ? rightValue - leftValue : leftValue - rightValue;
    }

    if (sortField === "confidence") {
      const lc = left.confidence ?? -1;
      const rc = right.confidence ?? -1;
      return sortDirection === "desc" ? rc - lc : lc - rc;
    }

    const leftPnl = getSortablePnl(left);
    const rightPnl = getSortablePnl(right);

    if (leftPnl == null && rightPnl == null) return 0;
    if (leftPnl == null) return 1;
    if (rightPnl == null) return -1;

    return sortDirection === "desc" ? rightPnl - leftPnl : leftPnl - rightPnl;
  });

  const totalPages = Math.max(1, Math.ceil(sorted.length / itemsPerPage));
  const safePage = Math.min(currentPage, totalPages);
  const pageStart = (safePage - 1) * itemsPerPage;
  const paginatedRows = sorted.slice(pageStart, pageStart + itemsPerPage);

  const withOutcome = sorted.filter((row) => {
    const o = getOutcome(row);
    return o !== null && o.result !== "executing";
  });
  const wins = withOutcome.filter((row) => getOutcome(row)?.result === "win").length;
  const winRate = withOutcome.length > 0 ? (wins / withOutcome.length) * 100 : null;

  function exportCsv() {
    const headers = [
      "data_decisao",
      "ativo",
      "timeframe",
      "lado",
      "modo",
      "confianca",
      "risco_pct",
      "status_trade",
      "resultado",
      "pnl_money",
      "motivo_entrada",
      "motivo_saida",
      "pos_analise",
    ];

    const lines = sorted.map((row) => {
      const trade = getTrade(row);
      const outcome = getOutcome(row);
      return [
        csvEscape(row.created_at),
        csvEscape(row.symbol),
        csvEscape(row.timeframe),
        csvEscape(row.side),
        csvEscape(row.mode),
        csvEscape(row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : ""),
        csvEscape(row.risk_pct),
        csvEscape(trade?.status ?? ""),
        csvEscape(outcome?.result ?? ""),
        csvEscape(outcome?.pnl_money),
        csvEscape(row.rationale ?? ""),
        csvEscape(outcome?.win_loss_reason ?? ""),
        csvEscape(outcome?.post_analysis ?? ""),
      ].join(",");
    });

    const csv = [headers.join(","), ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `auditoria-vuno-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function exportXlsx() {
    const data = sorted.map((row) => {
      const trade = getTrade(row);
      const outcome = getOutcome(row);

      return {
        data_decisao: row.created_at,
        ativo: row.symbol,
        timeframe: row.timeframe,
        lado: row.side,
        modo: row.mode,
        confianca: row.confidence != null ? Number((row.confidence * 100).toFixed(1)) : null,
        risco_pct: row.risk_pct,
        status_trade: trade?.status ?? null,
        resultado: outcome?.result ?? null,
        pnl_money: outcome?.pnl_money ?? null,
        motivo_entrada: row.rationale ?? null,
        motivo_saida: outcome?.win_loss_reason ?? null,
        pos_analise: outcome?.post_analysis ?? null,
      };
    });

    const workbook = XLSX.utils.book_new();
    const worksheet = XLSX.utils.json_to_sheet(data);
    XLSX.utils.book_append_sheet(workbook, worksheet, "Auditoria");
    XLSX.writeFile(workbook, `auditoria-vuno-${new Date().toISOString().slice(0, 10)}.xlsx`);
  }

  const firstItem = sorted.length === 0 ? 0 : pageStart + 1;
  const lastItem = Math.min(pageStart + paginatedRows.length, sorted.length);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Auditoria</h1>
          <p className="text-sm text-slate-500">Trilha de decisões do motor Vuno</p>
        </div>
        
        <div className="flex bg-slate-900/50 p-1 rounded-xl border border-slate-800 self-start sm:self-center">
          <button
            onClick={() => setViewMode("trades")}
            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              viewMode === "trades" 
                ? "bg-sky-500 text-white shadow-lg shadow-sky-500/20" 
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Execuções Reais
          </button>
          <button
            onClick={() => setViewMode("screener")}
            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              viewMode === "screener" 
                ? "bg-slate-700 text-white" 
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Screener Full
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={exportCsv}
            className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20"
          >
            CSV
          </button>
          <button
            onClick={exportXlsx}
            className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300 transition-colors hover:bg-emerald-500/20"
          >
            Excel
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
          <p className="text-xs text-slate-500">Decisões</p>
          <p className="mt-1 text-xl font-bold text-slate-200">{filtered.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
          <p className="text-xs text-slate-500">Com resultado</p>
          <p className="mt-1 text-xl font-bold text-slate-200">{withOutcome.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
          <p className="text-xs text-slate-500">Win Rate</p>
          <p className="mt-1 text-xl font-bold text-slate-200">{winRate !== null ? `${winRate.toFixed(1)}%` : "—"}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
          <p className="text-xs text-slate-500">Última análise</p>
          <p className="mt-1 text-sm font-semibold text-slate-200">{sorted[0] ? fmtDt(sorted[0].created_at) : "—"}</p>
        </div>
      </div>

      <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4 lg:grid-cols-[minmax(0,1.2fr)_repeat(5,170px)]">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Buscar ativo</label>
          <input
            value={symbolQuery}
            onChange={(e) => {
              setSymbolQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="EURUSD, XAUUSD..."
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Resultado</label>
          <select
            value={resultFilter}
            onChange={(e) => {
              setResultFilter(e.target.value as ResultFilter);
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          >
            <option value="all">Todos</option>
            <option value="win">WIN</option>
            <option value="loss">LOSS</option>
            <option value="breakeven">Breakeven</option>
            <option value="pending">Sem resultado</option>
            <option value="alta_conv_loss">⚠ Alta convicção + Loss</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Modo</label>
          <select
            value={modeFilter}
            onChange={(e) => {
              setModeFilter(e.target.value as ModeFilter);
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          >
            <option value="all">Todos</option>
            <option value="observer">Observer</option>
            <option value="demo">Demo</option>
            <option value="real">Real</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Período</label>
          <select
            value={periodFilter}
            onChange={(e) => {
              setPeriodFilter(e.target.value as PeriodFilter);
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          >
            <option value="all">Tudo</option>
            <option value="today">Hoje</option>
            <option value="7d">7 dias</option>
            <option value="30d">30 dias</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Início</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setPeriodFilter("all");
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Fim</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setPeriodFilter("all");
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Ordenar por</label>
          <select
            value={sortField}
            onChange={(e) => {
              setSortField(e.target.value as SortField);
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          >
            <option value="created_at">Data</option>
            <option value="pnl_money">PnL</option>
            <option value="confidence">Convicção</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Direção</label>
          <select
            value={sortDirection}
            onChange={(e) => {
              setSortDirection(e.target.value as SortDirection);
              setCurrentPage(1);
            }}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none transition-colors focus:border-sky-500"
          >
            <option value="desc">Maior para menor</option>
            <option value="asc">Menor para maior</option>
          </select>
        </div>
      </div>

      {sorted.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/40 py-14 text-center">
          <p className="text-sm text-slate-400">Nada encontrado com esses filtros</p>
          <p className="mt-1 text-xs text-slate-600">Tente limpar a busca ou ampliar o período.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-400">
              Mostrando <span className="font-semibold text-slate-200">{firstItem}</span> a <span className="font-semibold text-slate-200">{lastItem}</span> de <span className="font-semibold text-slate-200">{sorted.length}</span> registros
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setCurrentPage(Math.max(1, safePage - 1))}
                disabled={safePage === 1}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Anterior
              </button>
              <span className="text-sm text-slate-400">
                Página <span className="font-semibold text-slate-200">{safePage}</span> de <span className="font-semibold text-slate-200">{totalPages}</span>
              </span>
              <button
                type="button"
                onClick={() => setCurrentPage(Math.min(totalPages, safePage + 1))}
                disabled={safePage === totalPages}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition-colors hover:border-slate-500 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Próxima
              </button>
            </div>
          </div>

          {paginatedRows.map((row) => {
            const trade = getTrade(row);
            const outcome = getOutcome(row);
            return (
              <div key={row.id} className={`rounded-xl border transition-all ${expanded === row.id ? "bg-slate-800/20 border-slate-700 shadow-inner" : "bg-slate-900 border-slate-800 hover:border-slate-700"}`}>
                <button
                  type="button"
                  onClick={() => setExpanded(expanded === row.id ? null : row.id)}
                  className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="text-base font-bold text-slate-100">{row.symbol}</span>
                      <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold tracking-tight uppercase ${sideBadge(row.side)}`}>
                        {row.side}
                      </span>
                      <span className="rounded-md bg-slate-800/80 px-2 py-0.5 text-[10px] font-medium text-slate-400 border border-slate-700/50">
                        {row.timeframe}
                      </span>
                      {(() => { 
                        const c = convictionBadge(row.confidence); 
                        return c ? <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${c.cls}`}>{c.label}</span> : null; 
                      })()}
                      
                      {outcome?.result === 'executing' ? (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-sky-500/10 border border-sky-500/30">
                          <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse" />
                          <span className="text-[10px] font-bold text-sky-300 uppercase">EM EXECUÇÃO</span>
                        </div>
                      ) : (
                        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase ${resultBadge(outcome?.result)}`}>
                          {outcome?.result || "PENDENTE"}
                        </span>
                      )}

                      {(() => {
                        const pnl = getOutcome(row)?.pnl_money;
                        if (pnl == null) return null;
                        return (
                          <span className={`text-[10px] font-bold ml-auto sm:ml-0 ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {pnl >= 0 ? "+" : ""}{pnl.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
                          </span>
                        );
                      })()}
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                      <span className="text-[11px] text-slate-500 whitespace-nowrap">
                        <span className="opacity-60">ID:</span> {row.id.slice(0, 8)} 
                      </span>
                      <span className="text-[11px] text-slate-500 whitespace-nowrap italic">
                        {fmtDt(row.created_at)}
                      </span>
                      {(() => {
                        const secs = row.duration_seconds ?? (() => {
                          const t = row.executed_trades?.[0];
                          if (t?.closed_at && t?.opened_at) {
                            const diff = new Date(t.closed_at).getTime() - new Date(t.opened_at).getTime();
                            return isNaN(diff) ? null : Math.floor(diff / 1000);
                          }
                          return null;
                        })();
                        if (!secs) return null;
                        return (
                          <span className="text-[11px] text-slate-500 whitespace-nowrap">
                            <span className="opacity-60">Dur:</span> {fmtDuration(secs)}
                          </span>
                        );
                      })()}
                      {viewMode === "screener" && (
                        <span className="text-[11px] text-slate-400 font-medium px-1.5 rounded bg-slate-800/50">
                          {row.mode}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {vpeBadges(row.rationale ?? "").slice(0, 1).map((b, i) => (
                      <span key={i} className={`hidden sm:inline-flex rounded px-2 py-0.5 text-[9px] font-black uppercase ${b.cls}`}>
                        {b.label}
                      </span>
                    ))}
                    <span className={`text-slate-500 transition-transform duration-200 ${expanded === row.id ? "rotate-180" : ""}`}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
                    </span>
                  </div>
                </button>

                {expanded === row.id && (
                  <div className="border-t border-slate-800 px-4 py-4">
                      <div className="space-y-1 text-slate-400">
                        <p><span className="text-slate-500">Preço Entrada:</span> {row.entry_price ? row.entry_price.toFixed(5) : "—"}</p>
                        <p><span className="text-slate-500">Stop Loss:</span> <span className="text-rose-400">{row.stop_loss ? row.stop_loss.toFixed(5) : "—"}</span></p>
                        <p><span className="text-slate-500">Take Profit:</span> <span className="text-emerald-400">{row.take_profit ? row.take_profit.toFixed(5) : "—"}</span></p>
                        <p><span className="text-slate-500">Confiança:</span> {row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : "—"}</p>
                      </div>

                      <div className="space-y-1 text-slate-400">
                        <p><span className="text-slate-500">Resultado:</span> {outcome?.result?.toUpperCase() ?? "PENDENTE"}</p>
                        <p>
                          <span className="text-slate-500">PnL Real:</span>{" "}
                          {(() => {
                            const pnl = getOutcome(row)?.pnl_money;
                            if (pnl == null) return "—";
                            return `${pnl >= 0 ? "+" : ""}R$ ${pnl.toFixed(2)}`;
                          })()}
                        </p>
                        <p><span className="text-slate-500">Status MT5:</span> {trade?.status ?? "Análise"}</p>
                        <p className="leading-relaxed"><span className="text-slate-500">Obs:</span> {outcome?.win_loss_reason ?? "Aguardando desfecho..."}</p>
                      </div>

                      <div className="space-y-3 text-slate-400">
                        <div>
                          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Explicação do sinal</p>
                          <p className="mt-1 leading-relaxed text-slate-300">
                            {row.rationale ? stripTechSuffix(row.rationale) : "Sem motivo registrado."}
                          </p>
                        </div>
                        
                        {(outcome?.post_analysis || row.post_analysis) && (
                          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                            <p className="text-[10px] font-bold text-amber-500 uppercase tracking-widest">LIÇÃO APRENDIDA (IA)</p>
                            <p className="mt-1 text-xs leading-relaxed text-amber-200/90">
                              {outcome?.post_analysis || row.post_analysis}
                            </p>
                          </div>
                        )}
                      </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
