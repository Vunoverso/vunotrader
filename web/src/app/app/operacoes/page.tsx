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

type RawTradeOutcome = {
  result: "win" | "loss" | "breakeven";
  pnl_money: number | null;
  pnl_points: number | null;
  win_loss_reason: string | null;
};

type RawExecutedTrade = {
  id: string;
  broker_ticket: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  lot: number | null;
  status: "open" | "closed" | "canceled";
  opened_at: string | null;
  closed_at: string | null;
  trade_outcomes: RawTradeOutcome[] | null;
};

type RawDecision = TradeDecisionRow & {
  id: string;
  created_at: string;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  outcome_status: "pending" | "executing" | "win" | "loss" | "breakeven" | "neutral" | null;
  outcome_profit: number | null;
  outcome_pips: number | null;
  post_analysis: string | null;
  closed_at: string | null;
  executed_trades: RawExecutedTrade[] | null;
};

function mapDecisionResult(status: RawDecision["outcome_status"]): TradeOutcomeRow["result"] | null {
  if (status === "win" || status === "loss" || status === "breakeven") return status;
  if (status === "neutral") return "breakeven";
  return null;
}

function mapDecisionStatus(status: RawDecision["outcome_status"]): TradeRow["status"] {
  if (status === "win" || status === "loss" || status === "breakeven" || status === "neutral") return "closed";
  return "open";
}

export default async function OperacoesPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="Operacoes" />;
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
      rationale,
      mode,
      created_at,
      entry_price,
      stop_loss,
      take_profit,
      outcome_status,
      outcome_profit,
      outcome_pips,
      post_analysis,
      closed_at,
      executed_trades (
        id,
        broker_ticket,
        entry_price,
        stop_loss,
        take_profit,
        lot,
        status,
        opened_at,
        closed_at,
        trade_outcomes (
          result,
          pnl_money,
          pnl_points,
          win_loss_reason
        )
      )
    `)
    .eq("user_id", user.id)
    .neq("side", "hold")
    .order("created_at", { ascending: false })
    .limit(120);

  const normalizedTrades: TradeRow[] = ((decisions ?? []) as RawDecision[]).map((decision) => {
    const executedTrade = Array.isArray(decision.executed_trades) ? decision.executed_trades[0] ?? null : null;
    const executedOutcome = Array.isArray(executedTrade?.trade_outcomes)
      ? executedTrade.trade_outcomes[0] ?? null
      : null;

    const decisionResult = mapDecisionResult(decision.outcome_status);
    const fallbackOutcome: TradeOutcomeRow | null = decisionResult
      ? {
          result: decisionResult,
          pnl_money: decision.outcome_profit ?? null,
          pnl_points: decision.outcome_pips ?? null,
          win_loss_reason: decision.post_analysis ?? null,
        }
      : null;

    return {
      id: executedTrade?.id ?? decision.id,
      broker_ticket: executedTrade?.broker_ticket ?? null,
      entry_price: executedTrade?.entry_price ?? decision.entry_price,
      stop_loss: executedTrade?.stop_loss ?? decision.stop_loss,
      take_profit: executedTrade?.take_profit ?? decision.take_profit,
      lot: executedTrade?.lot ?? null,
      status: executedTrade?.status ?? mapDecisionStatus(decision.outcome_status),
      opened_at: executedTrade?.opened_at ?? decision.created_at,
      closed_at: executedTrade?.closed_at ?? decision.closed_at,
      trade_decisions: {
        symbol: decision.symbol,
        timeframe: decision.timeframe,
        side: decision.side,
        confidence: decision.confidence,
        risk_pct: decision.risk_pct,
        rationale: decision.rationale,
        mode: decision.mode,
      },
      trade_outcomes: executedOutcome
        ? {
            result: executedOutcome.result,
            pnl_money: executedOutcome.pnl_money,
            pnl_points: executedOutcome.pnl_points,
            win_loss_reason: executedOutcome.win_loss_reason,
          }
        : fallbackOutcome,
    };
  });

  return <OperacoesTable trades={normalizedTrades} />;
}
