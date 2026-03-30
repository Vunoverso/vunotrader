import type { SupabaseClient } from "@supabase/supabase-js";

type PlanRef = { code: string; name: string } | { code: string; name: string }[] | null;

type SubscriptionRow = {
  id: string;
  status: "trialing" | "active" | "past_due" | "canceled" | "paused";
  billing_cycle: "monthly" | "yearly";
  trial_ends_at: string | null;
  current_period_end: string | null;
  saas_plans: PlanRef;
};

export type SubscriptionAccess = {
  organizationId: string | null;
  hasActivePlan: boolean;
  isTrialing: boolean;
  trialDaysLeft: number;
  status: SubscriptionRow["status"] | "none";
  planCode: string | null;
  planName: string | null;
};

export async function getSubscriptionAccess(
  supabase: SupabaseClient,
  authUserId: string
): Promise<SubscriptionAccess> {
  const { data: profile } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", authUserId)
    .limit(1)
    .maybeSingle();

  if (!profile?.id) {
    return {
      organizationId: null,
      hasActivePlan: false,
      isTrialing: false,
      trialDaysLeft: 0,
      status: "none",
      planCode: null,
      planName: null,
    };
  }

  const { data: member } = await supabase
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profile.id)
    .limit(1)
    .maybeSingle();

  const organizationId = member?.organization_id ?? null;
  if (!organizationId) {
    return {
      organizationId: null,
      hasActivePlan: false,
      isTrialing: false,
      trialDaysLeft: 0,
      status: "none",
      planCode: null,
      planName: null,
    };
  }

  const { data: sub } = await supabase
    .from("saas_subscriptions")
    .select("id, status, billing_cycle, trial_ends_at, current_period_end, saas_plans(code, name)")
    .eq("organization_id", organizationId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const row = (sub ?? null) as SubscriptionRow | null;
  const now = Date.now();
  const trialEndsTs = row?.trial_ends_at ? new Date(row.trial_ends_at).getTime() : null;
  const trialMsLeft = trialEndsTs ? trialEndsTs - now : 0;
  const trialDaysLeft = trialMsLeft > 0 ? Math.ceil(trialMsLeft / (1000 * 60 * 60 * 24)) : 0;
  const isTrialing = row?.status === "trialing" && trialDaysLeft > 0;
  const hasActivePlan = row?.status === "active";
  const plan = Array.isArray(row?.saas_plans) ? row?.saas_plans[0] : row?.saas_plans;

  return {
    organizationId,
    hasActivePlan,
    isTrialing,
    trialDaysLeft,
    status: row?.status ?? "none",
    planCode: plan?.code ?? null,
    planName: plan?.name ?? null,
  };
}
