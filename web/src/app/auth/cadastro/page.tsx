"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function CadastroPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
    acceptTerms: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ type: "info" | "success"; message: string } | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();

  function update(field: keyof typeof form, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function validate(): string | null {
    if (!form.name.trim()) return "Informe seu nome completo.";
    if (!form.email.includes("@")) return "Informe um e-mail válido.";
    if (form.password.length < 8) return "A senha deve ter pelo menos 8 caracteres.";
    if (form.password !== form.confirmPassword) return "As senhas não coincidem.";
    if (!form.acceptTerms) return "Você precisa aceitar os Termos de Uso para continuar.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const err = validate();
    if (err) {
      setError(err);
      setNotice(null);
      return;
    }
    setError(null);
    setNotice({ type: "info", message: "Estamos criando sua conta. Aguarde alguns segundos..." });
    setLoading(true);

    const supabase = createClient();
    const { data, error: authError } = await supabase.auth.signUp({
      email: form.email,
      password: form.password,
      options: {
        data: { full_name: form.name },
      },
    });

    setLoading(false);

    if (authError) {
      setNotice(null);
      const status = (authError as { status?: number }).status;
      if (status === 429) {
        setError("Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.");
      } else if (authError.message?.toLowerCase().includes("already registered")) {
        setError("Este e-mail já está cadastrado. Tente fazer login.");
      } else if (authError.message?.toLowerCase().includes("password")) {
        setError("A senha não atende aos requisitos mínimos de segurança.");
      } else {
        setError("Não foi possível criar a conta. Verifique os dados e tente novamente.");
      }
      return;
    }

    setNotice({ type: "success", message: "Conta criada. Tentando login automático..." });
    await new Promise((resolve) => setTimeout(resolve, 700));

    if (data.session) {
      router.push("/app/dashboard");
      router.refresh();
      return;
    }

    const { error: loginAfterSignupError } = await supabase.auth.signInWithPassword({
      email: form.email,
      password: form.password,
    });

    if (!loginAfterSignupError) {
      router.push("/app/dashboard");
      router.refresh();
      return;
    }

    const loginMsg = loginAfterSignupError.message?.toLowerCase() ?? "";
    if (loginMsg.includes("email not confirmed")) {
      router.push("/auth/confirmar-email");
      return;
    }

    router.push("/auth/login?novo=1");
  }

  const canSubmit =
    form.name && form.email && form.password && form.confirmPassword && form.acceptTerms;

  return (
    <div className="w-full max-w-md">
      {/* Card */}
      <div className="bg-white rounded-2xl shadow-md border border-slate-100 px-8 py-10">
        {/* Título */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-800 mb-1">
            Criar sua conta
          </h1>
          <p className="text-sm text-slate-500">
            Comece a operar com IA em minutos, sem cartão de crédito
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
          {/* Nome completo */}
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              Nome completo
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              required
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              placeholder="João Silva"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
            />
          </div>

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
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              placeholder="seu@email.com"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
            />
          </div>

          {/* Senha */}
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              Senha
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="Mínimo 8 caracteres"
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

          {/* Confirmar senha */}
          <div>
            <label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-slate-700 mb-1.5"
            >
              Confirmar senha
            </label>
            <div className="relative">
              <input
                id="confirmPassword"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                value={form.confirmPassword}
                onChange={(e) => update("confirmPassword", e.target.value)}
                placeholder="Repita a senha"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 pr-10 text-sm text-slate-800 placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/20 focus:outline-none transition"
              />
            </div>
          </div>

          {/* Aceitar termos */}
          <div className="flex items-start gap-3 pt-1">
            <input
              id="acceptTerms"
              type="checkbox"
              required
              checked={form.acceptTerms}
              onChange={(e) => update("acceptTerms", e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer accent-sky-600"
            />
            <label
              htmlFor="acceptTerms"
              className="text-sm text-slate-600 leading-snug cursor-pointer"
            >
              Li e aceito os{" "}
              <Link
                href="/termos"
                target="_blank"
                className="text-sky-600 hover:underline font-medium"
              >
                Termos de Uso
              </Link>{" "}
              e a{" "}
              <Link
                href="/politica-privacidade"
                target="_blank"
                className="text-sky-600 hover:underline font-medium"
              >
                Política de Privacidade
              </Link>
            </label>
          </div>

          {/* Botão principal */}
          <button
            type="submit"
            disabled={loading || !canSubmit}
            className="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition focus:outline-none focus:ring-2 focus:ring-sky-500/40 mt-1"
          >
            {loading ? "Criando conta…" : "Criar conta grátis"}
          </button>

          {notice && (
            <div
              role="status"
              aria-live="polite"
              className={`rounded-lg border px-4 py-2.5 text-sm ${
                notice.type === "success"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-sky-200 bg-sky-50 text-sky-700"
              }`}
            >
              {notice.message}
            </div>
          )}
        </form>

        {/* Divider */}
        <div className="my-6 flex items-center gap-3">
          <span className="flex-1 h-px bg-slate-100" />
          <span className="text-xs text-slate-400">já tem conta?</span>
          <span className="flex-1 h-px bg-slate-100" />
        </div>

        <p className="text-center text-sm text-slate-500">
          <Link
            href="/auth/login"
            className="font-medium text-sky-600 hover:text-sky-700 hover:underline"
          >
            Entrar na minha conta
          </Link>
        </p>
      </div>

      <p className="mt-4 text-center text-xs text-slate-400">
        Conexão segura · Dados criptografados em trânsito
      </p>
    </div>
  );
}
