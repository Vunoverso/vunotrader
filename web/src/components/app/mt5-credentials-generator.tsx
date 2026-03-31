"use client";

import { useState } from "react";

type ApiResponse = {
  ok: boolean;
  error?: string;
  warning?: string;
  robot_id?: string;
  robot_token?: string;
  user_id?: string;
  organization_id?: string;
  instance_name?: string;
  allowed_modes?: string[];
  real_trading_enabled?: boolean;
};

function CopyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
      <p className="text-[11px] uppercase tracking-wider text-slate-500">{label}</p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="truncate font-mono text-xs text-slate-200">{value}</p>
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(value)}
          className="rounded-md border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
        >
          Copiar
        </button>
      </div>
    </div>
  );
}

export default function Mt5CredentialsGenerator() {
  const [mode, setMode] = useState<"demo" | "real">("demo");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ApiResponse | null>(null);

  async function handleGenerate() {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/mt5/robot-credentials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      const data = (await res.json()) as ApiResponse;
      setResult(data);
    } catch {
      setResult({ ok: false, error: "Falha de rede ao gerar credenciais." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-sky-500/20 bg-sky-500/5 p-6 space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-sky-300">Gerar credenciais do robô</h2>
        <p className="mt-2 text-sm text-slate-300">
          Gere RobotID e RobotToken para conectar seu EA no MT5. A decisão final de ativar em demo ou real é sua.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setMode("demo")}
          className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
            mode === "demo"
              ? "border-sky-500/40 bg-sky-500/20 text-sky-300"
              : "border-slate-700 bg-slate-900 text-slate-400"
          }`}
        >
          Demo
        </button>
        <button
          type="button"
          onClick={() => setMode("real")}
          className={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
            mode === "real"
              ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
              : "border-slate-700 bg-slate-900 text-slate-400"
          }`}
        >
          Real
        </button>

        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading}
          className="ml-auto rounded-lg border border-sky-500/30 bg-sky-500/20 px-4 py-2 text-sm font-semibold text-sky-200 hover:bg-sky-500/30 disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? "Gerando..." : "Gerar RobotID + Token"}
        </button>
      </div>

      {result && !result.ok && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {result.error ?? "Falha ao gerar credenciais."}
        </div>
      )}

      {result?.ok && result.robot_id && result.robot_token && result.user_id && result.organization_id && (
        <div className="space-y-3">
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">
            {result.warning ?? "Salve o token agora. Ele não será exibido novamente."}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <CopyField label="UserID" value={result.user_id} />
            <CopyField label="OrganizationID" value={result.organization_id} />
            <CopyField label="RobotID" value={result.robot_id} />
            <CopyField label="RobotToken" value={result.robot_token} />
          </div>

          <p className="text-xs text-slate-400">
            Instância criada: {result.instance_name} · Modos: {(result.allowed_modes ?? []).join(", ") || "demo"}
          </p>
        </div>
      )}
    </section>
  );
}
