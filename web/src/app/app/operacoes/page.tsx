import { createClient } from "@/lib/supabase/server";
import OperacoesTable from "@/components/app/operacoes-table";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";

type TradeDecisionRow = {
  symbol: string;
  timeframe: string;
  side: "buy" | "sell" | "hold";
  confidence: number | null;
  risk_pct: number | null;
  rationale: string | null;
  mode: string;
};

type TradeOutcomeRow = {
  result: "win" | "loss" | "breakeven";
  pnl_money: number | null;
  pnl_points: number | null;
  win_loss_reason: string | null;
};

type TradeRow = {
  id: string;
  broker_ticket: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  lot: number | null;
  status: "open" | "closed" | "canceled";
  opened_at: string | null;
  closed_at: string | null;
  trade_decisions: TradeDecisionRow | null;
  trade_outcomes: TradeOutcomeRow | null;
};

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

  const normalizedTrades: TradeRow[] = (trades ?? []).map((trade) => ({
    ...trade,
    trade_decisions: Array.isArray(trade.trade_decisions) ? trade.trade_decisions[0] ?? null : trade.trade_decisions,
    trade_outcomes: Array.isArray(trade.trade_outcomes) ? trade.trade_outcomes[0] ?? null : trade.trade_outcomes,
  })) as TradeRow[];

  return <OperacoesTable trades={normalizedTrades} />;
}
