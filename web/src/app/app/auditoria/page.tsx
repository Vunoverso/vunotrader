import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";
import AuditoriaTable, { type AuditRow } from "@/components/app/auditoria-table";

function isDynamicServerError(error: unknown) {
  return !!(
    error &&
    typeof error === "object" &&
    "digest" in error &&
    (error as { digest?: string }).digest === "DYNAMIC_SERVER_USAGE"
  );
}

export default async function AuditoriaPage() {
  let supabase;
  try {
    supabase = await createClient();
  } catch (err) {
    if (isDynamicServerError(err)) {
      throw err;
    }
    console.error("[AuditoriaPage] Falha ao criar cliente Supabase:", err);
    return (
      <div className="p-8 text-center text-sm text-slate-400">
        Serviço temporariamente indisponível. Tente novamente em instantes.
      </div>
    );
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return null;

  let access;
  try {
    access = await getSubscriptionAccess(supabase, user.id);
  } catch (err) {
    if (isDynamicServerError(err)) {
      throw err;
    }
    console.error("[AuditoriaPage] Falha ao validar assinatura:", err);
    return (
      <div className="p-8 text-center text-sm text-slate-400">
        Não foi possível validar a assinatura neste momento.
      </div>
    );
  }

  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="Auditoria" />;
  }

  let rows: AuditRow[] = [];
  try {
    const { data: decisions, error } = await supabase
      .from("trade_decisions")
      .select(`
        id,
        symbol,
        timeframe,
        side,
        confidence,
        risk_pct,
        mode,
        rationale,
        created_at,
        entry_price,
        stop_loss,
        take_profit,
        outcome_status,
        outcome_profit,
        outcome_pips,
        closed_at,
        duration_seconds,
        post_analysis,
        executed_trades (
          id,
          status,
          opened_at,
          closed_at,
          trade_outcomes (
            result,
            pnl_money,
            win_loss_reason,
            post_analysis
          )
        )
      `)
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(200);

    if (error) {
      console.error("[AuditoriaPage] Erro na query Supabase:", error.message, error.code);
    } else {
      rows = (decisions ?? []) as unknown as AuditRow[];
    }
  } catch (err) {
    if (isDynamicServerError(err)) {
      throw err;
    }
    console.error("[AuditoriaPage] Exceção inesperada na query:", err);
  }

  return <div className="mx-auto max-w-6xl"><AuditoriaTable rows={rows} currentDateIso={new Date().toISOString()} /></div>;
}
