"use client";

import { useState } from "react";

type Props = {
  disabled: boolean;
  sampleCount: number;
};

type ActionResult = {
  ok: boolean;
  message?: string;
  output?: string;
  error?: string;
  detail?: string;
};

export default function AdminGlobalMemoryButton({ disabled, sampleCount }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<ActionResult | null>(null);

  async function handleRebuild() {
    if (disabled || state === "loading") return;

    const confirmed = window.confirm(
      `Confirma reconstruir a memória global com base em ${sampleCount} eventos anonimizados?\n\n` +
        "Esta ação é exclusiva de admin e pode demorar alguns minutos."
    );
    if (!confirmed) return;

    setState("loading");
    setResult(null);

    try {
      const res = await fetch("/api/admin/global-memory/rebuild", { method: "POST" });
      const data: ActionResult = await res.json();
      setResult(data);
      setState(data.ok ? "done" : "error");
    } catch {
      setResult({ ok: false, error: "Erro de rede ao chamar a API." });
      setState("error");
    }
  }

  return (
    <div className="flex flex-col items-end gap-3">
      <button
        onClick={handleRebuild}
        disabled={disabled || state === "loading"}
        className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition ${
          disabled
            ? "cursor-not-allowed border border-dashed border-slate-700 bg-slate-900 text-slate-600"
            : state === "loading"
            ? "cursor-wait border border-slate-700 bg-slate-800 text-slate-400"
            : "border border-cyan-600/50 bg-cyan-600/20 text-cyan-300 hover:bg-cyan-600/30"
        }`}
      >
        {state === "loading" ? (
          <>
            <span className="animate-spin">⟳</span>
            Reconstruindo...
          </>
        ) : (
          <>
            <span>🧠</span>
            Rebuild Memória Global
          </>
        )}
      </button>

      {result && (
        <div
          className={`w-full max-w-md rounded-xl border px-4 py-3 text-xs ${
            result.ok
              ? "border-green-800/40 bg-green-950/30 text-green-300"
              : "border-red-800/40 bg-red-950/30 text-red-300"
          }`}
        >
          <p className="font-semibold">{result.ok ? `✅ ${result.message}` : `❌ ${result.error}`}</p>
          {result.detail && <p className="mt-1 text-slate-500">{result.detail}</p>}
          {result.output && (
            <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap text-slate-400">
              {result.output}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
