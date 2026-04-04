import { createHash, randomBytes } from "crypto";
import { NextRequest, NextResponse } from "next/server";

import { buildRobotPackageBuffer } from "@/lib/mt5/package-archive";
import {
  buildBridgeName,
  buildPackageFileName,
  type RobotPackageInput,
} from "@/lib/mt5/package-template";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";

type Mode = "demo" | "real";
type RobotProductType = "robo_integrado" | "robo_hibrido_visual";

function generateToken(): string {
  return randomBytes(24).toString("base64url");
}

function hashToken(token: string): string {
  return createHash("sha256").update(token, "utf8").digest("hex");
}

function normalizeRobotProductType(value: unknown): RobotProductType {
  return String(value ?? "").trim().toLowerCase() === "robo_hibrido_visual"
    ? "robo_hibrido_visual"
    : "robo_integrado";
}

async function revokeInstance(instanceId: string): Promise<void> {
  const admin = createAdminClient();
  await admin.from("robot_instances").delete().eq("id", instanceId);
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const supabase = await createClient();
  const {
    data: { user },
    error: authErr,
  } = await supabase.auth.getUser();

  if (authErr || !user) {
    return NextResponse.json({ ok: false, error: "Nao autenticado." }, { status: 401 });
  }

  const body = await req.json().catch(() => ({}));
  const modeRaw = String(body?.mode ?? "demo").toLowerCase();
  const mode: Mode = modeRaw === "real" ? "real" : "demo";
  const robotProductType = normalizeRobotProductType(body?.product_type);
  const admin = createAdminClient();
  const access = await getSubscriptionAccess(supabase, user.id);

  const visualHybridEnabled = Boolean(
    access.features["robot.visual_hybrid"] && access.features["robot.visual_shadow"]
  );

  if (robotProductType === "robo_hibrido_visual" && !visualHybridEnabled) {
    return NextResponse.json(
      { ok: false, error: "Seu plano atual ainda nao libera o Robo Hibrido Visual." },
      { status: 403 }
    );
  }

  const { data: profile } = await admin
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .limit(1)
    .maybeSingle();

  if (!profile?.id) {
    return NextResponse.json({ ok: false, error: "Perfil do usuario nao encontrado." }, { status: 404 });
  }

  const { data: member } = await admin
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profile.id)
    .limit(1)
    .maybeSingle();

  if (!member?.organization_id) {
    return NextResponse.json({ ok: false, error: "Organizacao nao encontrada para este perfil." }, { status: 404 });
  }

  const organizationId = String(member.organization_id);
  const profileId = String(profile.id);
  const token = generateToken();
  const name = `VunoBridge-${new Date().toISOString().replace(/[:.]/g, "-")}`;
  const allowReal = mode === "real";
  const allowedModes = allowReal ? ["demo", "real"] : ["demo"];
  const visualShadowEnabled = robotProductType === "robo_hibrido_visual" && visualHybridEnabled;

  const { data: created, error: insertErr } = await admin
    .from("robot_instances")
    .insert({
      organization_id: organizationId,
      profile_id: profileId,
      name,
      robot_token_hash: hashToken(token),
      status: "active",
      allowed_modes: allowedModes,
      real_trading_enabled: allowReal,
      max_risk_real: 1.5,
      robot_product_type: robotProductType,
      visual_shadow_enabled: visualShadowEnabled,
    })
    .select("id, name, allowed_modes, real_trading_enabled, robot_product_type, visual_shadow_enabled")
    .single();

  if (insertErr || !created?.id) {
    return NextResponse.json({ ok: false, error: "Falha ao criar instancia do robo." }, { status: 500 });
  }

  const packageInput: RobotPackageInput = {
    robotId: created.id,
    robotToken: token,
    userId: user.id,
    organizationId,
    instanceName: created.name,
    mode,
    robotProductType,
    visualShadowEnabled,
  };

  let packageBuffer: Buffer;

  try {
    packageBuffer = await buildRobotPackageBuffer(packageInput);
  } catch (error) {
    await revokeInstance(created.id);
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Falha ao montar o pacote da instancia.",
      },
      { status: 500 },
    );
  }

  const { error: pauseErr } = await admin
    .from("robot_instances")
    .update({ status: "paused" })
    .eq("organization_id", organizationId)
    .eq("profile_id", profileId)
    .eq("status", "active")
    .neq("id", created.id);

  if (pauseErr) {
    await revokeInstance(created.id);
    return NextResponse.json({ ok: false, error: "Falha ao pausar instancias antigas." }, { status: 500 });
  }

  const packageBytes = Uint8Array.from(packageBuffer);

  return new NextResponse(packageBytes, {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="${buildPackageFileName(created.name)}"`,
      "Cache-Control": "no-store",
      "X-Vuno-Bridge-Name": buildBridgeName(created.id),
      "X-Vuno-Instance-Id": created.id,
      "X-Vuno-Instance-Name": created.name,
      "X-Vuno-Robot-Product-Type": created.robot_product_type,
      "X-Vuno-Visual-Shadow": created.visual_shadow_enabled ? "true" : "false",
    },
  });
}