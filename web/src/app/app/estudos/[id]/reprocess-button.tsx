"use client";

import { useState } from "react";

export default function ReprocessButton({ materialId }: { materialId: string }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<"ok" | "error" | null>(null);

  async function handleReprocess() {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/study/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ materialId }),
      });
      const data = await res.json();
      setResult(data.ok ? "ok" : "error");
    } catch {
      setResult("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3 shrink-0">
      <button
        onClick={handleReprocess}
        disabled={loading}
        className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Processando…" : "Reprocessar"}
      </button>
      {result === "ok" && (
        <span className="text-xs text-emerald-400">Processamento iniciado.</span>
      )}
      {result === "error" && (
        <span className="text-xs text-red-400">Erro ao iniciar.</span>
      )}
    </div>
  );
}
