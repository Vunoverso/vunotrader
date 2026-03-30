import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createPlanAction, updatePlanAction } from "./actions";

type PlanRow = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  monthly_price: number;
  yearly_price: number | null;
  is_active: boolean;
  saas_plan_limits:
    | {
        id: string;
        max_users: number | null;
        max_trades_per_month: number | null;
        max_ai_tokens_per_day: number | null;
        max_storage_gb: number | null;
        max_bots: number | null;
      }[]
    | null;
};

type SubscriptionRow = {
  id: string;
  status: string;
  billing_cycle: "monthly" | "yearly";
  current_period_end: string | null;
  organizations: { name: string | null } | { name: string | null }[] | null;
  saas_plans: { code: string; name: string } | { code: string; name: string }[] | null;
};

function currency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value ?? 0);
}

function statusBadge(active: boolean) {
  return active
    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
    : "border-slate-700 bg-slate-800 text-slate-400";
}

export default async function AdminPlanosPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user?.user_metadata?.is_admin !== true) {
    redirect("/app/dashboard");
  }

  const { data: plans } = await supabase
    .from("saas_plans")
    .select("id, code, name, description, monthly_price, yearly_price, is_active, saas_plan_limits(id, max_users, max_trades_per_month, max_ai_tokens_per_day, max_storage_gb, max_bots)")
    .order("monthly_price", { ascending: true });

  const { data: subscriptions } = await supabase
    .from("saas_subscriptions")
    .select("id, status, billing_cycle, current_period_end, organizations(name), saas_plans(code, name)")
    .order("created_at", { ascending: false })
    .limit(18);

  const planRows = (plans ?? []) as PlanRow[];
  const subRows = (subscriptions ?? []) as SubscriptionRow[];

  const activePlans = planRows.filter((plan) => plan.is_active).length;
  const monthlyMrr = subRows.reduce((acc, sub) => {
    const plan = Array.isArray(sub.saas_plans) ? sub.saas_plans[0] : sub.saas_plans;
    const currentPlan = planRows.find((item) => item.code === plan?.code);
    if (sub.status !== "active" || !currentPlan) return acc;
    const value = sub.billing_cycle === "yearly" ? (currentPlan.yearly_price ?? currentPlan.monthly_price * 12) / 12 : currentPlan.monthly_price;
    return acc + value;
  }, 0);
  const tokenCapacity = planRows.reduce((acc, plan) => acc + (plan.saas_plan_limits?.[0]?.max_ai_tokens_per_day ?? 0), 0);

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Planos</h1>
          <p className="text-sm text-slate-500">Catálogo SaaS, limites operacionais e visão rápida das assinaturas.</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-2">
          <Link href="/app/admin/planos/historico" className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs text-slate-300 transition-colors hover:bg-slate-700">
            📜 Ver histórico
          </Link>
          <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-xs text-slate-500">
            Edite preço, status e limites sem sair do painel admin.
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Planos ativos</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{activePlans}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Assinaturas monitoradas</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{subRows.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Capacidade diária de tokens</p>
          <p className="mt-2 text-2xl font-bold text-slate-100">{tokenCapacity.toLocaleString("pt-BR")}</p>
          <p className="mt-1 text-xs text-slate-600">MRR estimado: {currency(monthlyMrr)}</p>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <div className="space-y-5">
          <form action={createPlanAction} className="rounded-2xl border border-emerald-800/40 bg-emerald-950/20 p-5">
            <div className="mb-4 flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded bg-emerald-500/20 text-emerald-400 text-sm font-bold">
                +
              </span>
              <h2 className="text-lg font-semibold text-slate-100">Novo plano</h2>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Código (slug)</span>
                <input name="code" placeholder="e.g. enterprise" required className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Nome</span>
                <input name="name" placeholder="e.g. Enterprise" required className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Preço mensal</span>
                <input name="monthly_price" type="number" min="0" step="0.01" placeholder="0.00" required className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Preço anual (opcional)</span>
                <input name="yearly_price" type="number" min="0" step="0.01" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm md:col-span-2 xl:col-span-2">
                <span className="text-slate-500">Descrição</span>
                <input name="description" placeholder="Descrição breve do plano" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Máx. usuários</span>
                <input name="max_users" type="number" min="0" step="1" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Trades/mês</span>
                <input name="max_trades_per_month" type="number" min="0" step="1" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Tokens/dia</span>
                <input name="max_ai_tokens_per_day" type="number" min="0" step="1" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Storage GB</span>
                <input name="max_storage_gb" type="number" min="0" step="0.1" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-slate-500">Bots</span>
                <input name="max_bots" type="number" min="0" step="1" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-emerald-500" />
              </label>
            </div>

            <div className="mt-5 flex items-center justify-end">
              <button className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300 transition-colors hover:bg-emerald-500/20">
                Criar plano
              </button>
            </div>
          </form>
          {planRows.map((plan) => {
            const limits = plan.saas_plan_limits?.[0];
            return (
              <form key={plan.id} action={updatePlanAction} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
                <input type="hidden" name="plan_id" value={plan.id} />

                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-semibold text-slate-100">{plan.name}</h2>
                      <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${statusBadge(plan.is_active)}`}>
                        {plan.is_active ? "Ativo" : "Inativo"}
                      </span>
                    </div>
                    <p className="mt-1 text-xs uppercase tracking-[0.24em] text-slate-600">{plan.code}</p>
                  </div>

                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      name="is_active"
                      value="true"
                      defaultChecked={plan.is_active}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-sky-500"
                    />
                    Plano liberado
                  </label>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Nome</span>
                    <input name="name" defaultValue={plan.name} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Preço mensal</span>
                    <input name="monthly_price" type="number" min="0" step="0.01" defaultValue={plan.monthly_price} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Preço anual</span>
                    <input name="yearly_price" type="number" min="0" step="0.01" defaultValue={plan.yearly_price ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                </div>

                <label className="mt-4 block space-y-1 text-sm">
                  <span className="text-slate-500">Descrição</span>
                  <textarea name="description" defaultValue={plan.description ?? ""} rows={2} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                </label>

                <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Máx. usuários</span>
                    <input name="max_users" type="number" min="0" step="1" defaultValue={limits?.max_users ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Trades/mês</span>
                    <input name="max_trades_per_month" type="number" min="0" step="1" defaultValue={limits?.max_trades_per_month ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Tokens/dia</span>
                    <input name="max_ai_tokens_per_day" type="number" min="0" step="1" defaultValue={limits?.max_ai_tokens_per_day ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Storage GB</span>
                    <input name="max_storage_gb" type="number" min="0" step="0.1" defaultValue={limits?.max_storage_gb ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                  <label className="space-y-1 text-sm">
                    <span className="text-slate-500">Bots</span>
                    <input name="max_bots" type="number" min="0" step="1" defaultValue={limits?.max_bots ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
                  </label>
                </div>

                <div className="mt-5 flex items-center justify-end">
                  <button className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20">
                    Salvar plano
                  </button>
                </div>
              </form>
            );
          })}
        </div>

        <div className="space-y-5">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-500">Assinaturas recentes</h2>
            <div className="mt-4 space-y-3">
              {subRows.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 px-4 py-8 text-center text-sm text-slate-500">
                  Nenhuma assinatura encontrada.
                </div>
              ) : (
                subRows.map((sub) => {
                  const org = Array.isArray(sub.organizations) ? sub.organizations[0] : sub.organizations;
                  const plan = Array.isArray(sub.saas_plans) ? sub.saas_plans[0] : sub.saas_plans;

                  return (
                    <div key={sub.id} className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-200">{org?.name ?? "Organização sem nome"}</p>
                          <p className="text-xs text-slate-500">{plan?.name ?? "Plano indefinido"} · {sub.billing_cycle === "yearly" ? "Anual" : "Mensal"}</p>
                        </div>
                        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${sub.status === "active" ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}>
                          {sub.status}
                        </span>
                      </div>
                      <p className="mt-2 text-xs text-slate-600">
                        Vigência até {sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString("pt-BR") : "—"}
                      </p>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}