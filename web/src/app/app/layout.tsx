import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import DashboardShell from "@/components/app/dashboard-shell";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  const isAdmin = user.user_metadata?.is_admin === true;
  const access = await getSubscriptionAccess(supabase, user.id);

  // Status real do motor: busca último heartbeat da instância do usuário
  const { data: profileRow } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .limit(1)
    .maybeSingle();

  const { data: robotRow } = profileRow
    ? await supabase
        .from("robot_instances")
        .select("name, last_seen_at")
        .eq("profile_id", profileRow.id)
        .eq("status", "active")
        .order("last_seen_at", { ascending: false, nullsFirst: false })
        .limit(1)
        .maybeSingle()
    : { data: null };

  const motorOnline = (() => {
    if (!robotRow?.last_seen_at) return false;
    return (new Date().getTime() - new Date(robotRow.last_seen_at).getTime()) < 5 * 60 * 1000;
  })();

  const motorLabel = (() => {
    if (!robotRow?.last_seen_at || !motorOnline) return "Motor desconectado";
    const diffMin = Math.floor((new Date().getTime() - new Date(robotRow.last_seen_at).getTime()) / 60000);
    const timeStr = diffMin < 1 ? "agora" : `há ${diffMin} min`;
    return `Motor ativo · ${timeStr}`;
  })();

  return (
    <DashboardShell
      isAdmin={isAdmin}
      hasActivePlan={access.hasActivePlan}
      userEmail={user.email}
      motorOnline={motorOnline}
      motorLabel={motorLabel}
      subscriptionAccess={{
        hasActivePlan: access.hasActivePlan,
        isTrialing: access.isTrialing,
        trialDaysLeft: access.trialDaysLeft ?? 0,
      }}
    >
      {children}
    </DashboardShell>
  );
}
