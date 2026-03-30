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
            {/* Status do robô */}
            <div className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-400">
              <span className="h-2 w-2 rounded-full bg-slate-600" />
              Robô inativo
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
