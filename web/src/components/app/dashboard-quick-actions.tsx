"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type RobotInstance = {
  id: string;
  name: string;
  status: "active" | "paused" | "revoked";
  last_seen_at: string | null;
};

export function DashboardQuickActions() {
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [instance, setInstance] = useState<RobotInstance | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await fetch("/api/mt5/robot-credentials/instances");
      const data = await res.json();
      if (res.ok && data.ok && data.instances?.length > 0) {
        // Pega a instância mais recente (ou a primeira válida)
        const sorted = data.instances.sort((a: any, b: any) => 
          new Date(b.last_seen_at || 0).getTime() - new Date(a.last_seen_at || 0).getTime()
        );
        setInstance(sorted[0]);
      }
    } catch (err) {
      console.error("Erro ao carregar instâncias no dash:", err);
    } finally {
      setLoading(false);
    }
  }

  async function toggleStatus() {
    if (!instance || busy) return;
    setBusy(true);
    const action = instance.status === "active" ? "pause" : "activate";
    try {
      const res = await fetch("/api/mt5/robot-credentials/instances", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ robot_id: instance.id, action }),
      });
      const data = await res.json();
      if (res.ok && data.ok && data.instance) {
        setInstance(data.instance);
      }
    } catch (err) {
      setError("Falha ao alternar status.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (loading) return (
    <div className="h-10 w-32 animate-pulse rounded-lg bg-slate-800/50" />
  );

  if (!instance) return (
    <Link
      href="/app/instalacao"
      className="flex items-center gap-2 rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-xs font-bold text-sky-300 transition-all hover:bg-sky-500/20"
    >
      <span>🤖</span>
      CONFIGURAR ROBÔ
    </Link>
  );

  const isActive = instance.status === "active";

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={toggleStatus}
        disabled={busy}
        className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-xs font-black transition-all ${
          isActive 
            ? "border-amber-500/30 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20" 
            : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
        } disabled:opacity-50`}
      >
        <span className={`h-2 w-2 rounded-full ${isActive ? "bg-amber-400" : "bg-emerald-400 animate-pulse"}`} />
        {busy ? "PROCESSANDO..." : isActive ? "PAUSAR ROBÔ" : "ATIVAR ROBÔ"}
      </button>
      
      {error && <span className="text-[10px] text-red-400 uppercase font-bold">{error}</span>}
    </div>
  );
}
