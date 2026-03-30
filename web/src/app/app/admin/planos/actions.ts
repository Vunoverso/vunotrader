"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

async function assertAdmin() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user?.user_metadata?.is_admin !== true) {
    redirect("/app/dashboard");
  }

  return user?.id;
}

async function logPlanChange(
  planId: string,
  changeType: "price_update" | "limit_update" | "status_change" | "plan_created",
  fieldName: string,
  newValue: string,
  oldValue?: string | null,
  userId?: string
) {
  const admin = createAdminClient();
  await admin.from("plan_changes").insert({
    plan_id: planId,
    change_type: changeType,
    field_name: fieldName,
    old_value: oldValue ?? null,
    new_value: newValue,
    changed_by: userId ?? null,
  });
}

export async function createPlanAction(formData: FormData) {
  const userId = await assertAdmin();

  const code = typeof formData.get("code") === "string" ? (formData.get("code") as string).trim().toLowerCase() : "";
  const name = typeof formData.get("name") === "string" ? (formData.get("name") as string).trim() : "";
  const description = typeof formData.get("description") === "string" ? (formData.get("description") as string).trim() : null;
  const monthlyPrice = parseNullableNumber(formData.get("monthly_price"));
  const yearlyPrice = parseNullableNumber(formData.get("yearly_price"));

  if (!code || !name || monthlyPrice == null) return;

  const admin = createAdminClient();

  const { data: newPlan } = await admin
    .from("saas_plans")
    .insert({
      code,
      name,
      description,
      monthly_price: monthlyPrice,
      yearly_price: yearlyPrice,
      is_active: true,
    })
    .select("id")
    .single();

  if (newPlan?.id) {
    // Log plan creation
    await logPlanChange(newPlan.id, "plan_created", "name", name, undefined, userId);
    await logPlanChange(newPlan.id, "price_update", "monthly_price", monthlyPrice.toString(), undefined, userId);
    if (yearlyPrice) {
      await logPlanChange(newPlan.id, "price_update", "yearly_price", yearlyPrice.toString(), undefined, userId);
    }

    const maxUsersLimit = parseNullableInt(formData.get("max_users"));
    const maxTradesLimit = parseNullableInt(formData.get("max_trades_per_month"));
    const maxTokensLimit = parseNullableInt(formData.get("max_ai_tokens_per_day"));
    const maxStorageLimit = parseNullableNumber(formData.get("max_storage_gb"));
    const maxBotsLimit = parseNullableInt(formData.get("max_bots"));

    await admin.from("saas_plan_limits").insert({
      plan_id: newPlan.id,
      max_users: maxUsersLimit,
      max_trades_per_month: maxTradesLimit,
      max_ai_tokens_per_day: maxTokensLimit,
      max_storage_gb: maxStorageLimit,
      max_bots: maxBotsLimit,
    });

    // Log limit updates
    if (maxUsersLimit) await logPlanChange(newPlan.id, "limit_update", "max_users", maxUsersLimit.toString(), undefined, userId);
    if (maxTradesLimit) await logPlanChange(newPlan.id, "limit_update", "max_trades_per_month", maxTradesLimit.toString(), undefined, userId);
    if (maxTokensLimit) await logPlanChange(newPlan.id, "limit_update", "max_ai_tokens_per_day", maxTokensLimit.toString(), undefined, userId);
    if (maxStorageLimit) await logPlanChange(newPlan.id, "limit_update", "max_storage_gb", maxStorageLimit.toString(), undefined, userId);
    if (maxBotsLimit) await logPlanChange(newPlan.id, "limit_update", "max_bots", maxBotsLimit.toString(), undefined, userId);
  }

  revalidatePath("/app/admin/planos");
  revalidatePath("/app/admin/planos/historico");
}

function parseNullableNumber(value: FormDataEntryValue | null) {
  if (typeof value !== "string") return null;
  const normalized = value.trim().replace(",", ".");
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseNullableInt(value: FormDataEntryValue | null) {
  const parsed = parseNullableNumber(value);
  return parsed == null ? null : Math.trunc(parsed);
}

export async function updatePlanAction(formData: FormData) {
  const userId = await assertAdmin();

  const planId = formData.get("plan_id");
  if (typeof planId !== "string" || !planId) return;

  const admin = createAdminClient();

  const name = typeof formData.get("name") === "string" ? (formData.get("name") as string).trim() : "";
  const description = typeof formData.get("description") === "string" ? (formData.get("description") as string).trim() : null;
  const monthlyPrice = parseNullableNumber(formData.get("monthly_price"));
  const yearlyPrice = parseNullableNumber(formData.get("yearly_price"));
  const isActive = formData.get("is_active") === "true";

  if (!name || monthlyPrice == null) return;

  // Get current plan details to compare
  const { data: currentPlan } = await admin
    .from("saas_plans")
    .select("monthly_price, yearly_price, is_active")
    .eq("id", planId)
    .single();

  // Update plan
  await admin
    .from("saas_plans")
    .update({
      name,
      description,
      monthly_price: monthlyPrice,
      yearly_price: yearlyPrice,
      is_active: isActive,
    })
    .eq("id", planId);

  // Log changes
  if (currentPlan?.monthly_price !== monthlyPrice) {
    await logPlanChange(planId, "price_update", "monthly_price", monthlyPrice.toString(), currentPlan?.monthly_price?.toString(), userId);
  }
  if (currentPlan?.yearly_price !== yearlyPrice) {
    await logPlanChange(planId, "price_update", "yearly_price", (yearlyPrice ?? "").toString(), (currentPlan?.yearly_price ?? "").toString(), userId);
  }
  if (currentPlan?.is_active !== isActive) {
    await logPlanChange(planId, "status_change", "is_active", isActive.toString(), currentPlan?.is_active?.toString(), userId);
  }

  const limitsPayload = {
    plan_id: planId,
    max_users: parseNullableInt(formData.get("max_users")),
    max_trades_per_month: parseNullableInt(formData.get("max_trades_per_month")),
    max_ai_tokens_per_day: parseNullableInt(formData.get("max_ai_tokens_per_day")),
    max_storage_gb: parseNullableNumber(formData.get("max_storage_gb")),
    max_bots: parseNullableInt(formData.get("max_bots")),
  };

  const { data: currentLimits } = await admin
    .from("saas_plan_limits")
    .select("id, max_users, max_trades_per_month, max_ai_tokens_per_day, max_storage_gb, max_bots")
    .eq("plan_id", planId)
    .limit(1)
    .maybeSingle();

  if (currentLimits?.id) {
    await admin.from("saas_plan_limits").update(limitsPayload).eq("id", currentLimits.id);

    // Log limit changes
    if (currentLimits.max_users !== limitsPayload.max_users) {
      await logPlanChange(planId, "limit_update", "max_users", (limitsPayload.max_users ?? "").toString(), (currentLimits.max_users ?? "").toString(), userId);
    }
    if (currentLimits.max_trades_per_month !== limitsPayload.max_trades_per_month) {
      await logPlanChange(planId, "limit_update", "max_trades_per_month", (limitsPayload.max_trades_per_month ?? "").toString(), (currentLimits.max_trades_per_month ?? "").toString(), userId);
    }
    if (currentLimits.max_ai_tokens_per_day !== limitsPayload.max_ai_tokens_per_day) {
      await logPlanChange(planId, "limit_update", "max_ai_tokens_per_day", (limitsPayload.max_ai_tokens_per_day ?? "").toString(), (currentLimits.max_ai_tokens_per_day ?? "").toString(), userId);
    }
    if (currentLimits.max_storage_gb !== limitsPayload.max_storage_gb) {
      await logPlanChange(planId, "limit_update", "max_storage_gb", (limitsPayload.max_storage_gb ?? "").toString(), (currentLimits.max_storage_gb ?? "").toString(), userId);
    }
    if (currentLimits.max_bots !== limitsPayload.max_bots) {
      await logPlanChange(planId, "limit_update", "max_bots", (limitsPayload.max_bots ?? "").toString(), (currentLimits.max_bots ?? "").toString(), userId);
    }
  } else {
    await admin.from("saas_plan_limits").insert(limitsPayload);

    // Log new limits
    if (limitsPayload.max_users) await logPlanChange(planId, "limit_update", "max_users", limitsPayload.max_users.toString(), undefined, userId);
    if (limitsPayload.max_trades_per_month) await logPlanChange(planId, "limit_update", "max_trades_per_month", limitsPayload.max_trades_per_month.toString(), undefined, userId);
    if (limitsPayload.max_ai_tokens_per_day) await logPlanChange(planId, "limit_update", "max_ai_tokens_per_day", limitsPayload.max_ai_tokens_per_day.toString(), undefined, userId);
    if (limitsPayload.max_storage_gb) await logPlanChange(planId, "limit_update", "max_storage_gb", limitsPayload.max_storage_gb.toString(), undefined, userId);
    if (limitsPayload.max_bots) await logPlanChange(planId, "limit_update", "max_bots", limitsPayload.max_bots.toString(), undefined, userId);
  }

  revalidatePath("/app/admin");
  revalidatePath("/app/admin/planos");
  revalidatePath("/app/admin/planos/historico");
  revalidatePath("/app/admin/usuarios");
}