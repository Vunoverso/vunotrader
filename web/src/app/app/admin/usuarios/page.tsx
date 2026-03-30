import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { UsuariosFilters } from "./_components/usuarios-filters";
import { UserActionMenu } from "./_components/user-action-menu";
import {
  toggleAdminAction,
  banUserAction,
  deleteUserAction,
  changePlanAction,
  changeBillingCycleAction,
  createOrganizationForUserAction,
  updateMemberRoleAction,
  removeUserFromOrganizationAction,
} from "./actions";

// ── Constantes ────────────────────────────────────────────────
const PAGE_SIZE = 20;

// ── Tipos ─────────────────────────────────────────────────────
type OrgNode = {
  id: string;
  name: string;
  saas_subscriptions: Array<{
    status: string;
    billing_cycle?: "monthly" | "yearly";
    saas_plans: { name: string } | { name: string }[] | null;
  }>;
};

type MemberRow = {
  profile_id: string;
  role: string;
  organizations: OrgNode | OrgNode[] | null;
};

// ── Componentes internos ──────────────────────────────────────
function PlanBadge({ plan }: { plan: string }) {
  const map: Record<string, string> = {
    Starter: "bg-slate-700 text-slate-300 border-slate-600",
    Pro:     "bg-sky-500/20 text-sky-300 border-sky-500/30",
    Scale:   "bg-violet-500/20 text-violet-300 border-violet-500/30",
    Trial:   "bg-amber-500/20 text-amber-300 border-amber-500/30",
    "Sem plano": "bg-slate-800 text-slate-500 border-slate-700",
  };
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${map[plan] ?? map.Starter}`}>
      {plan}
    </span>
  );
}

function BillingCycleBadge({ cycle }: { cycle: "monthly" | "yearly" | null }) {
  if (!cycle) {
    return <span className="text-xs text-slate-600">—</span>;
  }

  const isYearly = cycle === "yearly";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
        isYearly
          ? "border-cyan-500/40 bg-cyan-500/15 text-cyan-300"
          : "border-slate-600 bg-slate-700 text-slate-300"
      }`}
    >
      {isYearly ? "Anual" : "Mensal"}
    </span>
  );
}

function RoleBadge({ role }: { role: string }) {
  const map: Record<string, string> = {
    owner:   "text-amber-400",
    admin:   "text-violet-400",
    analyst: "text-sky-400",
    viewer:  "text-slate-400",
  };
  const labels: Record<string, string> = {
    owner:   "Owner",
    admin:   "Admin",
    analyst: "Analista",
    viewer:  "Leitor",
  };
  return (
    <span className={`text-xs font-medium ${map[role] ?? "text-slate-500"}`}>
      {labels[role] ?? role}
    </span>
  );
}

// ── Página principal ──────────────────────────────────────────
export default async function AdminUsuariosPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; plano?: string; pagina?: string }>;
}) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (user?.user_metadata?.is_admin !== true) redirect("/app/dashboard");

  const params     = await searchParams;
  const search     = params.q?.trim() ?? "";
  const planFilter = params.plano ?? "";
  const page       = Math.max(1, parseInt(params.pagina ?? "1", 10));
  const offset     = (page - 1) * PAGE_SIZE;

  // ── Query: usuários paginados + busca ─────────────────────
  let query = createAdminClient()
    .from("user_profiles")
    .select("id, auth_user_id, full_name, email, created_at", { count: "exact" })
    .order("created_at", { ascending: false })
    .range(offset, offset + PAGE_SIZE - 1);

  if (search) {
    query = query.or(`full_name.ilike.%${search}%,email.ilike.%${search}%`);
  }

  const { data: profiles, count: totalCount } = await query;
  const total = totalCount ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // ── Query: org memberships dos usuários desta página ──────
  const profileIds = (profiles ?? []).map((p) => p.id);

  const { data: memberships } =
    profileIds.length > 0
      ? await createAdminClient()
          .from("organization_members")
          .select(
            "profile_id, role, organizations ( id, name, saas_subscriptions ( status, billing_cycle, saas_plans ( name ) ) )"
          )
          .in("profile_id", profileIds)
      : { data: [] as MemberRow[] };

  // ── Mapa profileId → membership ──────────────────────────
  const memberMap: Record<string, MemberRow> = {};
  (memberships as MemberRow[] ?? []).forEach((m) => {
    if (!memberMap[m.profile_id]) memberMap[m.profile_id] = m;
  });

  // ── Paginação: URL helper ─────────────────────────────────
  const pageUrl = (p: number) => {
    const qs = new URLSearchParams();
    if (search)     qs.set("q", search);
    if (planFilter) qs.set("plano", planFilter);
    if (p > 1)      qs.set("pagina", p.toString());
    const str = qs.toString();
    return `/app/admin/usuarios${str ? `?${str}` : ""}`;
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">

      {/* ── Breadcrumb + Título ──────────────────────────── */}
      <div>
        <nav className="flex items-center gap-1.5 text-sm text-slate-500">
          <Link href="/app/admin" className="hover:text-slate-300 transition-colors">
            Admin
          </Link>
          <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-slate-300">Usuários</span>
        </nav>

        <div className="mt-2 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-100">Gestão de Usuários</h1>
            <p className="mt-0.5 text-sm text-slate-500">
              Todos os perfis cadastrados na plataforma
            </p>
          </div>
          {/* Contador em destaque */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2.5 text-center">
            <p className="text-2xl font-bold font-mono text-sky-300">{total}</p>
            <p className="text-[11px] text-slate-500">usuários</p>
          </div>
        </div>
      </div>

      {/* ── Filtros ───────────────────────────────────────── */}
      <UsuariosFilters initialQ={search} initialPlano={planFilter} total={total} />

      {/* ── Tabela ────────────────────────────────────────── */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">

        {(profiles?.length ?? 0) > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left text-xs text-slate-500 uppercase tracking-wide">
                  <th className="px-4 py-3 font-medium">Usuário</th>
                  <th className="px-4 py-3 font-medium hidden md:table-cell">Organização</th>
                  <th className="px-4 py-3 font-medium">Plano</th>
                  <th className="px-4 py-3 font-medium hidden sm:table-cell">Ciclo</th>
                  <th className="px-4 py-3 font-medium hidden lg:table-cell">Função</th>
                  <th className="px-4 py-3 font-medium hidden sm:table-cell">Cadastro</th>
                  <th className="px-4 py-3 font-medium text-right">Ações</th>
                </tr>
              </thead>
              <tbody>
                {(profiles ?? []).map((profile) => {
                  const member = memberMap[profile.id];
                  const org    = member
                    ? (Array.isArray(member.organizations) ? member.organizations[0] : member.organizations)
                    : null;

                  const subs = org?.saas_subscriptions ?? [];
                  const sub =
                    subs.find((s) => s.status === "active") ??
                    subs.find((s) => s.status === "trialing") ??
                    subs[0];
                  const planRaw = sub?.saas_plans;
                  const planName =
                    (Array.isArray(planRaw) ? planRaw[0]?.name : planRaw?.name) ?? "Sem plano";
                  const billingCycle = (sub?.billing_cycle as "monthly" | "yearly" | undefined) ?? null;

                  // Iniciais para avatar
                  const initials = (profile.full_name ?? profile.email ?? "?")
                    .split(" ")
                    .slice(0, 2)
                    .map((n: string) => n[0])
                    .join("")
                    .toUpperCase();

                  const avatarColors = [
                    "bg-violet-500/20 text-violet-400",
                    "bg-sky-500/20 text-sky-400",
                    "bg-emerald-500/20 text-emerald-400",
                    "bg-amber-500/20 text-amber-400",
                  ];
                  const colorIdx =
                    profile.id.charCodeAt(0) % avatarColors.length;

                  return (
                    <tr
                      key={profile.id}
                      className="border-b border-slate-800 last:border-0 hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Usuário */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div
                            className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${avatarColors[colorIdx]}`}
                          >
                            {initials}
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-slate-200 truncate max-w-[160px]">
                              {profile.full_name || "Sem nome"}
                            </p>
                            <p className="text-xs text-slate-500 truncate max-w-[160px]">
                              {profile.email}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Organização */}
                      <td className="px-4 py-3 hidden md:table-cell">
                        {org ? (
                          <span className="text-sm text-slate-300">{org.name}</span>
                        ) : (
                          <span className="text-xs italic text-slate-600">Sem org</span>
                        )}
                      </td>

                      {/* Plano */}
                      <td className="px-4 py-3">
                        <PlanBadge plan={planName} />
                      </td>

                      {/* Ciclo */}
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <BillingCycleBadge cycle={billingCycle} />
                      </td>

                      {/* Função */}
                      <td className="px-4 py-3 hidden lg:table-cell">
                        {member?.role ? <RoleBadge role={member.role} /> : <span className="text-xs text-slate-600">—</span>}
                      </td>

                      {/* Data */}
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <span className="text-xs text-slate-500">
                          {new Date(profile.created_at).toLocaleDateString("pt-BR")}
                        </span>
                      </td>

                      {/* Ações */}
                      <td className="px-4 py-3 text-right">
                        <UserActionMenu
                          profileId={profile.id}
                          authUserId={profile.auth_user_id ?? ""}
                          userName={profile.full_name || profile.email || "Usuário"}
                          organizationId={org?.id ?? null}
                          currentRole={(member?.role as "owner" | "admin" | "analyst" | "viewer" | null) ?? null}
                          currentPlan={planName}
                          currentBillingCycle={billingCycle ?? "monthly"}
                          isAdmin={false}
                          isBanned={false}
                          toggleAdminAction={toggleAdminAction}
                          banUserAction={banUserAction}
                          deleteUserAction={deleteUserAction}
                          changePlanAction={changePlanAction}
                          changeBillingCycleAction={changeBillingCycleAction}
                          createOrganizationForUserAction={createOrganizationForUserAction}
                          updateMemberRoleAction={updateMemberRoleAction}
                          removeUserFromOrganizationAction={removeUserFromOrganizationAction}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-800">
              <svg className="h-7 w-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-400">Nenhum usuário encontrado</p>
            {search && (
              <p className="mt-1 text-xs text-slate-600">
                Tente outro nome ou e-mail
              </p>
            )}
            {search && (
              <Link
                href="/app/admin/usuarios"
                className="mt-3 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-400 hover:border-slate-600 hover:text-slate-200 transition-colors"
              >
                Limpar filtros
              </Link>
            )}
          </div>
        )}

        {/* ── Paginação ────────────────────────────────── */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3">
            <p className="text-xs text-slate-500">
              {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} de {total}
            </p>
            <div className="flex items-center gap-1">
              {/* Anterior */}
              {page > 1 ? (
                <Link
                  href={pageUrl(page - 1)}
                  className="flex h-7 w-7 items-center justify-center rounded text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </Link>
              ) : (
                <span className="flex h-7 w-7 items-center justify-center rounded text-slate-700">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </span>
              )}

              {/* Números (max 7 visíveis) */}
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 2)
                .reduce<(number | "…")[]>((acc, p, idx, arr) => {
                  if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push("…");
                  acc.push(p);
                  return acc;
                }, [])
                .map((p, idx) =>
                  p === "…" ? (
                    <span key={`ellipsis-${idx}`} className="flex h-7 w-7 items-center justify-center text-xs text-slate-600">…</span>
                  ) : (
                    <Link
                      key={p}
                      href={pageUrl(p as number)}
                      className={`flex h-7 w-7 items-center justify-center rounded text-xs font-medium transition-colors ${
                        p === page
                          ? "bg-violet-600 text-white"
                          : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                      }`}
                    >
                      {p}
                    </Link>
                  )
                )}

              {/* Próxima */}
              {page < totalPages ? (
                <Link
                  href={pageUrl(page + 1)}
                  className="flex h-7 w-7 items-center justify-center rounded text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              ) : (
                <span className="flex h-7 w-7 items-center justify-center rounded text-slate-700">
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
