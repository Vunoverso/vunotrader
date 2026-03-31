/**
 * POST /api/study/ingest
 *
 * Aciona o processamento de um material de estudo pendente.
 * Executa `study_ingest_worker.py --id <materialId>` no servidor.
 *
 * Body JSON: { materialId: string }
 *
 * Requer: sessão autenticada + pertencer à mesma organização do material.
 * Retorna: { ok: true } ou { ok: false, error: string }
 */

import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

export async function POST(req: NextRequest): Promise<NextResponse> {
  // 1. Auth
  const supabase = await createClient();
  const { data: { user }, error: authErr } = await supabase.auth.getUser();
  if (authErr || !user) {
    return NextResponse.json({ ok: false, error: "Não autenticado." }, { status: 401 });
  }

  // 2. Parâmetros
  let materialId: string | undefined;
  try {
    const body = await req.json();
    materialId = String(body?.materialId ?? "").trim();
  } catch {
    return NextResponse.json({ ok: false, error: "Body JSON inválido." }, { status: 400 });
  }

  // Valida formato UUID básico para evitar command injection
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!materialId || !UUID_RE.test(materialId)) {
    return NextResponse.json({ ok: false, error: "materialId inválido." }, { status: 400 });
  }

  // 3. Verifica que o material pertence à organização do usuário autenticado
  const { data: profile } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("auth_user_id", user.id)
    .single();

  if (!profile) {
    return NextResponse.json({ ok: false, error: "Perfil não encontrado." }, { status: 403 });
  }

  const { data: member } = await supabase
    .from("organization_members")
    .select("organization_id")
    .eq("profile_id", profile.id)
    .limit(1)
    .single();

  if (!member) {
    return NextResponse.json({ ok: false, error: "Usuário sem organização." }, { status: 403 });
  }

  const { data: material } = await supabase
    .from("study_materials")
    .select("id")
    .eq("id", materialId)
    .eq("organization_id", member.organization_id)
    .single();

  if (!material) {
    return NextResponse.json({ ok: false, error: "Material não encontrado." }, { status: 404 });
  }

  // 4. Executa o worker Python (timeout: 3 minutos por material)
  const scriptPath = process.env.INGEST_SCRIPT_PATH
    ?? path.resolve(process.cwd(), "..", "study_ingest_worker.py");

  try {
    await execAsync(
      `python "${scriptPath}" --id "${materialId}"`,
      { timeout: 180_000 }
    );

    return NextResponse.json({ ok: true });
  } catch (err: unknown) {
    const e = err as { message?: string; stderr?: string };
    console.error("[study/ingest] Falha ao processar material:", e.message, e.stderr);

    return NextResponse.json({
      ok: false,
      error: "Falha ao processar o material. Verifique os logs do servidor.",
    }, { status: 500 });
  }
}
