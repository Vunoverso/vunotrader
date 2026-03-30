from app.core.supabase import get_service_supabase

DECISION_ID = "4a36f246-df0f-46a5-8598-f34a36afb5c9"

sb = get_service_supabase()

decision = (
    sb.table("trade_decisions")
    .select("id,trade_id,user_id,organization_id,symbol,timeframe,side,confidence,risk_pct,created_at")
    .eq("id", DECISION_ID)
    .execute()
    .data
)

executed = (
    sb.table("executed_trades")
    .select("id,trade_decision_id,broker_ticket,status,entry_price,stop_loss,take_profit,lot,opened_at,closed_at")
    .eq("trade_decision_id", DECISION_ID)
    .execute()
    .data
)

outcome = []
if executed:
    outcome = (
        sb.table("trade_outcomes")
        .select("id,executed_trade_id,result,pnl_money,pnl_points,win_loss_reason,created_at")
        .eq("executed_trade_id", executed[0]["id"])
        .execute()
        .data
    )

print("DECISION", decision)
print("EXECUTED", executed)
print("OUTCOME", outcome)
