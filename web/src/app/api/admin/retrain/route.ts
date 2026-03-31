/**
 * POST /api/admin/retrain
 *
 * Dispara o pipeline de retreino do modelo ML.
 * Executa `retrain_pipeline.py` no servidor via child_process (Railway/servidor Node).
 *
 * Requer: sessão autenticada + papel admin ou owner da plataforma (is_platform_admin).
 * Retorna: { ok: true, message: string } ou { ok: false, error: string }
 *
 * Nota: em produção (Railway), o Python precisa estar disponível no container.
 * A variável de ambiente RETRAIN_SCRIPT_PATH pode sobrescrever o caminho padrão.
 */

import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

export async function POST(): Promise<NextResponse> {
  // 1. Autenticação
  const supabase = await createClient();
  const { data: { user }, error: authErr } = await supabase.auth.getUser();
  if (authErr || !user) {
    return NextResponse.json({ ok: false, error: "Não autenticado." }, { status: 401 });
  }

  // 2. Verifica papel de admin na plataforma
  const admin = createAdminClient();
  const { data: profile } = await admin
    .from("user_profiles")
    .select("is_platform_admin")
    .eq("id", user.id)
    .single();

  if (!profile?.is_platform_admin) {
    return NextResponse.json({ ok: false, error: "Acesso negado." }, { status: 403 });
  }

  // 3. Localiza o script de retreino
  const scriptPath = process.env.RETRAIN_SCRIPT_PATH
    ?? path.resolve(process.cwd(), "..", "retrain_pipeline.py");

  // 4. Executa com timeout de 5 minutos
  try {
    const { stdout, stderr } = await execAsync(
      `python "${scriptPath}" --days 30 --min-samples 50`,
      { timeout: 300_000 }
    );

    const output = `${stdout}\n${stderr}`.trim().slice(-2000); // últimas 2000 chars

    return NextResponse.json({
      ok: true,
      message: "Retreino concluído.",
      output,
    });
  } catch (err: unknown) {
    const e = err as { code?: number; message?: string; stdout?: string; stderr?: string };

    if (e.code === 2) {
      // exit code 2 = dados insuficientes (não é erro crítico)
      return NextResponse.json({
        ok: false,
        error: "Dados insuficientes para retreino. Aguarde mais operações.",
        output: `${e.stdout ?? ""}\n${e.stderr ?? ""}`.trim(),
      }, { status: 422 });
    }

    console.error("[retrain] Falha ao executar pipeline:", e.message);
    return NextResponse.json({
      ok: false,
      error: "Falha ao executar pipeline de retreino.",
      detail: e.message,
    }, { status: 500 });
  }
}
