import { randomBytes, createHash } from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";

type Mode = "demo" | "real";

function generateToken(): string {
  return randomBytes(24).toString("base64url");
}

function hashToken(token: string): string {
  return createHash("sha256").update(token, "utf8").digest("hex");
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const supabase = await createClient();
  const {
    data: { user },
    error: authErr,
  } = await supabase.auth.getUser();

  if (authErr || !user) {
    return NextResponse.json({ ok: false, error: "Não autenticado." }, { status: 401 });
  }

  const body = await req.json().catch(() => ({}));
  const modeRaw = String(body?.mode ?? "demo").toLowerCase();
  const mode: Mode = modeRaw === "real" ? "real" : "demo";

  const admin = createAdminClient();

  const { data: profile } = await admin
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .limit(1)
    .maybeSingle();

  if (!profile?.id) {
    return NextResponse.json({ ok: false, error: "Perfil do usuário não encontrado." }, { status: 404 });
  }

  const { data: member } = await admin
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profile.id)
    .limit(1)
    .maybeSingle();

  if (!member?.organization_id) {
    return NextResponse.json({ ok: false, error: "Organização não encontrada para este perfil." }, { status: 404 });
  }

  const organizationId = String(member.organization_id);
  const profileId = String(profile.id);

  const token = generateToken();
  const tokenHash = hashToken(token);
  const name = `EA-${new Date().toISOString().replace(/[:.]/g, "-")}`;

  const { error: pauseErr } = await admin
    .from("robot_instances")
    .update({ status: "paused" })
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId)
    .eq("status", "active");

  if (pauseErr) {
    return NextResponse.json({ ok: false, error: "Falha ao pausar instâncias antigas." }, { status: 500 });
  }

  const allowReal = mode === "real";
  const allowedModes = allowReal ? ["demo", "real"] : ["demo"];

  const { data: created, error: insertErr } = await admin
    .from("robot_instances")
    .insert({
      organization_id: organizationId,
      profile_id: profileId,
      name,
      robot_token_hash: tokenHash,
      status: "active",
      allowed_modes: allowedModes,
      real_trading_enabled: allowReal,
      max_risk_real: 1.5,
    })
    .select("id, name, allowed_modes, real_trading_enabled")
    .single();

  if (insertErr || !created?.id) {
    return NextResponse.json({ ok: false, error: "Falha ao criar credenciais do robô." }, { status: 500 });
  }

  return NextResponse.json({
    ok: true,
    robot_id: created.id,
    robot_token: token,
    user_id: user.id,
    organization_id: organizationId,
    instance_name: created.name,
    allowed_modes: created.allowed_modes,
    real_trading_enabled: created.real_trading_enabled,
    warning: "O token é exibido apenas uma vez. Salve em local seguro.",
  });
}
