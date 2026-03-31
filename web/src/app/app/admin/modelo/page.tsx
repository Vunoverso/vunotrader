/**
 * /app/admin/modelo
 *
 * Página de gerenciamento do modelo ML de retreino.
 * - Exibe métricas do último retreino (tabela model_metrics).
 * - Botão "Retreinar agora" dispara POST /api/admin/retrain (Client Component).
 * - Seção de instruções para retreino manual / automático.
 */

import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import RetrainButton from "@/components/app/admin-retrain-button";

// ── Tipos ─────────────────────────────────────────────────────
type ModelMetric = {
  id: string;
  accuracy_rf: number | null;
  accuracy_gb: number | null;
  accuracy_ensemble: number | null;
  n_samples: number | null;
  win_rate: number | null;
  trained_at: string;
  notes: string | null;
};

// ── Helpers ───────────────────────────────────────────────────
function pct(v: number | null) {
  if (v === null || v === undefined) return "–";
  return `${(v * 100).toFixed(1)} %`;
}

function fmt(v: number | null) {
  if (v === null || v === undefined) return "–";
  return v.toLocaleString("pt-BR");
}

function fmtDt(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function MetricCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-white">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-600">{sub}</p>}
    </div>
  );
}

function AccuracyBar({ label, value }: { label: string; value: number | null }) {
  const pval = value === null ? 0 : Math.round(value * 100);
  const color =
    pval >= 65 ? "bg-green-500" : pval >= 55 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span className="font-medium text-white">{pct(value)}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pval}%` }}
        />
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────
export default async function ModeloAdminPage() {
  // Auth
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  // Verifica admin
  const admin = createAdminClient();
  const { data: profile } = await admin
    .from("user_profiles")
    .select("is_platform_admin")
    .eq("id", user.id)
    .single();

  if (!profile?.is_platform_admin) return notFound();

  // Carrega métricas do modelo
  const { data: metricsRaw } = await admin
    .from("model_metrics")
    .select(
      "id, accuracy_rf, accuracy_gb, accuracy_ensemble, n_samples, win_rate, trained_at, notes"
    )
    .order("trained_at", { ascending: false })
    .limit(10);

  const metrics = (metricsRaw ?? []) as ModelMetric[];
  const latest = metrics[0] ?? null;

  // Conta amostras disponíveis para retreino
  const { count: sampleCount } = await admin
    .from("anonymized_trade_events")
    .select("id", { count: "exact", head: true });

  const readyToRetrain = (sampleCount ?? 0) >= 50;

  return (
    <div className="mx-auto max-w-4xl space-y-10 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Link href="/app/admin" className="hover:text-slate-300">
              Admin
            </Link>
            <span>/</span>
            <span className="text-slate-300">Modelo ML</span>
          </div>
          <h1 className="mt-1 text-2xl font-bold text-white">Modelo ML</h1>
          <p className="mt-1 text-sm text-slate-400">
            Métricas do ensemble (RandomForest + GradientBoosting) e controle de retreino.
          </p>
        </div>
        <RetrainButton disabled={!readyToRetrain} sampleCount={sampleCount ?? 0} />
      </div>

      {/* Aviso de amostras */}
      {!readyToRetrain && (
        <div className="rounded-xl border border-amber-800/40 bg-amber-950/30 px-4 py-3 text-sm text-amber-300">
          <strong>Amostras insuficientes:</strong> {sampleCount ?? 0} de 50 mínimas registradas.
          O motor precisa executar mais operações antes de retreinar.
        </div>
      )}

      {/* Métricas do último treino */}
      {latest ? (
        <>
          <div>
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">
              Último retreino — {fmtDt(latest.trained_at)}
            </h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <MetricCard
                label="Amostras"
                value={fmt(latest.n_samples)}
                sub="operações anonimizadas"
              />
              <MetricCard
                label="Win Rate"
                value={pct(latest.win_rate)}
                sub="dados de treino"
              />
              <MetricCard
                label="Acc. Ensemble"
                value={pct(latest.accuracy_ensemble)}
                sub="modelo final"
              />
              <MetricCard
                label="Registros disponíveis"
                value={fmt(sampleCount)}
                sub="base anonymized_trade_events"
              />
            </div>
          </div>

          {/* Barras de acurácia */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-slate-300">Acurácia por modelo</h2>
            <AccuracyBar label="Random Forest" value={latest.accuracy_rf} />
            <AccuracyBar label="Gradient Boosting" value={latest.accuracy_gb} />
            <AccuracyBar label="Ensemble (votação)" value={latest.accuracy_ensemble} />
            {latest.notes && (
              <p className="mt-2 text-xs text-slate-600">{latest.notes}</p>
            )}
          </div>

          {/* Histórico */}
          {metrics.length > 1 && (
            <div>
              <h2 className="mb-3 text-sm font-semibold text-slate-500">
                Histórico de treinos
              </h2>
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-sm text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs text-slate-500">
                      <th className="px-4 py-2.5 text-left">Data</th>
                      <th className="px-4 py-2.5 text-right">RF</th>
                      <th className="px-4 py-2.5 text-right">GB</th>
                      <th className="px-4 py-2.5 text-right">Ensemble</th>
                      <th className="px-4 py-2.5 text-right">Amostras</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((m, i) => (
                      <tr
                        key={m.id}
                        className={`border-b border-slate-800/50 ${i === 0 ? "bg-slate-800/20" : ""}`}
                      >
                        <td className="px-4 py-2.5 text-slate-400">{fmtDt(m.trained_at)}</td>
                        <td className="px-4 py-2.5 text-right">{pct(m.accuracy_rf)}</td>
                        <td className="px-4 py-2.5 text-right">{pct(m.accuracy_gb)}</td>
                        <td className="px-4 py-2.5 text-right font-medium text-white">
                          {pct(m.accuracy_ensemble)}
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-500">
                          {fmt(m.n_samples)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/30 p-10 text-center">
          <p className="text-4xl">🤖</p>
          <p className="mt-3 font-medium text-slate-300">Nenhum retreino registrado ainda</p>
          <p className="mt-1 text-sm text-slate-500">
            Execute o primeiro retreino para ver as métricas aqui.
          </p>
        </div>
      )}

      {/* Instruções */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">Como funciona o retreino</h2>
        <div className="space-y-3 text-sm text-slate-400">
          <p>
            O pipeline lê a tabela <code className="rounded bg-slate-800 px-1 text-slate-200">anonymized_trade_events</code>,
            seleciona operações dos últimos 30 dias, treina dois modelos (RF + GB) e salva
            no disco como <code className="rounded bg-slate-800 px-1 text-slate-200">brain_model_rf.pkl</code> /
            <code className="rounded bg-slate-800 px-1 text-slate-200">brain_model_gb.pkl</code>.
          </p>
          <p>
            Ao clicar em <strong className="text-white">Retreinar agora</strong>, o servidor executa
            o script <code className="rounded bg-slate-800 px-1 text-slate-200">retrain_pipeline.py</code> com{" "}
            <code className="rounded bg-slate-800 px-1 text-slate-200">--days 30 --min-samples 50</code>.
          </p>
          <div className="mt-2 rounded-lg bg-slate-800/60 p-4 font-mono text-xs text-slate-300">
            python retrain_pipeline.py --days 30 --min-samples 50 --dry-run
          </div>
          <p className="text-xs text-slate-600">
            Use <code>--dry-run</code> para simular sem sobrescrever os modelos em disco.
            Mínimo recomendado: 50 amostras. Executar semanalmente após volume suficiente.
          </p>
        </div>
      </div>
    </div>
  );
}
