import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import AppSidebar from "@/components/app/app-sidebar";
import { getSubscriptionAccess } from "@/lib/subscription-access";

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
        .order("last_seen_at", { ascending: false })
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
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Sidebar fixa */}
      <AppSidebar isAdmin={isAdmin} hasActivePlan={access.hasActivePlan} />

      {/* Conteúdo principal */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-900 px-6 shrink-0">
          <div className="text-xs text-slate-400">
            {access.hasActivePlan ? (
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-emerald-300">Plano ativo</span>
            ) : access.isTrialing ? (
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-amber-300">Trial: {access.trialDaysLeft} dia(s)</span>
            ) : (
              <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-slate-400">Sem plano ativo</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {/* Status do motor */}
            <div className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${
              motorOnline
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "border-slate-700 bg-slate-800 text-slate-400"
            }`}>
              <span className={`h-2 w-2 rounded-full ${motorOnline ? "bg-emerald-400 animate-pulse" : "bg-slate-600"}`} />
              {motorLabel}
            </div>
            {/* Avatar / email */}
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-600/20 text-sky-400 text-xs font-bold select-none">
              {user.email?.[0]?.toUpperCase() ?? "U"}
            </div>
          </div>
        </header>

        {/* Área de scroll */}
        <main className="flex-1 overflow-y-auto p-6 bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
}
