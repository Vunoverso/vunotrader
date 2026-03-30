import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

type PlanChangeRow = {
  id: string;
  plan_id: string;
  change_type: string;
  field_name: string;
  old_value: string | null;
  new_value: string;
  created_at: string;
  saas_plans: {
    name: string;
    code: string;
  } | null;
};

function normalizeChange(rawChange: unknown): PlanChangeRow {
  const change = rawChange as Record<string, unknown>;
  const plans = change.saas_plans as Record<string, unknown> | Record<string, unknown>[] | null;
  const normalizedPlan = Array.isArray(plans) ? plans[0] : plans;

  return {
    id: (change.id as string) ?? "",
    plan_id: (change.plan_id as string) ?? "",
    change_type: (change.change_type as string) ?? "",
    field_name: (change.field_name as string) ?? "",
    old_value: (change.old_value as string | null) ?? null,
    new_value: (change.new_value as string) ?? "",
    created_at: (change.created_at as string) ?? "",
    saas_plans: normalizedPlan
      ? { name: ((normalizedPlan as Record<string, unknown>).name as string) ?? "", code: ((normalizedPlan as Record<string, unknown>).code as string) ?? "" }
      : null,
  };
}

function changeTypeBadge(changeType: string) {
  const badges: Record<
    string,
    { border: string; bg: string; text: string; label: string }
  > = {
    price_update: {
      border: "border-sky-500/30",
      bg: "bg-sky-500/10",
      text: "text-sky-300",
      label: "Atualização de preço",
    },
    limit_update: {
      border: "border-emerald-500/30",
      bg: "bg-emerald-500/10",
      text: "text-emerald-300",
      label: "Atualização de limite",
    },
    status_change: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/10",
      text: "text-amber-300",
      label: "Mudança de status",
    },
    plan_created: {
      border: "border-purple-500/30",
      bg: "bg-purple-500/10",
      text: "text-purple-300",
      label: "Plano criado",
    },
  };

  const badge = badges[changeType] || {
    border: "border-slate-700",
    bg: "bg-slate-800",
    text: "text-slate-400",
    label: changeType,
  };
  return (
    <span
      className={`rounded-full border ${badge.border} ${badge.bg} px-2 py-0.5 text-[11px] font-semibold ${badge.text}`}
    >
      {badge.label}
    </span>
  );
}

function formatFieldName(fieldName: string) {
  const names: Record<string, string> = {
    monthly_price: "Preço mensal",
    yearly_price: "Preço anual",
    max_users: "Máx. usuários",
    max_trades_per_month: "Trades/mês",
    max_ai_tokens_per_day: "Tokens/dia",
    max_storage_gb: "Storage (GB)",
    max_bots: "Bots",
    is_active: "Status",
    name: "Nome",
    code: "Código",
    description: "Descrição",
  };
  return names[fieldName] || fieldName;
}

export default async function AdminPlanosHistoricoPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user?.user_metadata?.is_admin !== true) {
    redirect("/app/dashboard");
  }

  const searchParams = await props.searchParams;
  const planId = (searchParams.plan_id as string) || "";
  const page = Math.max(1, parseInt((searchParams.page as string) || "1"));
  const pageSize = 25;
  const offset = (page - 1) * pageSize;

  // Get all plans for filter dropdown
  const { data: plans } = await supabase
    .from("saas_plans")
    .select("id, code, name")
    .order("monthly_price", { ascending: true });

  // Build query
  let query = supabase
    .from("plan_changes")
    .select(
      `
      id,
      plan_id,
      change_type,
      field_name,
      old_value,
      new_value,
      created_at,
      saas_plans(name, code)
    `,
      { count: "exact" }
    )
    .order("created_at", { ascending: false });

  if (planId) {
    query = query.eq("plan_id", planId);
  }

  const { data: changes, count } = await query.range(
    offset,
    offset + pageSize - 1
  );

  const changeRows = ((changes ?? []) as unknown[]).map(normalizeChange);
  const totalPages = Math.ceil((count ?? 0) / pageSize);

  // Stats
  const totalChanges = count ?? 0;
  const uniquePlansChanged = new Set(changeRows.map((c) => c.plan_id)).size;
  const priceUpdates = changeRows.filter(
    (c) => c.change_type === "price_update"
  ).length;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Histórico de planos</h1>
          <p className="text-sm text-slate-500">
            Auditoria completa de mudanças em preços, limites e status dos planos SaaS.
          </p>
        </div>
        <Link
          href="/app/admin/planos"
          className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-slate-300 transition-colors hover:bg-slate-700"
        >
          ← Back to Planos
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Total de mudanças</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{totalChanges}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Planos modificados</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">
            {uniquePlansChanged}
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Atualizações de preço</p>
          <p className="mt-2 text-2xl font-bold text-sky-400">{priceUpdates}</p>
        </div>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <form method="get" className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Filtro por plano
          </span>

          <select
            name="plan_id"
            defaultValue={planId}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
          >
            <option value="">Todos os planos</option>
            {(plans ?? []).map((plan) => (
              <option key={plan.id} value={plan.id}>
                {plan.name} ({plan.code})
              </option>
            ))}
          </select>
          <input type="hidden" name="page" value="1" />
          <button type="submit" className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-700">
            Aplicar
          </button>
        </form>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="px-4 py-3 text-left font-semibold text-slate-400">
                  Data
                </th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">
                  Plano
                </th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">
                  Tipo
                </th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">
                  Campo
                </th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">
                  Valor anterior
                </th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">
                  Novo valor
                </th>
              </tr>
            </thead>
            <tbody>
              {changeRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Nenhuma mudança encontrada.
                  </td>
                </tr>
              ) : (
                changeRows.map((change) => (
                  <tr
                    key={change.id}
                    className="border-b border-slate-800 transition-colors hover:bg-slate-800/50"
                  >
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-slate-200">
                          {new Date(change.created_at).toLocaleDateString("pt-BR")}
                        </span>
                        <span className="text-xs text-slate-600">
                          {new Date(change.created_at).toLocaleTimeString("pt-BR", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-slate-200">
                          {change.saas_plans?.name}
                        </span>
                        <span className="text-xs text-slate-600">
                          {change.saas_plans?.code}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {changeTypeBadge(change.change_type)}
                    </td>
                    <td className="px-4 py-3 text-slate-300">
                      {formatFieldName(change.field_name)}
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {change.old_value ? (
                        <code className="rounded bg-slate-950 px-2 py-1 font-mono text-xs">
                          {change.old_value}
                        </code>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <code className="rounded bg-emerald-950/50 px-2 py-1 font-mono text-xs text-emerald-300">
                        {change.new_value}
                      </code>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-800 pt-4">
            <p className="text-sm text-slate-500">
              Página {page} de {totalPages}
            </p>
            <div className="flex items-center gap-2">
              {page > 1 && (
                <Link
                  href={`?page=${page - 1}${planId ? `&plan_id=${planId}` : ""}`}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800"
                >
                  ← Anterior
                </Link>
              )}
              {page < totalPages && (
                <Link
                  href={`?page=${page + 1}${planId ? `&plan_id=${planId}` : ""}`}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800"
                >
                  Próxima →
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
