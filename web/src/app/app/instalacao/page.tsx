import Link from "next/link";

const steps = [
  {
    title: "1) Instalar o MetaTrader 5",
    description:
      "Instale o MT5 da sua corretora (ou da MetaQuotes), faça login em uma conta demo e mantenha o terminal aberto durante a operação.",
  },
  {
    title: "2) Baixar e copiar o robô (EA)",
    description:
      "No MT5, abra Arquivo > Abrir pasta de dados > MQL5 > Experts e copie o arquivo do EA da Vuno Trader (.ex5).",
  },
  {
    title: "3) Gerar token de conexão",
    description:
      "No painel da Vuno Trader, gere sua chave de conexão e salve com segurança. Esse token vincula o MT5 à sua conta.",
  },
  {
    title: "4) Configurar o EA no gráfico",
    description:
      "Arraste o EA para o gráfico, preencha token, modo (observer/demo/real), símbolo e timeframe. Habilite AutoTrading no MT5.",
  },
  {
    title: "5) Validar status no painel",
    description:
      "Volte ao Dashboard e confira se Brain Python e MT5 aparecem como conectados. Faça primeiro teste sempre em modo demo.",
  },
];

const checklist = [
  "Conta demo ativa na corretora",
  "MT5 aberto e AutoTrading habilitado",
  "EA da Vuno Trader em MQL5/Experts",
  "Token configurado no EA",
  "Modo DEMO selecionado para teste inicial",
  "Status conectado no Dashboard",
];

const faqItems = [
  {
    question: "Se eu mudar parâmetros no painel, preciso instalar tudo de novo?",
    answer:
      "Não. Alterações de risco, metas e regras no painel não exigem reinstalação do MT5 nem do EA. Basta salvar os parâmetros; o robô aplica no próximo ciclo de leitura.",
  },
  {
    question: "Quando preciso mexer no EA novamente?",
    answer:
      "Somente quando trocar token, conta, ambiente ou versão do robô (.ex5). Nesses casos, atualize os campos no EA ou substitua o arquivo no MQL5/Experts.",
  },
  {
    question: "Atualizei o robô para uma versão nova. O que fazer?",
    answer:
      "Substitua o arquivo .ex5 na pasta MQL5/Experts, recarregue o EA no gráfico e valide no Dashboard se o status voltou para conectado.",
  },
];

export default function InstalacaoPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Instalação e Conexão com MetaTrader 5</h1>
            <p className="mt-2 text-sm text-slate-400">
              Guia oficial para conectar sua conta MT5 ao Vuno Trader sem instalar Python local.
            </p>
          </div>
          <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300">
            Onboarding
          </span>
        </div>
      </header>

      <section className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-emerald-300">Cereja do bolo</h2>
        <p className="mt-2 text-sm text-emerald-100">
          Comece por aqui: baixe o EA, copie para o MT5 e conecte em modo demo.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a
            href="/downloads/VunoTrader_v2.mq5"
            download
            className="rounded-lg border border-emerald-400/30 bg-emerald-500/20 px-4 py-2 text-sm font-semibold text-emerald-100 hover:bg-emerald-500/30 transition-colors"
          >
            Baixar EA (.mq5)
          </a>
          <span className="rounded-lg border border-slate-700 px-4 py-2 text-xs text-slate-300">
            Depois de baixar: MT5 {'>'} Arquivo {'>'} Abrir pasta de dados {'>'} MQL5 {'>'} Experts
          </span>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Sem complicação</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-300">
            O MT5 fica no seu computador. O painel e a inteligência ficam na Vuno Trader.
            Você só conecta uma vez e depois ajusta parâmetros direto no painel.
          </p>
          <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-200">
            Sempre inicie em modo demo. Promova para real apenas após validação de risco e consistência.
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Checklist rápido</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            {checklist.map((item) => (
              <li key={item} className="flex items-start gap-2">
                <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-500">Passo a passo rápido</h2>
        <div className="space-y-3">
          {steps.map((step) => (
            <article key={step.title} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <h3 className="text-sm font-semibold text-slate-100">{step.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-400">{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Próximas ações</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/app/parametros"
            className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-300 hover:bg-sky-500/20 transition-colors"
          >
            Configurar parâmetros
          </Link>
          <Link
            href="/app/dashboard"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
          >
            Ver status no dashboard
          </Link>
          <Link
            href="/app/auditoria"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
          >
            Abrir auditoria
          </Link>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Dúvidas frequentes</h2>
        <div className="mt-4 space-y-3">
          {faqItems.map((item, idx) => (
            <details
              key={item.question}
              open={idx === 0}
              className="group rounded-xl border border-slate-800 bg-slate-950/60"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-semibold text-slate-100 marker:content-none">
                <span>{item.question}</span>
                <span className="text-slate-500 transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="px-4 pb-4 text-sm leading-relaxed text-slate-400">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
