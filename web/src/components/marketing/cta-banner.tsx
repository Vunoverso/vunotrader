export function CtaBanner() {
  return (
    <section className="pb-24">
      <div className="mx-auto w-full max-w-6xl px-6 lg:px-8">
        <div className="overflow-hidden rounded-[36px] bg-[linear-gradient(135deg,#082f49_0%,#0f766e_55%,#f0f9ff_100%)] p-8 shadow-[0_24px_80px_rgba(8,47,73,0.24)] sm:p-12">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-100">Pronto para avancar</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Transforme seu robo em uma operacao SaaS com memoria, seguranca e historico real.
            </h2>
            <p className="mt-4 max-w-2xl text-lg leading-8 text-cyan-50/90">
              Comece com observer e demo, conecte seu Supabase, acompanhe o aprendizado e suba para o real com governanca.
            </p>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row">
              <a
                href="/auth/cadastro"
                className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-50"
              >
                Criar conta
              </a>
              <a
                href="/auth/login"
                className="inline-flex items-center justify-center rounded-full border border-white/40 px-6 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                Entrar na plataforma
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}