"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

const ORG_ROLES = ["owner", "admin", "analyst", "viewer"] as const;
type OrgRole = (typeof ORG_ROLES)[number];

function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
}

// ── Guard: apenas admins podem executar estas actions ─────────
async function assertAdmin() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (user?.user_metadata?.is_admin !== true) redirect("/app/dashboard");
}

// ── Tornar/remover admin ──────────────────────────────────────
export async function toggleAdminAction(formData: FormData) {
  await assertAdmin();

  const authUserId = formData.get("auth_user_id") as string;
  const makeAdmin  = formData.get("make_admin") === "true";

  if (!authUserId) return;

  const admin = createAdminClient();
  await admin.auth.admin.updateUserById(authUserId, {
    user_metadata: { is_admin: makeAdmin },
  });

  revalidatePath("/app/admin/usuarios");
}

// ── Bloquear/desbloquear conta ────────────────────────────────
export async function banUserAction(formData: FormData) {
  await assertAdmin();

  const authUserId = formData.get("auth_user_id") as string;
  const ban        = formData.get("ban") === "true";

  if (!authUserId) return;

  const admin = createAdminClient();
  // "87600h" ≈ 10 anos (bloqueio permanente prático); "none" = desbloquear
  await admin.auth.admin.updateUserById(authUserId, {
    ban_duration: ban ? "87600h" : "none",
  });

  revalidatePath("/app/admin/usuarios");
}

// ── Remover conta ─────────────────────────────────────────────
export async function deleteUserAction(formData: FormData) {
  await assertAdmin();

  const authUserId = formData.get("auth_user_id") as string;
  if (!authUserId) return;

  const admin = createAdminClient();
  await admin.auth.admin.deleteUser(authUserId);

  revalidatePath("/app/admin/usuarios");
}

// ── Trocar plano da organização ─────────────────────────────
export async function changePlanAction(formData: FormData) {
  await assertAdmin();

  const organizationId = formData.get("organization_id") as string;
  const planCodeRaw    = formData.get("plan_code") as string;
  const billingCycle   = ((formData.get("billing_cycle") as string) || "monthly") as "monthly" | "yearly";

  if (!organizationId || !planCodeRaw) return;

  const planCode = planCodeRaw.trim().toLowerCase();
  const admin = createAdminClient();

  const { data: plan } = await admin
    .from("saas_plans")
    .select("id")
    .ilike("code", planCode)
    .eq("is_active", true)
    .limit(1)
    .maybeSingle();

  if (!plan?.id) return;

  const { data: sub } = await admin
    .from("saas_subscriptions")
    .select("id")
    .eq("organization_id", organizationId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (sub?.id) {
    await admin
      .from("saas_subscriptions")
      .update({
        plan_id: plan.id,
        status: "active",
        billing_cycle: billingCycle,
        updated_at: new Date().toISOString(),
      })
      .eq("id", sub.id);
  } else {
    const start = new Date();
    const end = new Date(start);
    if (billingCycle === "yearly") end.setFullYear(end.getFullYear() + 1);
    else end.setMonth(end.getMonth() + 1);

    await admin.from("saas_subscriptions").insert({
      organization_id: organizationId,
      plan_id: plan.id,
      status: "active",
      billing_cycle: billingCycle,
      current_period_start: start.toISOString(),
      current_period_end: end.toISOString(),
      updated_at: start.toISOString(),
    });
  }

  revalidatePath("/app/admin/usuarios");
}

// ── Trocar ciclo mensal/anual ───────────────────────────────
export async function changeBillingCycleAction(formData: FormData) {
  await assertAdmin();

  const organizationId = formData.get("organization_id") as string;
  const billingCycle = ((formData.get("billing_cycle") as string) || "monthly") as "monthly" | "yearly";

  if (!organizationId || !["monthly", "yearly"].includes(billingCycle)) return;

  const admin = createAdminClient();

  const { data: sub } = await admin
    .from("saas_subscriptions")
    .select("id")
    .eq("organization_id", organizationId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!sub?.id) return;

  const start = new Date();
  const end = new Date(start);
  if (billingCycle === "yearly") end.setFullYear(end.getFullYear() + 1);
  else end.setMonth(end.getMonth() + 1);

  await admin
    .from("saas_subscriptions")
    .update({
      billing_cycle: billingCycle,
      current_period_start: start.toISOString(),
      current_period_end: end.toISOString(),
      updated_at: start.toISOString(),
    })
    .eq("id", sub.id);

  revalidatePath("/app/admin/usuarios");
}

// ── Criar organização e vincular usuário ──────────────────────
export async function createOrganizationForUserAction(formData: FormData) {
  await assertAdmin();

  const profileId = formData.get("profile_id") as string;
  const orgNameRaw = (formData.get("org_name") as string) || "Organização";

  if (!profileId) return;

  const admin = createAdminClient();

  const { data: currentMembership } = await admin
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profileId)
    .limit(1)
    .maybeSingle();

  if (currentMembership?.organization_id) {
    revalidatePath("/app/admin/usuarios");
    return;
  }

  const orgName = orgNameRaw.trim() || "Organização";
  const uniqueSuffix = Date.now().toString().slice(-6);
  const slug = `${slugify(orgName) || "org"}-${uniqueSuffix}`;

  const { data: org } = await admin
    .from("organizations")
    .insert({
      name: orgName,
      slug,
      owner_profile_id: profileId,
      updated_at: new Date().toISOString(),
    })
    .select("id")
    .single();

  if (!org?.id) return;

  await admin
    .from("organization_members")
    .insert({
      organization_id: org.id,
      profile_id: profileId,
      role: "owner",
    });

  revalidatePath("/app/admin/usuarios");
}

// ── Trocar papel na organização ─────────────────────────────
export async function updateMemberRoleAction(formData: FormData) {
  await assertAdmin();

  const organizationId = formData.get("organization_id") as string;
  const profileId = formData.get("profile_id") as string;
  const role = (formData.get("role") as string) as OrgRole;

  if (!organizationId || !profileId || !ORG_ROLES.includes(role)) return;

  const admin = createAdminClient();

  const { data: current } = await admin
    .from("organization_members")
    .select("role")
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId)
    .maybeSingle();

  if (!current?.role) return;

  // Impede remover o último owner via troca de role
  if (current.role === "owner" && role !== "owner") {
    const { count: owners } = await admin
      .from("organization_members")
      .select("profile_id", { count: "exact", head: true })
      .eq("organization_id", organizationId)
      .eq("role", "owner");

    if ((owners ?? 0) <= 1) return;
  }

  await admin
    .from("organization_members")
    .update({ role })
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId);

  // Mantém owner_profile_id sincronizado quando promove para owner
  if (role === "owner") {
    await admin
      .from("organizations")
      .update({ owner_profile_id: profileId, updated_at: new Date().toISOString() })
      .eq("id", organizationId);
  }

  revalidatePath("/app/admin/usuarios");
}

// ── Remover usuário da organização ───────────────────────────
export async function removeUserFromOrganizationAction(formData: FormData) {
  await assertAdmin();

  const organizationId = formData.get("organization_id") as string;
  const profileId = formData.get("profile_id") as string;

  if (!organizationId || !profileId) return;

  const admin = createAdminClient();

  const { data: current } = await admin
    .from("organization_members")
    .select("role")
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId)
    .maybeSingle();

  if (!current?.role) return;

  // Não permite remover o último owner
  if (current.role === "owner") {
    const { count: owners } = await admin
      .from("organization_members")
      .select("profile_id", { count: "exact", head: true })
      .eq("organization_id", organizationId)
      .eq("role", "owner");

    if ((owners ?? 0) <= 1) return;
  }

  await admin
    .from("organization_members")
    .delete()
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId);

  const { data: org } = await admin
    .from("organizations")
    .select("owner_profile_id")
    .eq("id", organizationId)
    .maybeSingle();

  if (org?.owner_profile_id === profileId) {
    const { data: nextOwner } = await admin
      .from("organization_members")
      .select("profile_id")
      .eq("organization_id", organizationId)
      .eq("role", "owner")
      .limit(1)
      .maybeSingle();

    await admin
      .from("organizations")
      .update({ owner_profile_id: nextOwner?.profile_id ?? null, updated_at: new Date().toISOString() })
      .eq("id", organizationId);
  }

  revalidatePath("/app/admin/usuarios");
}
