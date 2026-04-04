"use client";

import { useState } from "react";

type RobotProductType = "robo_integrado" | "robo_hibrido_visual";

interface InstallationAccess {
  hasActivePlan: boolean;
  isTrialing: boolean;
  trialDaysLeft: number;
  planCode: string | null;
  features: Record<string, boolean>;
}

type PackageResult = {
  ok: boolean;
  error?: string;
  warning?: string;
  instanceName?: string;
  bridgeName?: string;
  fileName?: string;
  mode?: "demo" | "real";
  productType?: RobotProductType;
  visualShadowEnabled?: boolean;
};

function resolveFileName(contentDisposition: string | null): string {
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition ?? "");
  return match?.[1] ?? "vuno-robo.zip";
}

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function Mt5CredentialsGenerator({ access }: { access: InstallationAccess | null }) {
  const [mode, setMode] = useState<"demo" | "real">("demo");
  const [productType, setProductType] = useState<RobotProductType>("robo_integrado");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PackageResult | null>(null);

  const visualHybridEnabled = Boolean(
    access?.features?.["robot.visual_hybrid"] && access?.features?.["robot.visual_shadow"]
  );

  const visualLineLabel = visualHybridEnabled
    ? "Liberado no seu plano"
    : access?.hasActivePlan
    ? "Upgrade do plano"
    : access?.isTrialing
    ? `Trial ${access.trialDaysLeft}d`
    : "Pro ou Scale";

  async function handleGenerate() {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/mt5/robot-package", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode, product_type: productType }),
      });

      if (!res.ok) {
        const data = (await res.json().catch(() => ({}))) as PackageResult;
        setResult({ ok: false, error: data.error ?? "Falha ao gerar o pacote do robo." });
        return;
      }

      const blob = await res.blob();
      const fileName = resolveFileName(res.headers.get("Content-Disposition"));
      const instanceName = res.headers.get("X-Vuno-Instance-Name") ?? undefined;
      const bridgeName = res.headers.get("X-Vuno-Bridge-Name") ?? undefined;
      const responseProductType = (res.headers.get("X-Vuno-Robot-Product-Type") as RobotProductType | null) ?? productType;
      const visualShadowEnabled = res.headers.get("X-Vuno-Visual-Shadow") === "true";

      downloadBlob(blob, fileName);
      window.dispatchEvent(new Event("vuno:robot-package-created"));

      setResult({
        ok: true,
        warning: "O pacote saiu com a chave da instancia embutida. Se gerar outro pacote, prefira pausar o anterior.",
        instanceName,
        bridgeName,
        fileName,
        mode,
        productType: responseProductType,
        visualShadowEnabled,
      });
    } catch {
      setResult({ ok: false, error: "Falha de rede ao gerar o pacote do robo." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded-2xl border border-sky-500/20 bg-sky-500/5 p-6 space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-sky-300">Gerar pacote fechado da instância</h2>
        <p className="mt-2 text-sm text-slate-300">
          Crie uma nova instância e baixe um zip já preenchido com token, bridge local, runtime/config.json e os
          arquivos do MT5. O iniciador do pacote usa o executável local quando ele já vier disponível.
        </p>
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {[
            "Cada download cria uma instância nova",
            "A chave já sai embutida no pacote",
            "No EA você só informa o InpBridgeRoot",
          ].map((item) => (
            <div key={item} className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2 text-xs text-slate-300">
              {item}
            </div>
          ))}
        </div>
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
          {loading ? "Montando pacote..." : "Criar instância e baixar pacote"}
        </button>
      </div>

      <div className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/40 p-4 md:grid-cols-2">
        <button
          type="button"
          onClick={() => setProductType("robo_integrado")}
          className={`rounded-xl border px-4 py-3 text-left transition-colors ${
            productType === "robo_integrado"
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
              : "border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-700"
          }`}
        >
          <p className="text-xs font-semibold uppercase tracking-wider text-emerald-300">Robo Integrado</p>
          <p className="mt-2 text-sm text-slate-200">Linha oficial com bridge local e execucao por snapshot estruturado.</p>
        </button>

        <button
          type="button"
          onClick={() => visualHybridEnabled && setProductType("robo_hibrido_visual")}
          disabled={!visualHybridEnabled}
          className={`rounded-xl border px-4 py-3 text-left transition-colors ${
            productType === "robo_hibrido_visual"
              ? "border-sky-500/40 bg-sky-500/10 text-sky-200"
              : visualHybridEnabled
              ? "border-slate-800 bg-slate-950/70 text-slate-300 hover:border-slate-700"
              : "cursor-not-allowed border-amber-500/20 bg-amber-500/5 text-slate-400"
          }`}
        >
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-sky-300">Robo Hibrido Visual</p>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-[10px] font-semibold text-slate-300">
              {visualLineLabel}
            </span>
          </div>
          <p className="mt-2 text-sm text-slate-200">Adiciona screenshot, contexto visual e shadow mode sem mudar a ordem oficial.</p>
        </button>
      </div>

      {result && !result.ok && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {result.error ?? "Falha ao gerar o pacote do robô."}
        </div>
      )}

      {result?.ok && (
        <div className="space-y-3">
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">
            {result.warning ?? "Pacote baixado. A chave já ficou embutida e o token não precisa mais ser copiado no EA."}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
              <p className="text-[11px] uppercase tracking-wider text-slate-500">Instância criada</p>
              <p className="mt-1 text-sm text-slate-100">{result.instanceName ?? "Instância Vuno"}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
              <p className="text-[11px] uppercase tracking-wider text-slate-500">Bridge para usar no EA</p>
              <p className="mt-1 font-mono text-sm text-slate-100">{result.bridgeName ?? "VunoBridge"}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3">
              <p className="text-[11px] uppercase tracking-wider text-slate-500">Linha do robo</p>
              <p className="mt-1 text-sm text-slate-100">
                {result.productType === "robo_hibrido_visual" ? "Robo Hibrido Visual" : "Robo Integrado"}
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 md:col-span-2">
              <p className="text-[11px] uppercase tracking-wider text-slate-500">Arquivo baixado</p>
              <p className="mt-1 text-sm text-slate-100">{result.fileName ?? "vuno-robo.zip"}</p>
            </div>
          </div>

          <p className="text-xs text-slate-400">
            Próximo passo: execute agent-local/iniciar-vuno-robo.cmd, copie o conteúdo de mt5/ para a pasta MQL5/Experts
            e use o valor de InpBridgeRoot informado acima. Esse iniciador prioriza vuno-agent.exe quando o pacote já
            sai com o binário pronto. Modo inicial: {(result.mode ?? mode).toUpperCase()}.
            {result.visualShadowEnabled ? " Shadow visual ja sai habilitado nesta instancia." : ""}
          </p>
        </div>
      )}
    </section>
  );
}
