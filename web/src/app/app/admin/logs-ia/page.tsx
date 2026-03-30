import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

type SearchParams = Promise<{
  provider?: string;
  task?: string;
  period?: string;
  page?: string;
}>;

type AiLogRow = {
  id: string;
  provider: string | null;
  model_name: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  estimated_cost: number | null;
  task_type: string | null;
  user_id: string | null;
  created_at: string;
  organizations: { name: string | null } | { name: string | null }[] | null;
};

function badgeTone(value: string) {
  const map: Record<string, string> = {
    openai: "border-sky-500/30 bg-sky-500/10 text-sky-300",
    rag: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    ingestion: "border-violet-500/30 bg-violet-500/10 text-violet-300",
    analysis: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  };

  return map[value.toLowerCase()] ?? "border-slate-700 bg-slate-800 text-slate-300";
}

export default async function AdminLogsIaPage({ searchParams }: { searchParams: SearchParams }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user?.user_metadata?.is_admin !== true) {
    redirect("/app/dashboard");
  }

  const params = await searchParams;
  const provider = (params.provider ?? "all").trim();
  const task = (params.task ?? "all").trim();
  const period = (params.period ?? "7d").trim();
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const pageSize = 20;

  const periodStart = new Date();
  if (period === "1d") periodStart.setDate(periodStart.getDate() - 1);
  else if (period === "30d") periodStart.setDate(periodStart.getDate() - 30);
  else periodStart.setDate(periodStart.getDate() - 7);

  let countQuery = supabase
    .from("ai_usage_logs")
    .select("id", { count: "exact", head: true })
    .gte("created_at", periodStart.toISOString());

  let dataQuery = supabase
    .from("ai_usage_logs")
    .select("id, provider, model_name, prompt_tokens, completion_tokens, total_tokens, estimated_cost, task_type, user_id, created_at, organizations(name)")
    .gte("created_at", periodStart.toISOString())
    .order("created_at", { ascending: false });

  if (provider !== "all") {
    countQuery = countQuery.eq("provider", provider);
    dataQuery = dataQuery.eq("provider", provider);
  }

  if (task !== "all") {
    countQuery = countQuery.eq("task_type", task);
    dataQuery = dataQuery.eq("task_type", task);
  }

  const from = (page - 1) * pageSize;
  const to = from + pageSize - 1;

  const [{ count }, { data: logs }, { data: recentLogs }, { data: providers }, { data: tasks }] = await Promise.all([
    countQuery,
    dataQuery.range(from, to),
    supabase
      .from("ai_usage_logs")
      .select("provider, task_type, total_tokens, estimated_cost, organizations(name), created_at")
      .gte("created_at", periodStart.toISOString())
      .order("created_at", { ascending: false })
      .limit(250),
    supabase.from("ai_usage_logs").select("provider").not("provider", "is", null).limit(200),
    supabase.from("ai_usage_logs").select("task_type").not("task_type", "is", null).limit(200),
  ]);

  const rows = (logs ?? []) as AiLogRow[];
  const metricsBase = (recentLogs ?? []).filter((row) => {
    if (provider !== "all" && row.provider !== provider) return false;
    if (task !== "all" && row.task_type !== task) return false;
    return true;
  });

  const totalTokens = metricsBase.reduce((acc, row) => acc + (row.total_tokens ?? 0), 0);
  const totalCost = metricsBase.reduce((acc, row) => acc + Number(row.estimated_cost ?? 0), 0);
  const organizations = new Set(
    metricsBase
      .map((row) => {
        const org = Array.isArray(row.organizations) ? row.organizations[0] : row.organizations;
        return org?.name ?? null;
      })
      .filter(Boolean),
  );

  const totalPages = Math.max(1, Math.ceil((count ?? 0) / pageSize));
  const providerOptions = Array.from(new Set((providers ?? []).map((row) => row.provider).filter(Boolean))).sort();
  const taskOptions = Array.from(new Set((tasks ?? []).map((row) => row.task_type).filter(Boolean))).sort();

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Logs de IA</h1>
          <p className="text-sm text-slate-500">Consumo, custo estimado e trilha operacional dos jobs de IA.</p>
        </div>
        <Link href="/app/admin" className="text-sm font-medium text-sky-300 hover:text-sky-200">
          Voltar ao admin
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Logs no recorte</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{count ?? 0}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Tokens consumidos</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{totalTokens.toLocaleString("pt-BR")}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Custo estimado</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">US$ {totalCost.toFixed(4)}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Orgs impactadas</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{organizations.size}</p>
        </div>
      </div>

      <form className="grid gap-3 rounded-xl border border-slate-800 bg-slate-900 p-4 lg:grid-cols-[repeat(3,220px)_auto]">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Provider</label>
          <select name="provider" defaultValue={provider} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500">
            <option value="all">Todos</option>
            {providerOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Tipo de tarefa</label>
          <select name="task" defaultValue={task} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500">
            <option value="all">Todos</option>
            {taskOptions.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Período</label>
          <select name="period" defaultValue={period} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500">
            <option value="1d">Últimas 24h</option>
            <option value="7d">Últimos 7 dias</option>
            <option value="30d">Últimos 30 dias</option>
          </select>
        </div>
        <div className="flex items-end">
          <button className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20">
            Aplicar filtros
          </button>
        </div>
      </form>

      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-950/60">
              <tr className="border-b border-slate-800">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Quando</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Provider</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Modelo / tarefa</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Organização</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Tokens</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Custo</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-500">Nenhum log encontrado com esse recorte.</td>
                </tr>
              ) : (
                rows.map((row) => {
                  const org = Array.isArray(row.organizations) ? row.organizations[0] : row.organizations;
                  return (
                    <tr key={row.id} className="border-b border-slate-800/70 last:border-b-0 hover:bg-slate-800/30">
                      <td className="px-4 py-3 text-slate-400">{new Date(row.created_at).toLocaleString("pt-BR")}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${badgeTone(row.provider ?? "")}`}>
                          {row.provider ?? "—"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-200">{row.model_name ?? "Modelo não informado"}</p>
                        <p className="text-xs text-slate-500">{row.task_type ?? "Sem tipo"} · prompt {row.prompt_tokens ?? 0} · completion {row.completion_tokens ?? 0}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{org?.name ?? row.user_id ?? "—"}</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-300">{(row.total_tokens ?? 0).toLocaleString("pt-BR")}</td>
                      <td className="px-4 py-3 text-right font-mono text-emerald-300">US$ {Number(row.estimated_cost ?? 0).toFixed(4)}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-400">
        <p>Página {page} de {totalPages}</p>
        <div className="flex items-center gap-2">
          <Link
            href={`?provider=${encodeURIComponent(provider)}&task=${encodeURIComponent(task)}&period=${encodeURIComponent(period)}&page=${Math.max(1, page - 1)}`}
            className={`rounded-lg border px-3 py-1.5 ${page <= 1 ? "pointer-events-none border-slate-800 text-slate-600" : "border-slate-700 text-slate-300 hover:border-slate-500"}`}
          >
            Anterior
          </Link>
          <Link
            href={`?provider=${encodeURIComponent(provider)}&task=${encodeURIComponent(task)}&period=${encodeURIComponent(period)}&page=${Math.min(totalPages, page + 1)}`}
            className={`rounded-lg border px-3 py-1.5 ${page >= totalPages ? "pointer-events-none border-slate-800 text-slate-600" : "border-slate-700 text-slate-300 hover:border-slate-500"}`}
          >
            Próxima
          </Link>
        </div>
      </div>
    </div>
  );
}