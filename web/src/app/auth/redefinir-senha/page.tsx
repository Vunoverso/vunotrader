"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

type Step = "loading" | "form" | "success" | "invalid";

export default function RedefinirSenhaPage() {
  const [step, setStep] = useState<Step>("loading");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // O Supabase processa o token da URL automaticamente via onAuthStateChange
    const supabase = createClient();
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY") {
        setStep("form");
      } else if (event === "SIGNED_IN") {
        // token já resgatado antes — continua no form
        setStep("form");
      }
    });

    // Timeout: se em 5s o Supabase não disparar o evento, o link é inválido/expirado
    const timeout = setTimeout(() => {
      setStep((prev) => (prev === "loading" ? "invalid" : prev));
    }, 5000);

    return () => {
      listener.subscription.unsubscribe();
      clearTimeout(timeout);
    };
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (password !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: updateError } = await supabase.auth.updateUser({ password });

    setLoading(false);

    if (updateError) {
      setError("Não foi possível redefinir a senha. O link pode ter expirado.");
      return;
    }

    setStep("success");

    setTimeout(() => {
      router.push("/app/dashboard");
      router.refresh();
    }, 2500);
  }

  // ── Estados da página ───────────────────────────────────────

  if (step === "loading") {
    return (
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-16 text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-sky-200 border-t-sky-600" />
          <p className="text-sm text-slate-500">Validando seu link…</p>
        </div>
      </div>
    );
  }

  if (step === "invalid") {
    return (
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10 text-center">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-red-50 text-red-500">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-7 w-7"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="m15 9-6 6M9 9l6 6" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800 mb-2">
            Link inválido ou expirado
          </h1>
          <p className="text-sm text-slate-500 mb-8">
            Este link de recuperação não é mais válido. Solicite um novo para
            continuar.
          </p>
          <Link
            href="/auth/esqueceu-senha"
            className="inline-block rounded-lg bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 transition"
          >
            Solicitar novo link
          </Link>
        </div>
      </div>
    );
  }

  if (step === "success") {
    return (
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10 text-center">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-green-50 text-green-600">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-7 w-7"
            >
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800 mb-2">
            Senha redefinida!
          </h1>
          <p className="text-sm text-slate-500">
            Sua senha foi atualizada com sucesso. Redirecionando para o
            painel…
          </p>
        </div>
      </div>
    );
  }

  // ── Formulário ──────────────────────────────────────────────
  return (
    <div className="w-full max-w-md">
      <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10">
        {/* Título */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">
            Nova senha
          </h1>
          <p className="text-sm text-slate-500">
            Escolha uma senha segura de pelo menos 8 caracteres
          </p>
        </div>

        {/* Erro */}
        {error && (
          <div className="mb-5 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              Nova senha
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Mínimo 8 caracteres"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
            />
          </div>

          <div>
            <label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              Confirmar nova senha
            </label>
            <input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repita a senha"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !password || !confirmPassword}
            className="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition focus:outline-none focus:ring-2 focus:ring-sky-500/40"
          >
            {loading ? "Salvando…" : "Redefinir senha"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <Link
            href="/auth/login"
            className="text-sm text-slate-500 hover:text-slate-700 hover:underline"
          >
            ← Voltar para o login
          </Link>
        </div>
      </div>

      <p className="mt-4 text-center text-xs text-slate-400">
        Conexão segura · Dados criptografados em trânsito
      </p>
    </div>
  );
}
