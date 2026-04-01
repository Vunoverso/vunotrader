import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null = null;

export function createClient() {
  if (browserClient) return browserClient;

  // Tenta carregar com os nomes padrão ou fallback do backend
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 
              process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY;

  if (!url || !key) {
    console.error("Erro de Inicialização Supabase (Client):", { 
      urlExists: !!url, 
      keyExists: !!key 
    });
    throw new Error(
      `Dados do projeto (URL e Key) são obrigatórios! Verifique o .env.local. Faltando: ${!url ? 'URL ' : ''}${!key ? 'KEY' : ''}`
    );
  }

  browserClient = createBrowserClient(url, key);

  return browserClient;
}
