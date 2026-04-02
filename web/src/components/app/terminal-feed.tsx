"use client";

import { useEffect, useState, useRef } from "react";

const BRAZIL_TIME_ZONE = "America/Sao_Paulo";
const TIME_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
  timeZone: BRAZIL_TIME_ZONE,
});

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
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);

  // Tick clock
  useEffect(() => {
    setTime(TIME_FORMATTER.format(new Date()));
    const timer = setInterval(() => {
      setTime(TIME_FORMATTER.format(new Date()));
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

  // Monitora se o usuário subiu o scroll manualmente
  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;
    
    // Se o usuário estiver a mais de 50px do fundo, desativamos o auto-scroll temporariamente
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
    if (isAutoScrollEnabled !== isAtBottom) {
      setIsAutoScrollEnabled(isAtBottom);
    }
  };

  // Scroll suave apenas no container interno quando chegar novos logs
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container && isAutoScrollEnabled) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [logs, isAutoScrollEnabled]);

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
    <div className="w-full glass-card border-sky-900/40 rounded-2xl overflow-hidden flex flex-col font-mono text-xs text-slate-300 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-sky-500/5 to-transparent pointer-events-none" />
      {/* HEADER */}
      <div className="border-b border-cyan-900/50 bg-[#0a0a0c] p-3 space-y-1">
        <div className="flex justify-between items-center text-sky-400">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-sky-500 animate-pulse" />
            <span className="font-black uppercase tracking-widest text-[10px]">VUNO/SCREENER</span>
            <span className="text-sky-700 font-bold ml-2 text-[9px] border border-sky-900/50 px-1.5 rounded">STATUS: ATIVO</span>
          </div>
          <div className="text-sky-600 tabular-nums font-bold text-[10px]">
            SYSTEM_TIME: <span className="text-sky-300">{time || "––:––:––"}</span>
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
      <div 
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="h-64 overflow-y-auto p-4 space-y-1 terminal-scrollbar relative z-10"
      >
        {logs.map((log) => {
          const isBuy = log.side.toLowerCase() === "buy";
          const isSell = log.side.toLowerCase() === "sell";
          const timeStr = TIME_FORMATTER.format(new Date(log.created_at));
          const confStr = log.confidence ? Math.round(log.confidence * 100) + "%" : "---";
          const sigColor = isBuy
            ? "text-emerald-400 font-black"
            : isSell
            ? "text-rose-400 font-black"
            : "text-sky-800";
          const sigLabel = isBuy ? "▲ BUY " : isSell ? "▼ SELL" : "– HOLD";

          return (
            <div key={log.id} className="flex flex-col border-l border-sky-900/30 pl-3 py-0.5 hover:bg-white/5 transition-colors">
              <div className="flex items-center gap-3">
                <span className="text-sky-800 shrink-0 tabular-nums text-[10px]">[{timeStr}]</span>
                <span className="text-sky-100 w-20 shrink-0 font-bold tracking-wider">{log.symbol}</span>
                <span className={`w-16 shrink-0 text-[10px] tracking-widest ${sigColor}`}>{sigLabel}</span>
                <span className="text-slate-600 text-[10px]">
                  CONF:<span className="text-slate-400 ml-1">{confStr}</span>
                </span>
              </div>
              {log.rationale && (
                <div className="text-[9px] text-sky-700/60 ml-[185px] leading-tight line-clamp-1 italic">
                  {log.rationale}
                </div>
              )}
            </div>
          );
        })}
        <div className="flex items-center gap-2 pt-2 border-t border-white/5">
          <span className="animate-pulse text-sky-500 font-black text-sm">_</span>
          <span className="text-sky-900 text-[9px] font-bold uppercase tracking-widest">Listening for next signal cycle...</span>
        </div>
      </div>
    </div>
  );
}
