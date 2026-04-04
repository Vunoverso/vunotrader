import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";

export default async function AssinaturaPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  const access = await getSubscriptionAccess(supabase, user.id);

  const { data: plans } = await supabase
    .from("saas_plans")
    .select("id, code, name, description, monthly_price, yearly_price")
    .eq("is_active", true)
    .order("monthly_price", { ascending: true });

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Assinatura</h1>
        <p className="mt-1 text-sm text-slate-500">
          Gerencie seu período de teste e escolha um plano para liberar todos os módulos.
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-300">
        <p>
          Status atual: <span className="font-semibold text-slate-100">{access.status === "none" ? "Sem assinatura" : access.status}</span>
        </p>
        {access.isTrialing && (
          <p className="mt-1 text-amber-300">Teste grátis ativo: {access.trialDaysLeft} dia(s) restante(s).</p>
        )}
        {!access.hasActivePlan && (
          <p className="mt-1 text-slate-400">
            Operações, Auditoria e Estudos permanecem bloqueados até ativação do plano.
          </p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {(plans ?? []).map((plan) => (
          <div key={plan.id} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-lg font-semibold text-slate-100">{plan.name}</h2>
            <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">{plan.code}</p>
            <p className="mt-3 text-2xl font-bold text-sky-300">
              R$ {Number(plan.monthly_price ?? 0).toFixed(2)}
              <span className="text-sm font-medium text-slate-500">/mês</span>
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Anual: R$ {Number(plan.yearly_price ?? 0).toFixed(2)}
            </p>
            <p className="mt-3 min-h-12 text-sm text-slate-400">{plan.description ?? "Plano disponível para ativação."}</p>
            <button
              disabled
              className="mt-4 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-semibold text-slate-400"
            >
              Ativação via suporte (checkout em implantação)
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
