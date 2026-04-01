"use client";

import { useEffect, useState, useRef } from "react";

type TradeDecision = {
  id: string;
  symbol: string;
  timeframe: string;
  side: string;
  confidence: number;
  risk_pct: number;
  mode: string;
  rationale: string;
  created_at: string;
};

export function TerminalFeed({
  userId,
  robotId,
  initialLogs,
}: {
  userId: string;
  robotId?: string;
  initialLogs?: TradeDecision[];
}) {
  const [logs, setLogs] = useState<TradeDecision[]>(initialLogs ?? []);
  const [activeAssets, setActiveAssets] = useState<string[]>(
    Array.from(new Set((initialLogs ?? []).map((d) => d.symbol)))
  );
  const [time, setTime] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Tick clock
  useEffect(() => {
    setTime(new Date().toLocaleTimeString("pt-BR", { hour12: false }));
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString("pt-BR", { hour12: false }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll via API route a cada 10s (sem precisar de auth client-side)
  useEffect(() => {
    async function fetchLogs() {
      if (!userId) return;
      try {
        const params = new URLSearchParams({ userId });
        if (robotId) params.set("robotId", robotId);
        const res = await fetch(`/api/terminal-feed?${params.toString()}`);
        if (!res.ok) return;
        const data: TradeDecision[] = await res.json();
        if (data.length > 0) {
          const sorted = [...data].sort(
            (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          );
          setLogs(sorted);
          setActiveAssets(Array.from(new Set(sorted.map((d) => d.symbol))));
        }
      } catch {
        // silencioso — mantém dados locais
      }
    }

    fetchLogs();
    const interval = setInterval(fetchLogs, 10_000);
    return () => clearInterval(interval);
  }, [userId, robotId]);

  // Scroll para o fim quando chegar novos logs
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) {
    return (
      <div className="w-full bg-[#0a0a0c] border border-cyan-800/30 rounded-lg p-4 font-mono text-xs text-cyan-500/50 flex items-center gap-2">
        <span className="animate-pulse text-cyan-400">█</span>
        <span>&gt; Inicializando terminal de rastreio VunoScreener...</span>
        <span className="animate-pulse text-cyan-800 ml-1">aguardando 1º ciclo do motor</span>
      </div>
    );
  }

  const lastLog = logs[logs.length - 1];

  return (
    <div className="w-full bg-[#050505] border border-cyan-900/40 rounded-lg overflow-hidden flex flex-col font-mono text-xs text-slate-300 relative shadow-[0_0_20px_rgba(8,145,178,0.05)]">
      {/* HEADER */}
      <div className="border-b border-cyan-900/50 bg-[#0a0a0c] p-3 space-y-1">
        <div className="flex justify-between items-center text-cyan-400">
          <div>
            <span className="text-cyan-600">█ </span>
            <span className="font-bold">VUNO/SCREENER</span>
            <span className="text-cyan-700 ml-2">| STATUS: ATIVO</span>
          </div>
          <div className="text-cyan-600 tabular-nums">
            HORA: <span className="text-cyan-300">{time || "––:––:––"}</span>
          </div>
        </div>
        <div className="flex items-center justify-between text-cyan-700">
          <div>
            MODO:{" "}
            <span className="text-cyan-400">
              {lastLog?.mode === "observer" ? "SIMULAÇÃO/APREND." : lastLog?.mode?.toUpperCase() ?? "–"}
            </span>
          </div>
          <div className="flex gap-2 items-center flex-wrap">
            <span>ATIVOS RASTREADOS:</span>
            {activeAssets.map((sym) => (
              <span
                key={sym}
                className="border border-cyan-800/60 bg-cyan-950/40 text-cyan-300 px-1.5 py-0.5 rounded text-[10px]"
              >
                {sym}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* FEED */}
      <div className="h-64 overflow-y-auto p-3 space-y-1 scroller">
        {logs.map((log) => {
          const isBuy = log.side.toLowerCase() === "buy";
          const isSell = log.side.toLowerCase() === "sell";
          const timeStr = new Date(log.created_at).toLocaleTimeString("pt-BR", { hour12: false });
          const confStr = log.confidence ? Math.round(log.confidence * 100) + "%" : "---";
          const sigColor = isBuy
            ? "text-emerald-400 font-bold"
            : isSell
            ? "text-red-400 font-bold"
            : "text-cyan-600";
          const sigLabel = isBuy ? "▲ BUY " : isSell ? "▼ SELL" : "– HOLD";

          return (
            <div key={log.id} className="flex flex-col border-l border-cyan-900/40 pl-2">
              <div className="flex items-center gap-2">
                <span className="text-cyan-800 shrink-0 tabular-nums">[{timeStr}]</span>
                <span className="text-cyan-200 w-16 shrink-0">{log.symbol}</span>
                <span className={`w-14 shrink-0 ${sigColor}`}>{sigLabel}</span>
                <span className="text-cyan-800">|</span>
                <span className="text-slate-500">
                  cnf:<span className="text-slate-400">{confStr}</span>
                </span>
              </div>
              {log.rationale && (
                <div className="text-[10px] text-cyan-700/70 ml-[170px] leading-tight line-clamp-1">
                  {log.rationale}
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} className="flex items-center gap-1 pt-1">
          <span className="animate-pulse text-cyan-500 text-sm">_</span>
          <span className="text-cyan-800 text-[10px]">aguardando próximo ciclo...</span>
        </div>
      </div>

      <style jsx>{`
        .scroller::-webkit-scrollbar { width: 4px; }
        .scroller::-webkit-scrollbar-track { background: #050505; }
        .scroller::-webkit-scrollbar-thumb { background: #086682; border-radius: 4px; }
      `}</style>
    </div>
  );
}
