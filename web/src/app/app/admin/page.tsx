import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

// ── Tipos internos ────────────────────────────────────────────
type PlanDist = { name: string; count: number; color: string; price: number };
type RecentUser = { id: string; name: string; email: string; plan: string; createdAt: string; status: string };
type RobotInstanceRow = {
  id: string;
  name: string;
  status: string;
  allowed_modes: string[];
  real_trading_enabled: boolean;
  last_seen_at: string | null;
  organization_id: string;
  orgName: string;
};

// ── Componentes internos ──────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon,
  accent = "slate",
  trend,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
  accent?: "green" | "sky" | "violet" | "amber" | "slate";
  trend?: { value: string; up: boolean };
}) {
  const bg: Record<string, string> = {
    green:  "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    sky:    "bg-sky-500/10 text-sky-400 border-sky-500/20",
    violet: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    amber:  "bg-amber-500/10 text-amber-400 border-amber-500/20",
    slate:  "bg-slate-700 text-slate-400 border-slate-600",
  };
  const val: Record<string, string> = {
    green:  "text-emerald-300",
    sky:    "text-sky-300",
    violet: "text-violet-300",
    amber:  "text-amber-300",
    slate:  "text-slate-200",
  };
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-start justify-between">
        <div className={`flex h-10 w-10 items-center justify-center rounded-lg border ${bg[accent]}`}>
          {icon}
        </div>
        {trend && (
          <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${trend.up ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
            {trend.up ? "▲" : "▼"} {trend.value}
          </span>
        )}
      </div>
      <p className="mt-4 text-xs text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold font-mono tracking-tight ${val[accent]}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-600">{sub}</p>}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-4 text-sm font-semibold uppercase tracking-widest text-slate-500">
      {children}
    </h2>
  );
}

function StatusDot({ active }: { active: boolean }) {
  return (
    <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
      {active && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${active ? "bg-emerald-400" : "bg-slate-600"}`} />
    </span>
  );
}

function PlanBadge({ plan }: { plan: string }) {
  const map: Record<string, string> = {
    Starter: "bg-slate-700 text-slate-300 border-slate-600",
    Pro:     "bg-sky-500/20 text-sky-300 border-sky-500/30",
    Scale:   "bg-violet-500/20 text-violet-300 border-violet-500/30",
    Trial:   "bg-amber-500/20 text-amber-300 border-amber-500/30",
  };
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${map[plan] ?? map.Starter}`}>
      {plan}
    </span>
  );
}

function SystemCard({
  title,
  connected,
  description,
  detail,
}: {
  title: string;
  connected: boolean;
  description: string;
  detail?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-slate-200">{title}</p>
        <span className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${connected ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" : "border-slate-700 bg-slate-800 text-slate-500"}`}>
          <StatusDot active={connected} />
          {connected ? "Online" : "Offline"}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-slate-500">{description}</p>
      {detail && <p className="mt-2 font-mono text-[11px] text-slate-600">{detail}</p>}
    </div>
  );
}

// ── Página ────────────────────────────────────────────────────
export default async function AdminPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  // Proteção: apenas usuários com is_admin=true no user_metadata têm acesso
  const isAdmin = user?.user_metadata?.is_admin === true;
  if (!isAdmin) redirect("/app/dashboard");

  // ── Dados reais: total de perfis ──────────────────────────
  const adminClient = createAdminClient();

  const { count: totalUsers } = await adminClient
    .from("user_profiles")
    .select("id", { count: "exact", head: true });

  const { count: totalOrgs } = await adminClient
    .from("organizations")
    .select("id", { count: "exact", head: true });

  const { count: activeSubs } = await adminClient
    .from("saas_subscriptions")
    .select("id", { count: "exact", head: true })
    .eq("status", "active");

  // Últimos 5 usuários cadastrados
  const { data: recentProfiles } = await adminClient
    .from("user_profiles")
    .select("id, full_name, email, created_at")
    .order("created_at", { ascending: false })
    .limit(8);

  // Subscrições com plano
  const { data: subsByPlan } = await adminClient
    .from("saas_subscriptions")
    .select("status, saas_plans(name, monthly_price)")
    .eq("status", "active");

  // Uso de IA hoje
  const today = new Date().toISOString().slice(0, 10);
  const { data: aiToday } = await adminClient
    .from("ai_usage_logs")
    .select("total_tokens, estimated_cost")
    .gte("created_at", today);

  // Robot instances: todas as instâncias, cruzando nome da org
  const { data: robotsRaw } = await adminClient
    .from("robot_instances")
    .select("id, name, status, allowed_modes, real_trading_enabled, last_seen_at, organization_id")
    .order("last_seen_at", { ascending: false, nullsFirst: false })
    .limit(50);

  const { data: orgsForRobots } = await adminClient
    .from("organizations")
    .select("id, name");

  const orgNameById: Record<string, string> = {};
  (orgsForRobots ?? []).forEach((o: { id: string; name: string }) => {
    orgNameById[o.id] = o.name;
  });

  const nowMs = new Date().getTime();
  const robotInstances: RobotInstanceRow[] = (robotsRaw ?? []).map((r) => ({
    id: r.id,
    name: r.name,
    status: r.status,
    allowed_modes: r.allowed_modes ?? ["demo"],
    real_trading_enabled: r.real_trading_enabled ?? false,
    last_seen_at: r.last_seen_at,
    organization_id: r.organization_id,
    orgName: orgNameById[r.organization_id] ?? "—",
  }));

  // Classificar status de atividade
  function robotActivityStatus(lastSeen: string | null): "active" | "sleeping" | "offline" {
    if (!lastSeen) return "offline";
    const diffMin = (nowMs - new Date(lastSeen).getTime()) / 60000;
    if (diffMin < 5) return "active";
    if (diffMin < 60) return "sleeping";
    return "offline";
  }

  const totalTokensToday = aiToday?.reduce((acc, r) => acc + (r.total_tokens ?? 0), 0) ?? 0;
  const totalAiCostToday = aiToday?.reduce((acc, r) => acc + Number(r.estimated_cost ?? 0), 0) ?? 0;

  // ── Calcular métricas ─────────────────────────────────────
  const planCounts: Record<string, { count: number; price: number }> = {};
  // O Supabase retorna FK como array quando é join — normaliza para objeto ou array
  type SubRow = { status: string; saas_plans: { name: string; monthly_price: number } | { name: string; monthly_price: number }[] | null };
  (subsByPlan as SubRow[] ?? []).forEach((sub) => {
    const plan = Array.isArray(sub.saas_plans) ? sub.saas_plans[0] : sub.saas_plans;
    const name = plan?.name ?? "Starter";
    const price = plan?.monthly_price ?? 0;
    if (!planCounts[name]) planCounts[name] = { count: 0, price };
    planCounts[name].count++;
  });

  const mrr = Object.values(planCounts).reduce((acc, p) => acc + p.count * p.price, 0);

  const planDist: PlanDist[] = [
    { name: "Starter", count: planCounts["Starter"]?.count ?? 0,  color: "bg-slate-500",   price: planCounts["Starter"]?.price ?? 99  },
    { name: "Pro",     count: planCounts["Pro"]?.count ?? 0,      color: "bg-sky-500",     price: planCounts["Pro"]?.price ?? 249     },
    { name: "Scale",   count: planCounts["Scale"]?.count ?? 0,    color: "bg-violet-500",  price: planCounts["Scale"]?.price ?? 599   },
  ];
  const totalPlanCount = planDist.reduce((a, p) => a + p.count, 0) || 1;

  const recentUsers: RecentUser[] = (recentProfiles ?? []).map((p) => ({
    id: p.id,
    name: p.full_name || "—",
    email: p.email || "—",
    plan: "Starter",
    createdAt: new Date(p.created_at).toLocaleDateString("pt-BR"),
    status: "active",
  }));

  const now = new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

  return (
    <div className="mx-auto max-w-6xl space-y-8">

      {/* ── Header ────────────────────────────────────────── */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-violet-500/20 text-violet-400">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5">
                <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
            </span>
            <h1 className="text-xl font-bold text-slate-100">Painel Admin</h1>
            <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-violet-400">
              Platform
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-500">Visão geral de todos os tenants, planos e uso da plataforma</p>
        </div>
        <p className="text-xs text-slate-600">Atualizado em {now}</p>
      </div>

      {/* ── Stats grid ────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Usuários cadastrados"
          value={(totalUsers ?? 0).toString()}
          sub="Perfis no sistema"
          accent="sky"
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path strokeLinecap="round" strokeLinejoin="round" d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
          }
        />
        <StatCard
          label="Organizações"
          value={(totalOrgs ?? 0).toString()}
          sub="Tenants ativos"
          accent="amber"
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline strokeLinecap="round" strokeLinejoin="round" points="9 22 9 12 15 12 15 22"/>
            </svg>
          }
        />
        <StatCard
          label="Assinaturas ativas"
          value={(activeSubs ?? 0).toString()}
          sub="Planos em vigor"
          accent="green"
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline strokeLinecap="round" strokeLinejoin="round" points="22 4 12 14.01 9 11.01"/>
            </svg>
          }
        />
        <StatCard
          label="MRR estimado"
          value={mrr > 0 ? `R$ ${mrr.toLocaleString("pt-BR")}` : "R$ 0"}
          sub="Receita mensal recorrente"
          accent="violet"
          icon={
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
              <line x1="12" y1="1" x2="12" y2="23"/>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          }
        />
      </div>

      {/* ── Linha 2: Usuários recentes + Distribuição planos ── */}
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">

        {/* Tabela de usuários recentes */}
        <div className="rounded-xl border border-slate-800 bg-slate-900">
          <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
            <SectionTitle>Cadastros recentes</SectionTitle>
            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs text-slate-400">
              {recentUsers.length} registros
            </span>
          </div>
          {recentUsers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Usuário</th>
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Plano</th>
                    <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Cadastro</th>
                  </tr>
                </thead>
                <tbody>
                  {recentUsers.map((u, i) => (
                    <tr key={u.id} className={`${i !== recentUsers.length - 1 ? "border-b border-slate-800/60" : ""} hover:bg-slate-800/30 transition-colors`}>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-sky-600/20 text-xs font-bold text-sky-400">
                            {(u.name !== "—" ? u.name : u.email)[0]?.toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-slate-200">{u.name}</p>
                            <p className="text-xs text-slate-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <PlanBadge plan={u.plan} />
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{u.createdAt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-14 text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-slate-600">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-6 w-6">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                </svg>
              </div>
              <p className="text-sm text-slate-500">Nenhum usuário cadastrado ainda</p>
            </div>
          )}
        </div>

        {/* Distribuição por plano */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <SectionTitle>Distribuição por plano</SectionTitle>
          <div className="space-y-4">
            {planDist.map((plan) => {
              const pct = Math.round((plan.count / totalPlanCount) * 100);
              return (
                <div key={plan.name}>
                  <div className="mb-1.5 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${plan.color}`} />
                      <span className="text-sm font-medium text-slate-300">{plan.name}</span>
                    </div>
                    <span className="text-sm font-mono text-slate-400">{plan.count}</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${plan.color}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="mt-1 text-right text-[11px] text-slate-600">
                    R$ {plan.price}/mês · {pct}%
                  </p>
                </div>
              );
            })}
          </div>

          <div className="mt-6 border-t border-slate-800 pt-4">
            <p className="text-xs text-slate-600">Total de assinantes</p>
            <p className="mt-1 text-2xl font-bold font-mono text-slate-200">
              {planDist.reduce((a, p) => a + p.count, 0)}
            </p>
            <p className="mt-1 text-xs text-slate-600">
              MRR: <span className="text-slate-400 font-semibold">R$ {mrr.toLocaleString("pt-BR")}</span>
            </p>
          </div>
        </div>
      </div>

      {/* ── Uso de IA ─────────────────────────────────────── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="flex items-center justify-between mb-4">
          <SectionTitle>Uso de IA</SectionTitle>
          <span className="text-xs text-slate-600">Hoje · {new Date().toLocaleDateString("pt-BR")}</span>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg bg-slate-800 p-4">
            <p className="text-xs text-slate-500">Tokens hoje</p>
            <p className="mt-2 text-xl font-bold font-mono text-violet-300">
              {totalTokensToday.toLocaleString("pt-BR")}
            </p>
          </div>
          <div className="rounded-lg bg-slate-800 p-4">
            <p className="text-xs text-slate-500">Custo estimado</p>
            <p className="mt-2 text-xl font-bold font-mono text-emerald-300">
              US$ {totalAiCostToday.toFixed(4)}
            </p>
          </div>
          <div className="rounded-lg bg-slate-800 p-4">
            <p className="text-xs text-slate-500">Limite diário</p>
            <p className="mt-2 text-xl font-bold font-mono text-amber-300">—</p>
          </div>
          <div className="rounded-lg bg-slate-800 p-4">
            <p className="text-xs text-slate-500">Status</p>
            <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-slate-300">
              <StatusDot active={false} />
              Brain offline
            </p>
          </div>
        </div>
      </div>

      {/* ── Status do sistema ─────────────────────────────── */}
      <div>
        <SectionTitle>Status do sistema</SectionTitle>
        <div className="grid gap-4 sm:grid-cols-3">
          <SystemCard
            title="Brain Python"
            connected={false}
            description="Serviço de inteligência externo. Inicie o vunotrader_brain.py para conectar a plataforma."
            detail="vunotrader_brain.py · port 8000"
          />
          <SystemCard
            title="MT5 / Expert Advisor"
            connected={false}
            description="Nenhum EA reportando. Compile VunoTrader_v2.mq5 e abra em conta demo no MetaTrader 5."
            detail="VunoTrader_v2.mq5 · WebSocket"
          />
          <SystemCard
            title="Supabase"
            connected={true}
            description="Banco de dados e autenticação operacionais. RLS ativo em todas as tabelas principais."
            detail="supabase.co · RLS ✓"
          />
        </div>
      </div>

      {/* ── Instâncias de Robô ────────────────────────── */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <SectionTitle>Instâncias de Robô</SectionTitle>
          <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs text-slate-400">
            {robotInstances.length} instância{robotInstances.length !== 1 ? "s" : ""}
          </span>
        </div>
        {robotInstances.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-slate-800 bg-slate-900 py-12 text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800 text-slate-600">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-6 w-6">
                <rect x="3" y="11" width="18" height="10" rx="2"/>
                <circle cx="12" cy="5" r="2"/>
                <path strokeLinecap="round" d="M12 7v4"/>
              </svg>
            </div>
            <p className="text-sm text-slate-500">Nenhuma instância registrada ainda</p>
            <p className="mt-1 text-xs text-slate-600">Instâncias aparecem quando o brain conecta pela primeira vez</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-800">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60">
                  <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Robô</th>
                  <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Org</th>
                  <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Modo</th>
                  <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Atividade</th>
                  <th className="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-600">Último sinal</th>
                </tr>
              </thead>
              <tbody className="bg-slate-900">
                {robotInstances.map((robot, i) => {
                  const activity = robotActivityStatus(robot.last_seen_at);
                  const activityConfig = {
                    active:   { label: "Ativo",    cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
                    sleeping: { label: "Dormindo", cls: "bg-amber-500/10   text-amber-400   border-amber-500/20"   },
                    offline:  { label: "Offline",  cls: "bg-slate-700      text-slate-400   border-slate-600"      },
                  }[activity];
                  const lastSeenLabel = robot.last_seen_at
                    ? (() => {
                        const diffMin = Math.round((nowMs - new Date(robot.last_seen_at).getTime()) / 60000);
                        if (diffMin < 1) return "agora";
                        if (diffMin < 60) return `há ${diffMin} min`;
                        const diffH = Math.floor(diffMin / 60);
                        return diffH < 24 ? `há ${diffH}h` : `há ${Math.floor(diffH / 24)}d`;
                      })()
                    : "nunca";
                  return (
                    <tr
                      key={robot.id}
                      className={`${i !== robotInstances.length - 1 ? "border-b border-slate-800/60" : ""} transition-colors hover:bg-slate-800/30`}
                    >
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-400">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-4 w-4">
                              <rect x="3" y="11" width="18" height="10" rx="2"/>
                              <circle cx="12" cy="5" r="2"/>
                              <path strokeLinecap="round" d="M12 7v4"/>
                            </svg>
                          </div>
                          <div>
                            <p className="font-medium text-slate-200">{robot.name}</p>
                            <p className="font-mono text-[10px] text-slate-600">{robot.id.slice(0, 8)}…</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-sm text-slate-400">{robot.orgName}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex flex-wrap gap-1">
                          {(robot.allowed_modes ?? ["demo"]).map((m) => (
                            <span
                              key={m}
                              className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                                m === "real"
                                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                                  : "border-slate-700 bg-slate-800 text-slate-400"
                              }`}
                            >
                              {m === "real" ? "Real" : "Demo"}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`flex w-fit items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${activityConfig.cls}`}>
                          <StatusDot active={activity === "active"} />
                          {activityConfig.label}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-mono text-xs text-slate-500">{lastSeenLabel}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/40 px-5 py-2.5">
              <p className="text-[11px] text-slate-600">
                Ativo = &lt;5 min · Dormindo = &lt;60 min · Offline = &gt;60 min
              </p>
              {robotInstances.filter((r) => robotActivityStatus(r.last_seen_at) === "active" && r.real_trading_enabled).length > 0 && (
                <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                  </span>
                  {robotInstances.filter((r) => robotActivityStatus(r.last_seen_at) === "active" && r.real_trading_enabled).length} real ativo
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Ações rápidas ─────────────────────────────────── */}
      <div>
        <SectionTitle>Ações rápidas</SectionTitle>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: "Ver todos os usuários",     href: "/app/admin/usuarios",  icon: "👥" },
            { label: "Gerenciar planos",           href: "/app/admin/planos",    icon: "📋" },
            { label: "Logs de IA",                 href: "/app/admin/logs-ia",   icon: "🤖" },
            { label: "Modelo ML",                  href: "/app/admin/modelo",    icon: "🔄" },
          ].map((a) => (
            <Link
              key={a.label}
              href={a.href}
              className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900 px-4 py-3.5 text-left text-sm text-slate-300 transition hover:border-slate-600 hover:text-white"
            >
              <span className="text-xl">{a.icon}</span>
              <span className="leading-snug">{a.label}</span>
            </Link>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-700">
          Usuários, planos e modelo ML disponíveis. Logs de IA em breve.
        </p>
      </div>

    </div>
  );
}
