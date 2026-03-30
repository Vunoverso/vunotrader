"use client";

import { useEffect, useState } from "react";
import { navItems } from "@/lib/marketing-content";

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-40 border-b border-white/50 bg-white/70 backdrop-blur-xl transition-shadow duration-300 ${
        scrolled ? "shadow-[0_4px_24px_rgba(15,23,42,0.10)]" : ""
      }`}
    >
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4 lg:px-8">
        <a href="#top" className="text-lg font-semibold tracking-tight text-slate-950">
          Vuno Trader
        </a>
        <nav className="hidden items-center gap-8 md:flex">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-slate-600 transition hover:text-slate-950"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3">
          <a
            href="/auth/login"
            className="rounded-full px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Entrar
          </a>
          <a
            href="/auth/cadastro"
            className="rounded-full bg-slate-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 active:scale-95"
          >
            Testar plataforma
          </a>
        </div>
      </div>
      {/* Mobile nav pills */}
      <div className="border-t border-white/60 px-6 py-3 md:hidden">
        <div className="mx-auto flex max-w-6xl gap-2 overflow-x-auto pb-1">
          {navItems.map((item) => (
            <a
              key={`${item.href}-mobile`}
              href={item.href}
              className="whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
            >
              {item.label}
            </a>
          ))}
        </div>
      </div>
    </header>
  );
}
