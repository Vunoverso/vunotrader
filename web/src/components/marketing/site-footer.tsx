import Link from "next/link";

import { footerLinkGroups } from "@/lib/marketing-content";

export function SiteFooter() {
  const year = new Date().getFullYear();

  const renderFooterLink = (label: string, href: string) => {
    const mobileClasses =
      "rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-100";
    const desktopClasses = "md:border-none md:bg-transparent md:px-0 md:py-0 md:text-sm md:font-normal md:text-slate-600 md:hover:text-slate-950";
    const className = `${mobileClasses} ${desktopClasses}`;

    if (href.startsWith("/")) {
      return (
        <Link key={label} href={href} className={className}>
          {label}
        </Link>
      );
    }

    return (
      <a key={label} href={href} className={className}>
        {label}
      </a>
    );
  };

  return (
    <footer className="border-t border-sky-100 bg-white/90">
      <div className="mx-auto w-full max-w-6xl px-6 py-14 lg:px-8">
        <div className="grid gap-8 md:grid-cols-[1.3fr_1fr_1fr_1fr]">
          <div>
            <Link href="/" className="text-xl font-semibold tracking-tight text-slate-950">
              Vuno Trader
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-7 text-slate-600">
              Plataforma SaaS para operacao de robo trader com IA, memoria inteligente, trilha auditavel e governanca.
            </p>
            <a
              href="#top"
              className="mt-5 inline-flex rounded-full border border-slate-300 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-700 transition hover:border-slate-500"
            >
              Voltar ao topo
            </a>
          </div>

          {footerLinkGroups.map((group) => (
            <div key={group.title}>
              <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-800">{group.title}</h3>
              <div className="mt-4 flex flex-wrap gap-2 md:flex-col md:gap-3">
                {group.links.map((link) => renderFooterLink(link.label, link.href))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-sky-100 pt-6 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <p>© {year} Vuno Trader. Todos os direitos reservados.</p>
          <p>
            Desenvolvido por{" "}
            <a
              href="https://www.vunostudio.com.br"
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-slate-900 underline decoration-sky-300 decoration-2 underline-offset-4"
            >
              Vuno Studio
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}