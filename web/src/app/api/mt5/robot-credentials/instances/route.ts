import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

async function resolveScope() {
  const supabase = await createClient();
  const {
    data: { user },
    error: authErr,
  } = await supabase.auth.getUser();

  if (authErr || !user) {
    return { supabase, error: NextResponse.json({ ok: false, error: "Não autenticado." }, { status: 401 }) };
  }

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .limit(1)
    .maybeSingle();

  if (!profile?.id) {
    return {
      supabase,
      error: NextResponse.json({ ok: false, error: "Perfil não encontrado." }, { status: 404 }),
    };
  }

  const { data: member } = await supabase
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profile.id)
    .limit(1)
    .maybeSingle();

  if (!member?.organization_id) {
    return {
      supabase,
      error: NextResponse.json({ ok: false, error: "Organização não encontrada." }, { status: 404 }),
    };
  }

  return {
    supabase,
    profileId: String(profile.id),
    organizationId: String(member.organization_id),
    error: null,
  };
}

export async function GET(): Promise<NextResponse> {
  const scope = await resolveScope();
  if (scope.error) return scope.error;

  const { supabase, profileId, organizationId } = scope;

  const { data, error } = await supabase
    .from("robot_instances")
    .select("id, name, status, allowed_modes, real_trading_enabled, last_seen_at, created_at")
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId)
    .order("created_at", { ascending: false })
    .limit(20);

  if (error) {
    return NextResponse.json({ ok: false, error: "Falha ao listar instâncias." }, { status: 500 });
  }

  return NextResponse.json({ ok: true, instances: data ?? [] });
}

export async function PATCH(req: NextRequest): Promise<NextResponse> {
  const scope = await resolveScope();
  if (scope.error) return scope.error;

  const { supabase, profileId, organizationId } = scope;
  const body = await req.json().catch(() => ({}));
  const robotId = String(body?.robot_id ?? "").trim();
  const action = String(body?.action ?? "").trim().toLowerCase();

  if (!robotId) {
    return NextResponse.json({ ok: false, error: "robot_id é obrigatório." }, { status: 400 });
  }

  if (!["pause", "revoke", "activate"].includes(action)) {
    return NextResponse.json({ ok: false, error: "Ação inválida." }, { status: 400 });
  }

  const status = action === "pause" ? "paused" : action === "revoke" ? "revoked" : "active";

  const { data, error } = await supabase
    .from("robot_instances")
    .update({ status })
    .eq("id", robotId)
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId)
    .select("id, name, status, allowed_modes, real_trading_enabled, last_seen_at, created_at")
    .single();

  if (error || !data) {
    return NextResponse.json({ ok: false, error: "Falha ao atualizar instância." }, { status: 500 });
  }

  return NextResponse.json({ ok: true, instance: data });
}
