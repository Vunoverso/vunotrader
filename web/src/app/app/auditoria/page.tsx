import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";
import AuditoriaTable, { type AuditRow } from "@/components/app/auditoria-table";

export default async function AuditoriaPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="Auditoria" />;
  }

  const { data: decisions } = await supabase
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
    .limit(100);

  const rows = (decisions ?? []) as unknown as AuditRow[];

  return <div className="mx-auto max-w-6xl"><AuditoriaTable rows={rows} currentDateIso={new Date().toISOString()} /></div>;
}
