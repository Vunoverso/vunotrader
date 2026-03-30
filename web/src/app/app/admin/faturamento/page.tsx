import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

type BillingEventRow = {
  id: string;
  event_type: string;
  amount: number;
  currency: string;
  status: string;
  provider: string;
  provider_event_id: string | null;
  created_at: string;
  saas_subscriptions: {
    id: string;
    billing_cycle: "monthly" | "yearly";
    organizations: {
      name: string | null;
    } | null;
    saas_plans: {
      code: string;
      name: string;
    } | null;
  } | null;
};

function normalizeEvent(rawEvent: unknown): BillingEventRow {
  const event = rawEvent as Record<string, unknown>;
  const sub = event.saas_subscriptions as Record<string, unknown> | Record<string, unknown>[] | null;
  const normalizedSub = Array.isArray(sub) ? sub[0] : sub;

  const orgs = normalizedSub ? (normalizedSub as Record<string, unknown>).organizations : null;
  const normalizedOrgs = Array.isArray(orgs) ? orgs[0] : orgs;
  const plans = normalizedSub ? (normalizedSub as Record<string, unknown>).saas_plans : null;
  const normalizedPlans = Array.isArray(plans) ? plans[0] : plans;

  return {
    id: (event.id as string) ?? "",
    event_type: (event.event_type as string) ?? "",
    amount: (event.amount as number) ?? 0,
    currency: (event.currency as string) ?? "",
    status: (event.status as string) ?? "",
    provider: (event.provider as string) ?? "",
    provider_event_id: (event.provider_event_id as string | null) ?? null,
    created_at: (event.created_at as string) ?? "",
    saas_subscriptions: normalizedSub
      ? {
          id: ((normalizedSub as Record<string, unknown>).id as string) ?? "",
          billing_cycle:
            (((normalizedSub as Record<string, unknown>).billing_cycle as string) ?? "monthly") as
              | "monthly"
              | "yearly",
          organizations: normalizedOrgs
            ? { name: ((normalizedOrgs as Record<string, unknown>).name as string | null) ?? null }
            : null,
          saas_plans: normalizedPlans
            ? {
                code: ((normalizedPlans as Record<string, unknown>).code as string) ?? "",
                name: ((normalizedPlans as Record<string, unknown>).name as string) ?? "",
              }
            : null,
        }
      : null,
  };
}

function currency(value: number | null | undefined) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value ?? 0);
}

function eventTypeBadge(eventType: string) {
  const badges: Record<string, { border: string; bg: string; text: string; label: string }> = {
    charge_attempted: { border: "border-blue-500/30", bg: "bg-blue-500/10", text: "text-blue-300", label: "Tentativa" },
    charge_succeeded: { border: "border-emerald-500/30", bg: "bg-emerald-500/10", text: "text-emerald-300", label: "Sucesso" },
    charge_failed: { border: "border-red-500/30", bg: "bg-red-500/10", text: "text-red-300", label: "Falha" },
    refund_issued: { border: "border-amber-500/30", bg: "bg-amber-500/10", text: "text-amber-300", label: "Reembolso" },
    subscription_created: { border: "border-purple-500/30", bg: "bg-purple-500/10", text: "text-purple-300", label: "Nova assinatura" },
    subscription_canceled: { border: "border-slate-600", bg: "bg-slate-800", text: "text-slate-400", label: "Cancelada" },
  };

  const badge = badges[eventType] || { border: "border-slate-700", bg: "bg-slate-800", text: "text-slate-400", label: eventType };
  return <span className={`rounded-full border ${badge.border} ${badge.bg} px-2 py-0.5 text-[11px] font-semibold ${badge.text}`}>{badge.label}</span>;
}

export default async function AdminFaturamentoPage(props: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user?.user_metadata?.is_admin !== true) {
    redirect("/app/dashboard");
  }

  const searchParams = await props.searchParams;
  const status = (searchParams.status as string) || "";
  const provider = (searchParams.provider as string) || "";
  const page = Math.max(1, parseInt((searchParams.page as string) || "1"));
  const pageSize = 20;
  const offset = (page - 1) * pageSize;

  // Build query
  let query = supabase
    .from("billing_events")
    .select(
      `
      id,
      event_type,
      amount,
      currency,
      status,
      provider,
      provider_event_id,
      created_at,
      saas_subscriptions(
        id,
        billing_cycle,
        organizations(name),
        saas_plans(code, name)
      )
    `,
      { count: "exact" }
    )
    .order("created_at", { ascending: false });

  if (status) {
    query = query.eq("status", status);
  }

  if (provider) {
    query = query.eq("provider", provider);
  }

  const { data: events, count } = await query.range(offset, offset + pageSize - 1);

  const eventRows = ((events ?? []) as unknown[]).map(normalizeEvent);
  const totalPages = Math.ceil((count ?? 0) / pageSize);

  // Aggregates
  const successfulCharges = eventRows.filter((e) => e.event_type === "charge_succeeded").reduce((acc, e) => acc + e.amount, 0);
  const failedCharges = eventRows.filter((e) => e.event_type === "charge_failed").reduce((acc, e) => acc + e.amount, 0);
  const totalRefunds = eventRows.filter((e) => e.event_type === "refund_issued").reduce((acc, e) => acc + e.amount, 0);

  const uniqueProviders = [...new Set(eventRows.map((e) => e.provider))];

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Faturamento</h1>
          <p className="text-sm text-slate-500">Histórico de eventos de cobrança, reembolsos e integrações com provedores de pagamento.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-xs text-slate-500">
          Eventos sincronizados com Stripe, PayPal ou gateway configurado.
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Cobranças bem-sucedidas</p>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{currency(successfulCharges)}</p>
          <p className="mt-1 text-xs text-slate-600">{eventRows.filter((e) => e.event_type === "charge_succeeded").length} eventos</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Cobranças falhadas</p>
          <p className="mt-2 text-2xl font-bold text-red-400">{currency(failedCharges)}</p>
          <p className="mt-1 text-xs text-slate-600">{eventRows.filter((e) => e.event_type === "charge_failed").length} eventos</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs text-slate-500">Reembolsos emitidos</p>
          <p className="mt-2 text-2xl font-bold text-amber-400">{currency(totalRefunds)}</p>
          <p className="mt-1 text-xs text-slate-600">{eventRows.filter((e) => e.event_type === "refund_issued").length} eventos</p>
        </div>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5">
        <form method="get" className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">Filtros</span>
          </div>

          <select
            name="status"
            defaultValue={status}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
          >
            <option value="">Todos os status</option>
            <option value="succeeded">Sucesso</option>
            <option value="pending">Pendente</option>
            <option value="failed">Falha</option>
          </select>

          <select
            name="provider"
            defaultValue={provider}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
          >
            <option value="">Todos os provedores</option>
            {uniqueProviders.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
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
                <th className="px-4 py-3 text-left font-semibold text-slate-400">Data</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">Tipo de evento</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">Organização</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">Plano</th>
                <th className="px-4 py-3 text-right font-semibold text-slate-400">Valor</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-400">Provedor</th>
              </tr>
            </thead>
            <tbody>
              {eventRows.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Nenhum evento de faturamento encontrado.
                  </td>
                </tr>
              ) : (
                eventRows.map((event) => {
                  const org = event.saas_subscriptions?.organizations;
                  const plan = event.saas_subscriptions?.saas_plans;
                  return (
                    <tr key={event.id} className="border-b border-slate-800 transition-colors hover:bg-slate-800/50">
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="text-slate-200">{new Date(event.created_at).toLocaleDateString("pt-BR")}</span>
                          <span className="text-xs text-slate-600">{new Date(event.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">{eventTypeBadge(event.event_type)}</td>
                      <td className="px-4 py-3 text-slate-300">{org?.name ?? "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="text-slate-200">{plan?.name ?? "—"}</span>
                          <span className="text-xs text-slate-600">{plan?.code ?? "—"}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-semibold ${event.amount < 0 ? "text-red-400" : "text-emerald-400"}`}>{currency(event.amount)}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col">
                          <span className="text-slate-300">{event.provider}</span>
                          {event.provider_event_id && <span className="text-xs text-slate-600 font-mono">{event.provider_event_id.substring(0, 16)}...</span>}
                        </div>
                      </td>
                    </tr>
                  );
                })
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
                <Link href={`?page=${page - 1}${status ? `&status=${status}` : ""}${provider ? `&provider=${provider}` : ""}`} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800">
                  ← Anterior
                </Link>
              )}
              {page < totalPages && (
                <Link href={`?page=${page + 1}${status ? `&status=${status}` : ""}${provider ? `&provider=${provider}` : ""}`} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition-colors hover:bg-slate-800">
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
