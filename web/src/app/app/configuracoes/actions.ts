"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

const PROFILE_AVATAR_BUCKET = process.env.NEXT_PUBLIC_SUPABASE_PROFILE_BUCKET ?? "profile-avatars";

function normalizeDocument(value: string) {
  return value.replace(/\D/g, "");
}

function sanitizeFileName(name: string) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9._-]/g, "-")
    .replace(/-+/g, "-");
}

function isValidCpf(value: string) {
  const cpf = normalizeDocument(value);
  if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i += 1) sum += Number(cpf[i]) * (10 - i);
  let check = (sum * 10) % 11;
  if (check === 10) check = 0;
  if (check !== Number(cpf[9])) return false;

  sum = 0;
  for (let i = 0; i < 10; i += 1) sum += Number(cpf[i]) * (11 - i);
  check = (sum * 10) % 11;
  if (check === 10) check = 0;
  return check === Number(cpf[10]);
}

async function getUserAndProfile() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .limit(1)
    .maybeSingle();

  if (!profile?.id) {
    throw new Error("Perfil do usuário não encontrado.");
  }

  return { user, profileId: profile.id, supabase };
}

async function getUserOrganizationId(profileId: string) {
  const admin = createAdminClient();
  const { data: memberships } = await admin
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profileId)
    .limit(20);

  const organizationIds = Array.from(new Set((memberships ?? []).map((row) => row.organization_id).filter(Boolean)));
  if (organizationIds.length === 0) {
    return null;
  }

  const { data: subscriptions } = await admin
    .from("saas_subscriptions")
    .select("organization_id, status")
    .in("organization_id", organizationIds)
    .order("created_at", { ascending: false })
    .limit(50);

  const preferred =
    (subscriptions ?? []).find((row) => row.status === "active") ??
    (subscriptions ?? []).find((row) => row.status === "trialing") ??
    null;

  return preferred?.organization_id ?? organizationIds[0] ?? null;
}

export async function updateProfileAction(formData: FormData) {
  const { profileId, supabase } = await getUserAndProfile();

  const fullName = String(formData.get("full_name") ?? "").trim();
  const phone = String(formData.get("phone") ?? "").trim() || null;
  const addressLine1 = String(formData.get("address_line1") ?? "").trim() || null;
  const addressLine2 = String(formData.get("address_line2") ?? "").trim() || null;
  const city = String(formData.get("city") ?? "").trim() || null;
  const state = String(formData.get("state") ?? "").trim() || null;
  const postalCode = String(formData.get("postal_code") ?? "").trim() || null;
  const country = String(formData.get("country") ?? "").trim() || "BR";
  const documentTypeRaw = String(formData.get("document_type") ?? "").trim().toLowerCase();
  const documentType = documentTypeRaw === "cpf" || documentTypeRaw === "rg" ? documentTypeRaw : null;
  const documentValueRaw = String(formData.get("document_value") ?? "").trim();
  const documentValue = documentValueRaw ? normalizeDocument(documentValueRaw) : null;

  const isDocumentVerified = documentType === "cpf" && documentValue ? isValidCpf(documentValue) : false;

  await supabase
    .from("user_profiles")
    .update({
      full_name: fullName,
      phone,
      address_line1: addressLine1,
      address_line2: addressLine2,
      city,
      state,
      postal_code: postalCode,
      country,
      document_type: documentType,
      document_value: documentValue,
      document_verified: isDocumentVerified,
      updated_at: new Date().toISOString(),
    })
    .eq("id", profileId);

  revalidatePath("/app/configuracoes");
  revalidatePath("/app/dashboard");
}

export async function uploadProfileAvatarAction(formData: FormData) {
  const { user, profileId } = await getUserAndProfile();
  const file = formData.get("avatar_file");
  if (!(file instanceof File) || file.size === 0) return;

  if (!file.type.startsWith("image/")) return;
  if (file.size > 5 * 1024 * 1024) return;

  const safeName = sanitizeFileName(file.name || "avatar.png");
  const objectPath = `${user.id}/${Date.now()}-${safeName}`;
  const admin = createAdminClient();

  const bytes = await file.arrayBuffer();
  const { error: uploadError } = await admin.storage
    .from(PROFILE_AVATAR_BUCKET)
    .upload(objectPath, bytes, {
      contentType: file.type,
      upsert: false,
    });

  if (uploadError) return;

  const { data: publicData } = admin.storage
    .from(PROFILE_AVATAR_BUCKET)
    .getPublicUrl(objectPath);

  await admin
    .from("user_profiles")
    .update({
      avatar_url: publicData.publicUrl,
      updated_at: new Date().toISOString(),
    })
    .eq("id", profileId);

  revalidatePath("/app/configuracoes");
  revalidatePath("/app/dashboard");
}

export async function changeEmailAction(formData: FormData) {
  const { supabase } = await getUserAndProfile();
  const newEmail = String(formData.get("new_email") ?? "").trim();
  if (!newEmail) return;

  await supabase.auth.updateUser({ email: newEmail });
  revalidatePath("/app/configuracoes");
}

export async function changePasswordAction(formData: FormData) {
  const { supabase } = await getUserAndProfile();
  const newPassword = String(formData.get("new_password") ?? "").trim();
  if (!newPassword || newPassword.length < 8) return;

  await supabase.auth.updateUser({ password: newPassword });
  revalidatePath("/app/configuracoes");
}

export async function changeMyPlanAction(formData: FormData) {
  const { profileId } = await getUserAndProfile();
  const organizationId = await getUserOrganizationId(profileId);
  if (!organizationId) return;

  const planCode = String(formData.get("plan_code") ?? "").trim().toLowerCase();
  const billingCycleRaw = String(formData.get("billing_cycle") ?? "monthly").trim().toLowerCase();
  const billingCycle = billingCycleRaw === "yearly" ? "yearly" : "monthly";
  if (!planCode) return;

  const admin = createAdminClient();
  const { data: plan } = await admin
    .from("saas_plans")
    .select("id")
    .ilike("code", planCode)
    .eq("is_active", true)
    .limit(1)
    .maybeSingle();

  if (!plan?.id) return;

  const { data: currentSub } = await admin
    .from("saas_subscriptions")
    .select("id")
    .eq("organization_id", organizationId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const start = new Date();
  const end = new Date(start);
  if (billingCycle === "yearly") end.setFullYear(end.getFullYear() + 1);
  else end.setMonth(end.getMonth() + 1);

  if (currentSub?.id) {
    await admin
      .from("saas_subscriptions")
      .update({
        plan_id: plan.id,
        status: "active",
        billing_cycle: billingCycle,
        current_period_start: start.toISOString(),
        current_period_end: end.toISOString(),
        trial_ends_at: null,
        updated_at: start.toISOString(),
      })
      .eq("id", currentSub.id);
  } else {
    await admin.from("saas_subscriptions").insert({
      organization_id: organizationId,
      plan_id: plan.id,
      status: "active",
      billing_cycle: billingCycle,
      current_period_start: start.toISOString(),
      current_period_end: end.toISOString(),
      trial_ends_at: null,
      updated_at: start.toISOString(),
    });
  }

  revalidatePath("/app/configuracoes");
  revalidatePath("/app/dashboard");
}

export async function cancelMyPlanAction() {
  const { profileId } = await getUserAndProfile();
  const organizationId = await getUserOrganizationId(profileId);
  if (!organizationId) return;

  const admin = createAdminClient();
  const { data: currentSub } = await admin
    .from("saas_subscriptions")
    .select("id")
    .eq("organization_id", organizationId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (!currentSub?.id) return;

  await admin
    .from("saas_subscriptions")
    .update({
      status: "