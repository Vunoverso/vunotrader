import Link from "next/link";

export default function PlanGateCard({
  moduleName,
}: {
  moduleName: string;
}) {
  return (
    <div className="mx-auto max-w-4xl rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6">
      <h1 className="text-lg font-semibold text-amber-200">Acesso bloqueado para {moduleName}</h1>
      <p className="mt-2 text-sm text-amber-100/90">
        Seu período de teste permite acessar o painel, mas este módulo só libera com plano ativo.
      </p>
      <div className="mt-4 flex items-center gap-3">
        <Link
          href="/app/assinatura"
          className="rounded-lg border border-amber-400/40 bg-amber-400/20 px-4 py-2 text-sm font-semibold text-amber-100 transition-colors hover:bg-amber-400/30"
        >
          Ver planos e ativar
        </Link>
        <Link
          href="/app/dashboard"
          className="rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 transition-colors hover:bg-slate-800"
        >
          Voltar ao dashboard
        </Link>
      </div>
    </div>
  );
}
