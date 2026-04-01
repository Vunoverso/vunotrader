import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import Mt5ConnectionChecker from "@/components/app/mt5-connection-checker";
import Mt5CredentialsGenerator from "@/components/app/mt5-credentials-generator";
import Mt5RobotInstancesPanel from "@/components/app/mt5-robot-instances-panel";

const steps = [
  {
    title: "1) Instalar o MetaTrader 5",

    description:
      "Instale o MT5 da sua corretora (ou da MetaQuotes), faça login em uma conta demo e mantenha o terminal aberto durante a operação.",
  },
  {
    title: "2) Baixar e copiar o robô (EA)",
    description:
      "No MT5, abra Arquivo > Abrir pasta de dados > MQL5 > Experts e copie o arquivo do EA da Vuno Trader (.mq5 ou .ex5).",
  },
  {
    title: "3) Adicionar a URL do servidor nas configurações do MT5",
    description:
      "No MT5 vá em Ferramentas > Opções > Expert Advisors. Em 'URLs permitidas' adicione: https://vunotrader-api.onrender.com",
  },
  {
    title: "4) Gerar seu token de conexão",
    description:
      "Na seção abaixo, gere RobotID e RobotToken e salve com segurança. Essas credenciais vinculam o MT5 à sua conta.",
  },
  {
    title: "5) Configurar o EA no gráfico",
    description:
      "Arraste o EA para o gráfico. No campo BackendURL deixe: https://vunotrader-api.onrender.com — já vem preenchido. Preencha RobotID, RobotToken e escolha o modo (demo). Habilite AutoTrading.",
  },
  {
    title: "6) Validar status no painel",
    description:
      "Volte ao Dashboard e confira se o robô aparece como conectado. Faça o primeiro teste sempre em modo Demo.",
  },
];

const checklist = [
  "Conta demo ativa na corretora",
  "MT5 aberto e AutoTrading habilitado",
  "EA da Vuno Trader em MQL5/Experts",
  "URL do servidor colada no campo BackendURL do EA",
  "Token (RobotID e RobotToken) configurado no EA",
  "URL do servidor adicionada nas URLs permitidas do MT5",
  "Modo DEMO selecionado para teste inicial",
  "Status conectado no Dashboard",
];

const robotTypes = [
  {
    title: "Robô EA no MT5 (recomendado)",
    profile: "Onboarding simples e integrado ao painel",
    bestFor: "Quem quer o fluxo oficial com token, heartbeat, auditoria e gestão de instâncias.",
    howTo: [
      "Baixe o EA da Vuno Trader e copie para MQL5/Experts.",
      "Gere RobotID/RobotToken nesta página e preencha no EA.",
      "Anexe no gráfico, habilite AutoTrading e valide conexão no checker.",
    ],
  },
  {
    title: "Bot Python no CMD (avançado)",
    profile: "Controle local direto do terminal MT5",
    bestFor:
      "Quem quer operar por comandos no Windows, testar estratégia local ou usar run-engine no terminal.",
    howTo: [
      "Instale dependências: pip install -r brain-requirements.txt",
      "Verifique conexão: python scripts/mt5_cmd_bot.py status",
      "Rodar motor compartilhado: python scripts/mt5_cmd_bot.py run-engine --symbol EURUSD --timeframe M5 --volume 0.01 --dry-run",
    ],
  },
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

export default async function InstalacaoPage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

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
          Escolha a versão do robô (EA) que prefere baixar e copie para o seu MetaTrader 5:
        </p>
        <div className="mt-4 flex flex-wrap gap-4">
          <div className="space-y-2">
            <a
              href="/downloads/VunoTrader_v2.mq5"
              download
              className="flex items-center gap-2 rounded-lg border border-emerald-400/30 bg-emerald-500/20 px-4 py-3 text-sm font-semibold text-emerald-100 hover:bg-emerald-500/30 transition-colors"
            >
              <span className="text-lg">🤖</span>
              Baixar VunoTrader v2 (Simples)
            </a>
            <p className="text-[10px] text-slate-400 pl-1 italic">Recomendado para 1 ativo por gráfico</p>
          </div>

          <div className="space-y-2">
            <a
              href="/downloads/VunoScreener_v3.mq5"
              download
              className="flex items-center gap-2 rounded-lg border border-sky-400/30 bg-sky-500/20 px-4 py-3 text-sm font-semibold text-sky-100 hover:bg-sky-500/30 transition-colors"
            >
              <span className="text-lg">⚡</span>
              Baixar VunoScreener v3 (Multi-Ativos)
            </a>
            <p className="text-[10px] text-slate-400 pl-1 italic">Várias moedas em um único robô</p>
          </div>
        </div>
        <div className="mt-6 border-t border-emerald-500/10 pt-4">
          <span className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-2 text-xs text-slate-300">
            Caminho no MT5: Arquivo {'>'} Abrir pasta de dados {'>'} MQL5 {'>'} Experts
          </span>
        </div>
      </section>

      {/* ── URL do Servidor Cloud ─────────────────────────────────────── */}
      <section className="rounded-2xl border border-sky-500/30 bg-slate-900 p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="text-2xl">🌐</span>
          <div>
            <h2 className="text-base font-bold text-slate-100">URL do Servidor Vuno</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              O robô fala diretamente com este endereço — não precisa de Python instalado no seu PC.
            </p>
          </div>
        </div>

        {/* URL para copiar */}
        <div className="flex items-center gap-3 rounded-xl border border-sky-500/40 bg-sky-950/40 px-4 py-3">
          <code className="flex-1 text-sm font-mono text-sky-300 select-all">
            https://vunotrader-api.onrender.com
          </code>
          <span className="text-xs text-slate-500 shrink-0">clique e selecione para copiar</span>
        </div>

        {/* Passo a passo onde colocar no MT5 */}
        <div className="mt-5 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Onde colocar no MT5 — passo a passo</p>

          <ol className="space-y-3">
            {[
              {
                n: "1",
                label: "Adicionar URL nas permissões do MT5",
                detail: 'No MT5, clique em Ferramentas → Opções → aba \'Expert Advisors\'. Em \'URLs permitidas\', clique em \'+\' e cole: https://vunotrader-api.onrender.com. Clique OK.',
                badge: "MT5 → Ferramentas → Opções → Expert Advisors",
              },
              {
                n: "2",
                label: "Campo BackendURL no EA",
                detail: 'Ao arrastar o EA para o gráfico, na aba \'Inputs\', o campo BackendURL já vem preenchido com essa URL. Confira se está exatamente assim:',
                code: "https://vunotrader-api.onrender.com",
                badge: "EA → Inputs → BackendURL",
              },
              {
                n: "3",
                label: "Habilitar AutoTrading",
                detail: "No topo do MT5 certifique que o botão AutoTrading está verde (ativo). Sem isso o robô observa mas não executa.",
                badge: "MT5 → Barra superior → AutoTrading",
              },
            ].map((item) => (
              <li key={item.n} className="flex gap-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sky-600 text-xs font-bold text-white">
                  {item.n}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-100 text-sm">{item.label}</p>
                  <span className="inline-block mt-1 mb-2 rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400">
                    {item.badge}
                  </span>
                  <p className="text-sm text-slate-400 leading-relaxed">{item.detail}</p>
                  {'code' in item && (
                    <code className="mt-2 block rounded-lg border border-sky-500/30 bg-sky-950/40 px-3 py-2 text-xs font-mono text-sky-300 select-all">
                      {item.code}
                    </code>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <Mt5CredentialsGenerator />

      <Mt5RobotInstancesPanel />

      {/* Validação de conexão em tempo real */}
      {user && <Mt5ConnectionChecker userId={user.id} />}

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
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">Escolha o tipo de robô</h2>
        <p className="mt-2 text-sm text-slate-400">
          Você pode operar pelo fluxo oficial com EA no MT5 ou pelo controlador Python no CMD. Escolha conforme seu perfil.
        </p>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {robotTypes.map((type) => (
            <article key={type.title} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <h3 className="text-sm font-semibold text-slate-100">{type.title}</h3>
              <p className="mt-1 text-xs uppercase tracking-wider text-slate-500">{type.profile}</p>
              <p className="mt-2 text-sm text-slate-300">{type.bestFor}</p>

              <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
                <p className="text-[11px] uppercase tracking-wider text-slate-500">Como usar</p>
                <ul className="mt-2 space-y-2 text-sm text-slate-300">
                  {type.howTo.map((step) => (
                    <li key={step} className="flex items-start gap-2">
                      <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-sky-400" />
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          ))}
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
