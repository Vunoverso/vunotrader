import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import DashboardShell from "@/components/app/dashboard-shell";

function isDynamicServerError(error: unknown) {
  return !!(
    error &&
    typeof error === "object" &&
    "digest" in error &&
    (error as { digest?: string }).digest === "DYNAMIC_SERVER_USAGE"
  );
}

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let supabase;
  try {
    supabase = await createClient();
  } catch (err) {
    if (isDynamicServerError(err)) {
      throw err;
    }
    console.error("[AppLayout] Falha ao criar cliente Supabase:", err);
    return (
      <div className="flex min-h-screen items-center justify-center p-8 text-center text-sm text-slate-400">
        Serviço temporariamente indisponível. Verifique a configuração do ambiente e tente novamente.
      </div>
    );
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  const isAdmin = user.user_metadata?.is_admin === true;
  let access;
  try {
    access = await getSubscriptionAccess(supabase, user.id);
  } catch (err) {
    if (isDynamicServerError(err)) {
      throw err;
    }
    console.error("[AppLayout] Falha ao carregar assinatura:", err);
    access = {
      organizationId: null,
      planId: null,
      hasActivePlan: false,
      isTrialing: false,
      trialDaysLeft: 0,
      status: "none",
      planCode: null,
      planName: null,
      features: {},
    };
  }

  // Status real do motor: busca último heartbeat da instância do usuário
  let profileRow: { id: string } | null = null;
  let robotRow: { name?: string | null; last_seen_at?: string | null } | null = null;

  try {
    const { data } = await supabase
      .from("user_profiles")
      .select("id")
      .eq("auth_user_id", user.id)
      .limit(1)
      .maybeSingle();
    profileRow = data;
  } catch (err) {
    if (isDynamicServerError(err)) {
      throw err;
    }
    console.error("[AppLayout] Falha ao carregar profile:", err);
  }

  if (profileRow) {
    try {
      const { data } = await supabase
        .from("robot_instances")
        .select("name, last_seen_at")
        .eq("profile_id", profileRow.id)
        .eq("status", "active")
        .order("last_seen_at", { ascending: false, nullsFirst: false })
        .limit(1)
        .maybeSingle();
      robotRow = data;
    } catch (err) {
      if (isDynamicServerError(err)) {
        throw err;
      }
      console.error("[AppLayout] Falha ao carregar robot_instances:", err);
    }
  }

  return (
    <DashboardShell
      isAdmin={isAdmin}
      hasActivePlan={access.hasActivePlan}
      userEmail={user.email}
      lastSeenAt={robotRow?.last_seen_at || null}
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
