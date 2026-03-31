"use client";

/**
 * Botão "Retreinar agora" — Client Component.
 * Dispara POST /api/admin/retrain e exibe o resultado inline.
 */

import { useState } from "react";

type Props = {
  disabled: boolean;
  sampleCount: number;
};

type RetrainResult = {
  ok: boolean;
  message?: string;
  output?: string;
  error?: string;
  detail?: string;
};

export default function RetrainButton({ disabled, sampleCount }: Props) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<RetrainResult | null>(null);

  async function handleRetrain() {
    if (disabled || state === "loading") return;

    const confirmed = window.confirm(
      `Confirma o retreino do modelo usando ${sampleCount} amostras?\n\n` +
        "Este processo pode demorar alguns minutos."
    );
    if (!confirmed) return;

    setState("loading");
    setResult(null);

    try {
      const res = await fetch("/api/admin/retrain", { method: "POST" });
      const data: RetrainResult = await res.json();
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
        onClick={handleRetrain}
        disabled={disabled || state === "loading"}
        className={`flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition ${
          disabled
            ? "cursor-not-allowed border border-dashed border-slate-700 bg-slate-900 text-slate-600"
            : state === "loading"
            ? "cursor-wait border border-slate-700 bg-slate-800 text-slate-400"
            : "border border-violet-600/50 bg-violet-600/20 text-violet-300 hover:bg-violet-600/30"
        }`}
      >
        {state === "loading" ? (
          <>
            <span className="animate-spin">⟳</span>
            Retreinando…
          </>
        ) : (
          <>
            <span>🔄</span>
            Retreinar agora
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
          <p className="font-semibold">{result.ok ? "✅ " + result.message : "❌ " + result.error}</p>
          {result.detail && (
            <p className="mt-1 text-slate-500">{result.detail}</p>
          )}
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
