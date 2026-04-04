import type { SupabaseClient } from "@supabase/supabase-js";

import { createAdminClient } from "@/lib/supabase/admin";

type PlanRef = { code: string; name: string } | { code: string; name: string }[] | null;

type SubscriptionRow = {
  id: string;
  plan_id: string;
  status: "trialing" | "active" | "past_due" | "canceled" | "paused";
  billing_cycle: "monthly" | "yearly";
  trial_ends_at: string | null;
  current_period_end: string | null;
  saas_plans: PlanRef;
};

type FeatureRef = { code: string } | { code: string }[] | null;

type PlanFeatureRow = {
  is_enabled: boolean;
  saas_features: FeatureRef;
};

const KNOWN_FEATURE_CODES = [
  "robot.integrated",
  "robot.visual_hybrid",
  "robot.visual_shadow",
  "robot.visual_storage_extended",
  "robot.visual_compare",
  "ops.desktop_recovery",
] as const;

const LEGACY_PLAN_FEATURES: Record<string, string[]> = {
  starter: ["robot.integrated"],
  pro: ["robot.integrated", "robot.visual_hybrid", "robot.visual_shadow"],
  scale: [
    "robot.integrated",
    "robot.visual_hybrid",
    "robot.visual_shadow",
    "robot.visual_storage_extended",
    "robot.visual_compare",
    "ops.desktop_recovery",
  ],
};

function buildEmptyFeatures(): Record<string, boolean> {
  return KNOWN_FEATURE_CODES.reduce<Record<string, boolean>>((acc, code) => {
    acc[code] = false;
    return acc;
  }, {});
}

function inferLegacyFeatures(planCode: string | null): Record<string, boolean> {
  const features = buildEmptyFeatures();
  for (const code of LEGACY_PLAN_FEATURES[planCode ?? ""] ?? []) {
    features[code] = true;
  }
  return features;
}

async function loadPlanFeatures(planId: string | null, planCode: string | null): Promise<Record<string, boolean>> {
  const fallback = inferLegacyFeatures(planCode);
  if (!planId) {
    return fallback;
  }

  const admin = createAdminClient();
  const { data, error } = await admin
    .from("saas_plan_features")
    .select("is_enabled, saas_features(code)")
    .eq("plan_id", planId);

  if (error || !data?.length) {
    return fallback;
  }

  return (data as PlanFeatureRow[]).reduce<Record<string, boolean>>((acc, row) => {
    const feature = Array.isArray(row.saas_features) ? row.saas_features[0] : row.saas_features;
    if (feature?.code) {
      acc[feature.code] = row.is_enabled !== false;
    }
    return acc;
  }, { ...fallback });
}

export type SubscriptionAccess = {
  organizationId: string | null;
  planId: string | null;
  hasActivePlan: boolean;
  isTrialing: boolean;
  trialDaysLeft: number;
  status: SubscriptionRow["status"] | "none";
  planCode: string | null;
  planName: string | null;
  features: Record<string, boolean>;
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
      planId: null,
      hasActivePlan: false,
      isTrialing: false,
      trialDaysLeft: 0,
      status: "none",
      planCode: null,
      planName: null,
      features: buildEmptyFeatures(),
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
      planId: null,
      hasActivePlan: false,
      isTrialing: false,
      trialDaysLeft: 0,
      status: "none",
      planCode: null,
      planName: null,
      features: buildEmptyFeatures(),
    };
  }

  const { data: sub } = await supabase
    .from("saas_subscriptions")
    .select("id, plan_id, status, billing_cycle, trial_ends_at, current_period_end, saas_plans(code, name)")
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
  const features = await loadPlanFeatures(row?.plan_id ?? null, plan?.code ?? null);

  return {
    organizationId,
    planId: row?.plan_id ?? null,
    hasActivePlan,
    isTrialing,
    trialDaysLeft,
    status: row?.status ?? "none",
    planCode: plan?.code ?? null,
    planName: plan?.name ?? null,
    features,
  };
}
