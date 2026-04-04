"use client";

import { useEffect, useMemo, useState } from "react";

type RobotInstance = {
  id: string;
  name: string;
  status: "active" | "paused" | "revoked";
  allowed_modes: string[] | null;
  real_trading_enabled: boolean;
  last_seen_at: string | null;
  created_at: string;
  robot_product_type: "robo_integrado" | "robo_hibrido_visual" | "python_laboratorio";
  visual_shadow_enabled: boolean;
  computer_use_enabled: boolean;
  human_approval_required: boolean;
};

type ApiResponse = {
  ok: boolean;
  error?: string;
  instances?: RobotInstance[];
  instance?: RobotInstance;
};

function badgeClass(status: RobotInstance["status"]) {
  if (status === "active") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
  if (status === "paused") return "border-amber-500/30 bg-amber-500/10 text-amber-300";
  return "border-red-500/30 bg-red-500/10 text-red-300";
}

function heartbeatLabel(lastSeen: string | null) {
  if (!lastSeen) return "Sem heartbeat";
  const diffMs = Date.now() - new Date(lastSeen).getTime();
  const min = Math.floor(diffMs / 60000);
  if (min < 1) return "Heartbeat agora";
  if (min < 60) return `há ${min} min`;
  const h = Math.floor(min / 60);
  return `há ${h}h`;
}

function productTypeLabel(productType: RobotInstance["robot_product_type"]) {
  if (productType === "robo_hibrido_visual") return "Robo Hibrido Visual";
  if (productType === "python_laboratorio") return "Laboratorio Python";
  return "Robo Integrado";
}

export default function Mt5RobotInstancesPanel() {
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [items, setItems] = useState<RobotInstance[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/mt5/robot-credentials/instances", { method: "GET" });
      const data = (await res.json()) as ApiResponse;
      if (!res.ok || !data.ok) {
        setError(data.error ?? "Falha ao carregar instâncias.");
      } else {
        setItems(data.instances ?? []);
      }
    } catch {
      setError("Erro de rede ao carregar instâncias.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();

    function handlePackageCreated() {
      void load();
    }

    window.addEventListener("vuno:robot-package-created", handlePackageCreated);
    return () => window.removeEventListener("vuno:robot-package-created", handlePackageCreated);
  }, []);

  async function changeStatus(robotId: string, action: "pause" | "revoke" | "activate") {
    setBusyId(robotId);
    setError(null);
    try {
      const res = await fetch("/api/mt5/robot-credentials/instances", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ robot_id: robotId, action }),
      });
      const data = (await res.json()) as ApiResponse;
      if (!res.ok || !data.ok || !data.instance) {
        setError(data.error ?? "Falha ao atualizar instância.");
      } else {
        setItems((prev) => prev.map((item) => (item.id === robotId ? data.instance! : item)));
      }
    } catch {
      setError("Erro de rede ao atualizar instância.");
    } finally {
      setBusyId(null);
    }
  }

  const activeCount = useMemo(() => items.filter((item) => item.status === "active").length, [items]);

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Minhas instâncias</h2>
          <p className="mt-1 text-xs text-slate-500">
            Gerencie instâncias do robô para este usuário. Ativas: {activeCount}
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          Atualizar
        </button>
      </div>

      {loading ? (
        <div className="rounded-lg border border-slate-800 bg-slate-950/40 px-4 py-5 text-sm text-slate-400">Carregando instâncias...</div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-950/40 px-4 py-5 text-sm text-slate-500">
          Nenhuma instância criada ainda.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-100">{item.name}</p>
                    <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${badgeClass(item.status)}`}>
                      {item.status.toUpperCase()}
                    </span>
                    {item.real_trading_enabled && (
                      <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-300">
                        REAL habilitado
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.id} · modos: {(item.allowed_modes ?? []).join(", ") || "demo"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {productTypeLabel(item.robot_product_type)}
                    {item.visual_shadow_enabled ? " · shadow visual ativo" : ""}
                    {item.computer_use_enabled ? " · computer use assistido" : ""}
                    {item.human_approval_required ? " · aprovacao humana" : ""}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Último heartbeat: {heartbeatLabel(item.last_seen_at)}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {item.status !== "active" && (
                    <button
                      type="button"
                      onClick={() => changeStatus(item.id, "activate")}
                      disabled={busyId === item.id}
                      className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
                    >
                      Reativar
                    </button>
                  )}
                  {item.status === "active" && (
                    <button
                      type="button"
                      onClick={() => changeStatus(item.id, "pause")}
                      disabled={busyId === item.id}
                      className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 disabled:opacity-50"
                    >
                      Pausar
                    </button>
                  )}
                  {item.status !== "revoked" && (
                    <button
                      type="button"
                      onClick={() => changeStatus(item.id, "revoke")}
                      disabled={busyId === item.id}
                      className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-500/20 disabled:opacity-50"
                    >
                      Revogar
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="text-xs text-red-300">{error}</p>}
    </section>
  );
}
