"use client";

import { useEffect, useState } from "react";
import { PremiumMetricCard } from "@/components/app/premium-metric-card";

type LiveVisual = {
  cycle_id: string;
  visual_shadow_status: string;
  visual_alignment: string;
  visual_conflict_reason: string | null;
  summary: string | null;
  signal_bias: string | null;
  chart_image_url: string | null;
};

type LiveTrade = {
  id: string;
  symbol: string;
  side: string;
  entry_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  created_at: string;
  confidence: number;
  timeframe: string;
  robot_instance_id: string;
  robot_instances?: {
    name: string;
  };
  visual: LiveVisual | null;
};

type LiveTradesApiResponse = {
  ok: boolean;
  error?: string;
  trades?: LiveTrade[];
};

function visualBadge(visual: LiveVisual | null) {
  if (!visual) {
    return { label: "Sem shadow", cls: "border-slate-700 bg-slate-900 text-slate-500" };
  }

  if (visual.visual_shadow_status === "skipped_non_chart_symbol") {
    return { label: "Fora do grafico", cls: "border-slate-700 bg-slate-900 text-slate-300" };
  }

  if (visual.visual_alignment === "aligned") {
    return { label: "Shadow alinhado", cls: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" };
  }

  if (visual.visual_alignment === "divergent_high") {
    return { label: "Divergencia alta", cls: "border-rose-500/30 bg-rose-500/10 text-rose-300" };
  }

  if (visual.visual_alignment === "divergent_low") {
    return { label: "Divergencia baixa", cls: "border-amber-500/30 bg-amber-500/10 text-amber-300" };
  }

  if (visual.visual_shadow_status === "error") {
    return { label: "Shadow com erro", cls: "border-rose-500/30 bg-rose-500/10 text-rose-300" };
  }

  return { label: "Shadow pendente", cls: "border-sky-500/30 bg-sky-500/10 text-sky-300" };
}

export default function AoVivoPage() {
  const [trades, setTrades] = useState<LiveTrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [mounted, setMounted] = useState(false);

  async function fetchLiveTrades() {
    try {
      const response = await fetch("/api/mt5/live-trades", { cache: "no-store" });
      const data = (await response.json()) as LiveTradesApiResponse;
      if (response.ok && data.ok) {
        setTrades(data.trades ?? []);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setMounted(true);
    fetchLiveTrades();
    const interval = setInterval(fetchLiveTrades, 5000); // 5s refresh
    const clock = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => {
        clearInterval(interval);
        clearInterval(clock);
    };
  }, []);

  const totalPositions = trades.length;
  const shadowCount = trades.filter((trade) => trade.visual !== null).length;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white sm:text-3xl flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex h-3 w-3 rounded-full bg-rose-500"></span>
            </span>
            Monitoramento Ao Vivo
          </h1>
          <p className="text-sm font-medium text-slate-500 mt-1 uppercase tracking-widest flex items-center gap-2">
            Operações em Atuação no Mercado · 
            {mounted ? (
              <span className="text-slate-400 tabular-nums">{currentTime.toLocaleTimeString()}</span>
            ) : (
                <span className="text-slate-400 tabular-nums">--:--:--</span>
            )}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <PremiumMetricCard 
          label="Posições Abertas"
          value={totalPositions}
          subtitle="Controle de Risco Ativo"
          accent={totalPositions > 0 ? "sky" : "slate"}
        />
        <PremiumMetricCard 
          label="Exposição Global"
          value={totalPositions > 0 ? `${(totalPositions * 0.5).toFixed(1)}%` : "0.0%"}
          subtitle="Margem Estimada"
          accent="slate"
        />
        <PremiumMetricCard 
          label="Shadow Visual"
          value={`${shadowCount}/${totalPositions}`}
          subtitle="Ciclos com screenshot"
          accent={shadowCount > 0 ? "sky" : "slate"}
        />
      </div>

      <div className="glass-card rounded-2xl overflow-hidden min-h-[400px]">
        <div className="px-6 py-4 border-b border-white/5 bg-white/5 flex items-center justify-between">
            <h2 className="text-xs font-black uppercase tracking-widest text-slate-400">Monitor de Execução</h2>
            <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-slate-500 italic">Atualiza a cada 5s</span>
                <button onClick={fetchLiveTrades} className="p-1 hover:text-sky-400 transition-colors">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"/></svg>
                </button>
            </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500"></div>
          </div>
        ) : trades.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-slate-500 border-b border-white/5">
                  <th className="px-6 py-4">Início</th>
                  <th className="px-6 py-4">Ativo</th>
                  <th className="px-6 py-4">Tipo</th>
                  <th className="px-6 py-4">Shadow</th>
                  <th className="px-6 py-4">Screenshot</th>
                  <th className="px-6 py-4 text-right">Entrada</th>
                  <th className="px-6 py-4 text-right">SL / TP</th>
                  <th className="px-6 py-4 text-right">Duração</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {trades.map((trade) => {
                  const duration = Math.floor((new Date().getTime() - new Date(trade.created_at).getTime()) / 1000);
                  const mins = Math.floor(duration / 60);
                  const secs = duration % 60;
                  const badge = visualBadge(trade.visual);
                  
                  return (
                    <tr key={trade.id} className="hover:bg-white/5 transition-colors group">
                      <td className="px-6 py-4 tabular-nums text-slate-400">
                        {new Date(trade.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-white font-black">{trade.symbol}</span>
                        <p className="text-[9px] text-slate-500">
                          {trade.timeframe}
                          {trade.robot_instances?.name ? ` · ${trade.robot_instances.name}` : ""}
                        </p>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-widest ${
                          trade.side === "buy" ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"
                        }`}>
                          {trade.side}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-bold uppercase tracking-widest ${badge.cls}`}>
                          {badge.label}
                        </div>
                        {trade.visual?.summary && (
                          <p className="mt-1 max-w-[180px] text-[10px] leading-relaxed text-slate-500">
                            {trade.visual.summary}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {trade.visual?.chart_image_url ? (
                          <a href={trade.visual.chart_image_url} target="_blank" rel="noreferrer" className="block w-28 overflow-hidden rounded-lg border border-slate-700 bg-slate-900/80">
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={trade.visual.chart_image_url} alt={`Screenshot ${trade.symbol}`} className="h-16 w-full object-cover" />
                          </a>
                        ) : (
                          <div className="flex h-16 w-28 items-center justify-center rounded-lg border border-dashed border-slate-700 bg-slate-950/50 text-[10px] uppercase tracking-widest text-slate-500">
                            Sem imagem
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right text-slate-300 font-bold tabular-nums">
                        {trade.entry_price.toFixed(5)}
                      </td>
                      <td className="px-6 py-4 text-right tabular-nums">
                        <div className="text-[10px] text-rose-400 font-bold">SL: {trade.stop_loss?.toFixed(5) || "Mkt"}</div>
                        <div className="text-[10px] text-emerald-400 font-bold">TP: {trade.take_profit?.toFixed(5) || "Mkt"}</div>
                      </td>
                      <td className="px-6 py-4 text-right text-sky-400 font-bold tabular-nums">
                        {mins}m {secs}s
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-24 text-center">
             <div className="mb-4 text-slate-800">
                <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1"/></svg>
             </div>
             <h3 className="text-white font-black text-lg">Nenhuma Operação Ativa</h3>
             <p className="text-slate-500 text-sm max-w-xs mt-2">O motor está monitorando o mercado. Novos sinais aparecerão aqui assim que forem executados.</p>
          </div>
        )}
      </div>
    </div>
  );
}
