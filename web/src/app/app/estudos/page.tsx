import EstudosManager, { type EstudoItem } from "@/components/app/estudos-manager";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import PlanGateCard from "@/components/app/plan-gate-card";

export default async function EstudosPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const access = await getSubscriptionAccess(supabase, user.id);
  if (!access.hasActivePlan) {
    return <PlanGateCard moduleName="Estudos" />;
  }

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

  let initialItems: EstudoItem[] = [];

  if (organizationId) {
    const { data: materials } = await supabase
      .from("study_materials")
      .select("id, title, material_type, source_url, storage_path, summary, processing_status, processing_error, processed_at, created_at")
      .eq("organization_id", organizationId)
      .order("created_at", { ascending: false })
      .limit(100);

    initialItems = (materials ?? []) as EstudoItem[];
  }

  return (
    <EstudosManager
      userId={user.id}
      organizationId={organizationId}
      initialItems={initialItems}
    />
  );
}
