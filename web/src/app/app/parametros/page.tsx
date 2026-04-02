import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";
import ParametrosForm, { type ParametrosData } from "@/components/app/parametros-form";

export default async function ParametrosPage() {
  const supabase = await createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="Parâmetros" />;
  }

  // Busca o profile para obter o organization_id
  const { data: profile } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .single();

  let organizationId: string | null = null;
  if (profile) {
    const { data: member } = await supabase
      .from("organization_members")
      .select("organization_id")
      .eq("profile_id", profile.id)
      .limit(1)
      .single();
    organizationId = member?.organization_id ?? null;
  }

  // Busca os parâmetros existentes
  const { data: params } = await supabase
    .from("user_parameters")
    .select("*")
    .eq("user_id", user.id)
    .limit(1)
    .single();

  const initial: ParametrosData | null = params
    ? {
        id: params.id,
        organization_id: params.organization_id,
        mode: params.mode,
        capital_usd: params.capital_usd?.toString() ?? "10000",
        daily_profit_target: params.daily_profit_target?.toString() ?? "",
        weekly_profit_target: params.weekly_profit_target?.toString() ?? "",
        monthly_profit_target: params.monthly_profit_target?.toString() ?? "",
        daily_loss_limit: params.daily_loss_limit?.toString() ?? "",
        max_drawdown_pct: params.max_drawdown_pct?.toString() ?? "",
        risk_per_trade_pct: params.risk_per_trade_pct?.toString() ?? "",
        per_trade_stop_loss_mode: params.per_trade_stop_loss_mode ?? "atr",
        per_trade_stop_loss_value: params.per_trade_stop_loss_value?.toString() ?? "2",
        per_trade_take_profit_rr: params.per_trade_take_profit_rr?.toString() ?? "2",
        max_trades_per_day: params.max_trades_per_day?.toString() ?? "",
        trading_start_time: params.trading_start_time ?? "09:00",
        trading_end_time: params.trading_end_time ?? "17:30",
        allowed_symbols: Array.isArray(params.allowed_symbols)
          ? params.allowed_symbols.join(", ")
          : "",
        max_consecutive_losses: params.max_consecutive_losses?.toString() ?? "3",
        drawdown_pause_pct: params.drawdown_pause_pct?.toString() ?? "5",
        auto_reduce_risk: params.auto_reduce_risk ?? true,
      }
    : null;

  // Busca a instância do robô para obter o saldo atual (sincronizado via MT5)
  const { data: robotInstance } = await supabase
    .from("robot_instances")
    .select("current_balance")
    .eq("user_id", user.id)
    .order("last_seen_at", { ascending: false })
    .limit(1)
    .single();

  return (
    <ParametrosForm
      initial={initial}
      userId={user.id}
      organizationId={organizationId}
      currentBalance={robotInstance?.current_balance}
    />
  );
}
