import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";

const execAsync = promisify(exec);

export async function POST(): Promise<NextResponse> {
  const supabase = await createClient();
  const {
    data: { user },
    error: authErr,
  } = await supabase.auth.getUser();

  if (authErr || !user) {
    return NextResponse.json({ ok: false, error: "Não autenticado." }, { status: 401 });
  }

  const admin = createAdminClient();
  const { data: profile } = await admin
    .from("user_profiles")
    .select("is_platform_admin")
    .eq("id", user.id)
    .single();

  if (!profile?.is_platform_admin) {
    return NextResponse.json({ ok: false, error: "Acesso negado." }, { status: 403 });
  }

  const scriptPath =
    process.env.GLOBAL_MEMORY_REBUILD_SCRIPT_PATH ??
    path.resolve(process.cwd(), "..", "backend", "scripts", "rebuild_global_memory.py");

  const days = Number(process.env.GLOBAL_MEMORY_DAYS ?? "180");
  const minSamples = Number(process.env.GLOBAL_MEMORY_MIN_SAMPLES ?? "20");

  try {
    const { stdout, stderr } = await execAsync(
      `python "${scriptPath}" --days ${days} --min-samples ${minSamples}`,
      { timeout: 300_000 }
    );

    const output = `${stdout}\n${stderr}`.trim().slice(-2000);
    return NextResponse.json({
      ok: true,
      message: "Memória global reconstruída.",
      output,
    });
  } catch (err: unknown) {
    const e = err as { code?: number; message?: string; stdout?: string; stderr?: string };

    if (e.code === 2) {
      return NextResponse.json(
        {
          ok: false,
          error: "Dados insuficientes para agregação global.",
          output: `${e.stdout ?? ""}\n${e.stderr ?? ""}`.trim(),
        },
        { status: 422 }
      );
    }

    return NextResponse.json(
      {
        ok: false,
        error: "Falha ao reconstruir memória global.",
        detail: e.message,
      },
      { status: 500 }
    );
  }
}
