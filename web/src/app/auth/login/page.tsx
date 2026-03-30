"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (authError) {
      const status = (authError as { status?: number }).status;
      if (status === 429) {
        setError("Muitas tentativas de login. Aguarde alguns minutos antes de tentar novamente.");
      } else if (authError.message?.toLowerCase().includes("email not confirmed")) {
        setError("Confirme seu e-mail antes de fazer login. Verifique sua caixa de entrada.");
      } else {
        setError("Credenciais inválidas. Verifique seu e-mail e senha.");
      }
      return;
    }

    router.push("/app/dashboard");
    router.refresh();
  }

  return (
    <div className="w-full max-w-md">
      {/* Card */}
      <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10">
        {/* Título */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">
            Entrar na plataforma
          </h1>
          <p className="text-sm text-slate-500">
            Acesse sua conta para operar seus robôs
          </p>
        </div>

        {/* Erro */}
        {error && (
          <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Formulário */}
        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          {/* Email */}
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              E-mail
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
            />
          </div>

          {/* Senha */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-slate-700"
              >
                Senha
              </label>
              <Link
                href="/auth/esqueceu-senha"
                className="text-xs text-sky-600 hover:text-sky-700 hover:underline"
              >
                Esqueceu a senha?
              </Link>
            </div>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 pr-10 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition"
                aria-label={showPassword ? "Ocultar senha" : "Mostrar senha"}
              >
                {showPassword ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Botão principal */}
          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition focus:outline-none focus:ring-2 focus:ring-sky-500/40"
          >
            {loading ? "Entrando…" : "Entrar"}
          </button>
        </form>

        {/* Divider */}
        <div className="my-6 flex items-center gap-3">
          <span className="flex-1 h-px bg-slate-100" />
          <span className="text-xs text-slate-400">ou</span>
          <span className="flex-1 h-px bg-slate-100" />
        </div>

        {/* Link para cadastro */}
        <p className="text-center text-sm text-slate-500">
          Ainda não tem conta?{" "}
          <Link
            href="/auth/cadastro"
            className="font-medium text-sky-600 hover:text-sky-700 hover:underline"
          >
            Crie gratuitamente
          </Link>
        </p>
      </div>

      {/* Segurança */}
      <p className="mt-4 text-center text-xs text-slate-400">
        Conexão segura · Dados criptografados em trânsito
      </p>
    </div>
  );
}
