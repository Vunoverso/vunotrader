"use client";

import { useEffect, useState, useRef } from "react";
import { createClient } from "@/lib/supabase/client";

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
}: {
  userId: string;
  robotId?: string;
}) {
  const [logs, setLogs] = useState<TradeDecision[]>([]);
  const [activeAssets, setActiveAssets] = useState<string[]>([]);
  const [time, setTime] = useState<string>("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const supabase = createClient();

  // Tick clock
  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString("pt-BR", { hour12: false }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Poll for logs
  useEffect(() => {
    async function fetchLogs() {
      if (!userId) return;
      let query = supabase
        .from("trade_decisions")
        .select("id, symbol, timeframe, side, confidence, risk_pct, mode, rationale, created_at")
        .eq("user_id", userId)
        .order("created_at", { ascending: false })
        .limit(20);

      if (robotId) {
        query = query.eq("robot_instance_id", robotId);
      }

      const { data } = await query;
      if (data) {
        setLogs(data.reverse()); // Reverse to show oldest first in a top-down scroll, or keep DESC if we render bottom-up
        
        // Extract active assets from last 20 signals
        const assets = new Set(data.map((d: TradeDecision) => d.symbol));
        setActiveAssets(Array.from(assets));
      }
    }

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000); // Poll a cada 5 segundos

    return () => clearInterval(interval);
  }, [userId, robotId]);

  // Handle scrollToBottom if needed
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) {
    return (
      <div className="w-full bg-[#0a0a0c] border border-cyan-800/30 rounded-lg p-4 font-mono text-cyan-500/50 text-xs">
        &gt; Inicializando terminal de rastreio VunoScreener...
      </div>
    );
  }

  // Pegar último log para dados do cabeçalho
  const lastLog = logs[logs.length - 1];

  return (
    <div className="w-full bg-[#050505] border border-cyan-900/40 rounded-lg overflow-hidden flex flex-col font-mono text-xs text-slate-300 relative shadow-[0_0_20px_rgba(8,145,178,0.05)]">
      {/* HEADER HACKER */}
      <div className="border-b border-cyan-900/50 bg-[#0a0a0c] p-3">
        <div className="flex justify-between items-center text-cyan-400">
          <div>
            <span className="font-bold">STATUS:</span> RODANDO DUAL/MULTI-ATIVO
          </div>
          <div>
            <span className="font-bold">CICLO HORA:</span> {time}
          </div>
        </div>
        <div className="mt-1 flex items-center justify-between text-cyan-600/80">
          <div>
            <span className="font-bold">MODO DO CÉREBRO:</span> {lastLog?.mode === "observer" ? "SIMULAÇÃO/APRENDIZADO" : lastLog?.mode.toUpperCase()}
          </div>
          <div className="flex gap-2">
            <span className="font-bold">ATIVOS:</span>
            {activeAssets.map(sym => (
              <span key={sym} className="text-cyan-300">[{sym}]</span>
            ))}
          </div>
        </div>
      </div>

      {/* TERMINAL FEED AREA */}
      <div className="h-64 overflow-y-auto p-4 space-y-2 scroller flex flex-col">
        {logs.map((log) => {
          const isBuy = log.side.toLowerCase() === "buy";
          const isSell = log.side.toLowerCase() === "sell";
          const isHold = log.side.toLowerCase() === "hold";
          const timeStr = new Date(log.created_at).toLocaleTimeString("pt-BR", { hour12: false });
          const confStr = log.confidence ? Math.round(log.confidence * 100) + "%" : "---";
          
          let color = "text-slate-400";
          if (isBuy) color = "text-emerald-400 font-bold";
          if (isSell) color = "text-red-400 font-bold";
          if (isHold) color = "text-cyan-500/60";

          return (
            <div key={log.id} className="flex flex-col border-l-2 pl-2 border-cyan-900/30">
              <div className="flex items-center gap-2">
                <span className="text-cyan-700">[{timeStr}]</span>
                <span className="text-cyan-300 w-16">{log.symbol}</span>
                <span className={`w-12 ${color}`}>{log.side.toUpperCase()}</span>
                <span className="text-cyan-800">|</span>
                <span className="text-slate-500 w-16">cnf:{confStr}</span>
              </div>
              {log.rationale && (
                <div className="text-[10px] text-cyan-600/70 ml-[100px] mt-0.5 line-clamp-2 leading-tight">
                  {log.rationale}
                </div>
              )}
            </div>
          );
        })}
        <div ref={bottomRef} className="h-1 pb-2">
           <span className="animate-pulse text-cyan-500">_</span>
        </div>
      </div>

      <style jsx>{`
        .scroller::-webkit-scrollbar {
          width: 5px;
        }
        .scroller::-webkit-scrollbar-track {
          background: #050505;
        }
        .scroller::-webkit-scrollbar-thumb {
          background: #086682;
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
}
