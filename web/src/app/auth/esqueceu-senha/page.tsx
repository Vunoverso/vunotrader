"use client";

import { useState } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

type Step = "form" | "sent";

export default function EsqueceuSenhaPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("form");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setError("Informe um e-mail válido.");
      return;
    }
    setError(null);
    setLoading(true);

    const supabase = createClient();
    const { error: authError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/redefinir-senha`,
    });

    setLoading(false);

    if (authError) {
      setError("Não foi possível enviar o e-mail. Tente novamente.");
      return;
    }

    setStep("sent");
  }

  if (step === "sent") {
    return (
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10 text-center">
          {/* Ícone */}
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-sky-50 text-sky-600">
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
              <rect width="20" height="16" x="2" y="4" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
          </div>

          <h1 className="text-xl font-bold text-slate-800 mb-2">
            Verifique seu e-mail
          </h1>
          <p className="text-sm text-slate-500 mb-2">
            Enviamos um link de recuperação para
          </p>
          <p className="text-sm font-semibold text-slate-700 mb-6">{email}</p>
          <p className="text-xs text-slate-400 mb-8">
            O link expira em 30 minutos. Verifique também a pasta de spam.
          </p>

          <Link
            href="/auth/login"
            className="inline-block rounded-lg bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 transition"
          >
            Voltar para o login
          </Link>

          <p className="mt-5 text-xs text-slate-400">
            Não recebeu?{" "}
            <button
              onClick={() => setStep("form")}
              className="text-sky-600 hover:underline"
            >
              Tentar novamente
            </button>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      {/* Card */}
      <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10">
        {/* Título */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">
            Recuperar senha
          </h1>
          <p className="text-sm text-slate-500">
            Informe seu e-mail e enviaremos um link para redefinir sua senha
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
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              E-mail da sua conta
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

          <button
            type="submit"
            disabled={loading || !email}
            className="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition focus:outline-none focus:ring-2 focus:ring-sky-500/40"
          >
            {loading ? "Enviando…" : "Enviar link de recuperação"}
          </button>
        </form>

        {/* Voltar */}
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
