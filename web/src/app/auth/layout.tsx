import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Vuno Trader — Acesso",
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-[#f0f6ff]">
      {/* Topo minimalista */}
      <header className="flex items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 group">
          <span className="w-8 h-8 rounded-lg bg-sky-600 flex items-center justify-center text-white font-bold text-sm select-none">
            VT
          </span>
          <span className="font-semibold text-slate-800 tracking-tight">
            Vuno Trader
          </span>
        </Link>
        <span className="text-xs text-slate-400">
          Plataforma SaaS de Robô Trader
        </span>
      </header>

      {/* Conteúdo centralizado */}
      <main className="flex-1 flex items-center justify-center px-4 py-10">
        {children}
      </main>

      {/* Footer mínimo */}
      <footer className="py-4 text-center text-xs text-slate-400">
        © 2026 Vuno Trader · Desenvolvido por{" "}
        <a
          href="https://www.vunostudio.com.br"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sky-500 hover:underline"
        >
          Vuno Studio
        </a>
      </footer>
    </div>
  );
}
