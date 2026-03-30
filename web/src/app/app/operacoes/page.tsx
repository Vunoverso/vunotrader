import { createClient } from "@/lib/supabase/server";
import OperacoesTable from "@/components/app/operacoes-table";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";

export default async function OperacoesPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="Operações" />;
  }

  // Últimas 100 operações do usuário com decisão e resultado
  const { data: trades } = await supabase
    .from("executed_trades")
    .select(`
      id,
      broker_ticket,
      entry_price,
      stop_loss,
      take_profit,
      lot,
      status,
      opened_at,
      closed_at,
      trade_decisions!inner (
        symbol,
        timeframe,
        side,
        confidence,
        risk_pct,
        rationale,
        mode,
        user_id
      ),
      trade_outcomes (
        result,
        pnl_money,
        pnl_points,
        win_loss_reason
      )
    `)
    .eq("trade_decisions.user_id", user.id)
    .order("opened_at", { ascending: false })
    .limit(100);

  return <OperacoesTable trades={trades ?? []} />;
}
