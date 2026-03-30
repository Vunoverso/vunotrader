import { createClient } from "@supabase/supabase-js";

/**
 * Cliente Supabase com service role — use apenas em Server Actions/Route Handlers.
 * Nunca expor no cliente. A variável SUPABASE_SERVICE_ROLE_KEY não tem prefixo NEXT_PUBLIC_.
 */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error(
      "Variáveis de ambiente SUPABASE_URL (ou NEXT_PUBLIC_SUPABASE_URL) e SUPABASE_SERVICE_ROLE_KEY são obrigatórias."
    );
  }

  return createClient(url, key, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
