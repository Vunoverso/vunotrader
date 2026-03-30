import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import {
  updateProfileAction,
  uploadProfileAvatarAction,
  changeEmailAction,
  changePasswordAction,
  changeMyPlanAction,
  cancelMyPlanAction,
  deleteMyAccountAction,
} from "./actions";

type PlanRow = {
  id: string;
  code: string;
  name: string;
  monthly_price: number;
  yearly_price: number | null;
};

type SubscriptionRow = {
  status: "trialing" | "active" | "past_due" | "canceled" | "paused";
  billing_cycle: "monthly" | "yearly";
  trial_ends_at: string | null;
  current_period_end: string | null;
  saas_plans: { code: string; name: string } | { code: string; name: string }[] | null;
};

type ProfileRow = {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
};

type ProfileSettingsRow = {
  phone: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  document_type: string | null;
  document_value: string | null;
  document_verified: boolean | null;
};

type MemberRow = {
  profile_id: string;
  organizations: {
    id: string;
    name: string;
    saas_subscriptions: SubscriptionRow[];
  } | {
    id: string;
    name: string;
    saas_subscriptions: SubscriptionRow[];
  }[] | null;
};

export default async function ConfiguracoesPage() {
  const supabase = await createClient();
  const admin = createAdminClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/login");
  }

  const { data: profileByAuth } = await admin
    .from("user_profiles")
    .select("id, email, full_name, avatar_url")
    .eq("auth_user_id", user.id)
    .limit(1)
    .maybeSingle();

  const { data: profilesByEmail } = user.email
    ? await admin
        .from("user_profiles")
      .select("id, email, full_name, avatar_url")
        .eq("email", user.email)
        .order("created_at", { ascending: false })
        .limit(20)
    : { data: null };

  const profileCandidates = [profileByAuth, ...(profilesByEmail ?? [])]
    .filter((profile): profile is ProfileRow => Boolean(profile))
    .reduce<ProfileRow[]>((acc, profile) => {
      if (!acc.some((item) => item.id === profile.id)) {
        acc.push(profile);
      }
      return acc;
    }, []);

  const { data: memberships } = profileCandidates.length > 0
    ? await admin
        .from("organization_members")
        .select("profile_id, organizations ( id, name, saas_subscriptions ( status, billing_cycle, trial_ends_at, current_period_end, saas_plans ( code, name ) ) )")
        .in("profile_id", profileCandidates.map((profile) => profile.id))
        .limit(100)
    : { data: null };

  const memberRows = (memberships ?? []) as MemberRow[];
  const pickSubscription = (member: MemberRow) => {
    const organization = member.organizations
      ? (Array.isArray(member.organizations) ? member.organizations[0] : member.organizations)
      : null;

    const subscriptions = organization?.saas_subscriptions ?? [];
    return (
      subscriptions.find((row) => row.status === "active") ??
      subscriptions.find((row) => row.status === "trialing") ??
      subscriptions[0] ??
      null
    );
  };

  const preferredMember =
    memberRows.find((row) => row.profile_id === profileByAuth?.id && pickSubscription(row)) ??
    memberRows.find((row) => Boolean(pickSubscription(row))) ??
    memberRows[0] ??
    null;

  const profileIdWithOrg = preferredMember?.profile_id ?? profileCandidates[0]?.id ?? null;

  const profile = profileCandidates.find((row) => row.id === profileIdWithOrg) ?? profileCandidates[0] ?? null;
  const { data: profileSettingsData } = profile?.id
    ? await admin
        .from("user_profiles")
        .select("phone, address_line1, address_line2, city, state, postal_code, country, document_type, document_value, document_verified")
        .eq("id", profile.id)
        .limit(1)
        .maybeSingle()
    : { data: null };
  const profileSettings = (profileSettingsData ?? null) as ProfileSettingsRow | null;
  const subscription = preferredMember ? pickSubscription(preferredMember) : null;

  const { data: plans } = await admin
    .from("saas_plans")
    .select("id, code, name, monthly_price, yearly_price")
    .eq("is_active", true)
    .order("monthly_price", { ascending: true });

  const planRows = (plans ?? []) as PlanRow[];
  const currentPlan = Array.isArray(subscription?.saas_plans) ? subscription?.saas_plans[0] : subscription?.saas_plans;
  const displayName =
    profile?.full_name ??
    (typeof user.user_metadata?.full_name === "string" ? user.user_metadata.full_name : null) ??
    (typeof user.user_metadata?.name === "string" ? user.user_metadata.name : null) ??
    "";

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h1 className="text-xl font-bold text-slate-100">Configurações</h1>
        <p className="mt-1 text-sm text-slate-500">Gerencie seus dados pessoais, segurança, assinatura e conta.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <form action={updateProfileAction} className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Perfil</h2>

          <label className="block space-y-1 text-sm">
            <span className="text-slate-500">Nome completo</span>
            <input name="full_name" defaultValue={displayName} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
          </label>

          <label className="block space-y-1 text-sm">
            <span className="text-slate-500">Email</span>
            <input defaultValue={profile?.email ?? user.email ?? ""} disabled className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-400" />
          </label>

          <label className="block space-y-1 text-sm">
            <span className="text-slate-500">Telefone</span>
            <input name="phone" defaultValue={profileSettings?.phone ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1 text-sm sm:col-span-2">
              <span className="text-slate-500">Endereço</span>
              <input name="address_line1" defaultValue={profileSettings?.address_line1 ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
            <label className="block space-y-1 text-sm sm:col-span-2">
              <span className="text-slate-500">Complemento</span>
              <input name="address_line2" defaultValue={profileSettings?.address_line2 ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-500">Cidade</span>
              <input name="city" defaultValue={profileSettings?.city ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-500">Estado</span>
              <input name="state" defaultValue={profileSettings?.state ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-500">CEP</span>
              <input name="postal_code" defaultValue={profileSettings?.postal_code ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-slate-500">País</span>
              <input name="country" defaultValue={profileSettings?.country ?? "BR"} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block space-y-1 text-sm">
              <span className="text-slate-500">Tipo de documento</span>
              <select name="document_type" defaultValue={profileSettings?.document_type ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500">
                <option value="">Não informado</option>
                <option value="cpf">CPF</option>
                <option value="rg">RG</option>
              </select>
            </label>
            <label className="block space-y-1 text-sm sm:col-span-2">
              <span className="text-slate-500">Documento</span>
              <input name="document_value" defaultValue={profileSettings?.document_value ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            </label>
          </div>

          <p className={`text-xs ${profileSettings?.document_verified ? "text-emerald-300" : "text-slate-500"}`}>
            {profileSettings?.document_verified ? "Documento validado automaticamente." : "Documento ainda não validado."}
          </p>

          <button className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20">
            Salvar perfil
          </button>
        </form>

        <div className="space-y-6">
          <form action={uploadProfileAvatarAction} className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Foto de perfil</h2>
            <div className="flex items-center gap-3">
              <div className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-full border border-slate-700 bg-slate-950">
                {profile?.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={profile.avatar_url} alt="Avatar atual" className="h-full w-full object-cover" />
                ) : (
                  <span className="text-xs font-semibold text-slate-400">{(displayName || user.email || "U")[0]?.toUpperCase()}</span>
                )}
              </div>
              <div className="text-xs text-slate-500">
                <p>Envie uma imagem JPG, PNG ou WEBP.</p>
                <p>Tamanho máximo: 5MB.</p>
              </div>
            </div>
            <input name="avatar_file" type="file" accept="image/png,image/jpeg,image/webp,image/jpg" required className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 file:mr-3 file:rounded file:border-0 file:bg-slate-800 file:px-2 file:py-1 file:text-slate-200" />
            <button className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20">
              Enviar foto
            </button>
          </form>

          <form action={changeEmailAction} className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Segurança · Email</h2>
            <p className="text-xs text-slate-500">Atual: {profile?.email ?? user.email}</p>
            <input name="new_email" type="email" required placeholder="novo-email@dominio.com" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            <button className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20">
              Alterar email
            </button>
          </form>

          <form action={changePasswordAction} className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Segurança · Senha</h2>
            <input name="new_password" type="password" minLength={8} required placeholder="Nova senha (mínimo 8 caracteres)" className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500" />
            <button className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 transition-colors hover:bg-sky-500/20">
              Alterar senha
            </button>
          </form>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Plano atual</h2>
          <p className="text-sm text-slate-300">
            Status: <span className="font-semibold text-slate-100">{subscription?.status ?? "sem assinatura"}</span>
          </p>
          <p className="text-sm text-slate-300">
            Plano: <span className="font-semibold text-slate-100">{currentPlan?.name ?? "—"}</span>
          </p>
          <p className="text-sm text-slate-300">
            Ciclo: <span className="font-semibold text-slate-100">{subscription?.billing_cycle ?? "—"}</span>
          </p>
          <p className="text-xs text-slate-500">
            Trial até: {subscription?.trial_ends_at ? new Date(subscription.trial_ends_at).toLocaleDateString("pt-BR") : "—"}
          </p>
        </div>

        <form action={changeMyPlanAction} className="space-y-3 rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Mudar de plano</h2>
          <select name="plan_code" required defaultValue={currentPlan?.code ?? ""} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500">
            <option value="" disabled>Selecione o plano</option>
            {planRows.map((plan) => (
              <option key={plan.id} value={plan.code}>
                {plan.name} · R$ {Number(plan.monthly_price).toFixed(2)}/mês
              </option>
            ))}
          </select>
          <select name="billing_cycle" defaultValue={subscription?.billing_cycle ?? "monthly"} className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-200 outline-none focus:border-sky-500">
            <option value="monthly">Mensal</option>
            <option value="yearly">Anual</option>
          </select>
          <button className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300 transition-colors hover:bg-emerald-500/20">
            Ativar / trocar plano
          </button>
          <button formAction={cancelMyPlanAction} className="ml-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-300 transition-colors hover:bg-red-500/20">
            Cancelar plano
          </button>
        </form>
      </div>

      <form action={deleteMyAccountAction} className="space-y-3 rounded-2xl border border-red-500/30 bg-red-950/20 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-red-300">Excluir conta</h2>
        <p className="text-xs text-red-200/90">Ação permanente. Digite EXCLUIR para confirmar.</p>
        <input name="confirmation" placeholder="EXCLUIR" className="w-full max-w-xs rounded-lg border border-red-500/40 bg-slate-950 px-3 py-2 text-red-100 outline-none focus:border-red-400" />
        <button className="rounded-lg border border-red-500/40 bg-red-500/20 px-4 py-2 text-sm font-semibold text-red-200 transition-colors hover:bg-red-500/30">
          Excluir minha conta
        </button>
      </form>
    </div>
  );
}
