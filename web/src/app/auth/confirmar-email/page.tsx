import Link from "next/link";

export default function ConfirmarEmailPage() {
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
          Confirme seu e-mail
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          Enviamos um link de confirmação para o seu e-mail.
          Clique no link para ativar sua conta e acessar a plataforma.
        </p>
        <p className="text-xs text-slate-400 mb-8">
          Verifique também a pasta de spam. O link expira em 24 horas.
        </p>

        <p className="mb-6 rounded-lg border border-sky-100 bg-sky-50 px-4 py-2.5 text-xs text-sky-700">
          Se a confirmação de e-mail estiver desativada no projeto, você pode ignorar este aviso e tentar entrar agora.
        </p>

        <Link
          href="/auth/login"
          className="inline-block rounded-lg bg-sky-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-sky-700 transition"
        >
          Ir para o login e tentar agora
        </Link>
      </div>
    </div>
  );
}
