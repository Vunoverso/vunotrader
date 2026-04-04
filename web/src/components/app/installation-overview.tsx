import Link from "next/link";

interface InstallationAccess {
  hasActivePlan: boolean;
  isTrialing: boolean;
  trialDaysLeft: number;
  features: Record<string, boolean>;
}

const setupFlow = [
  {
    step: "01",
    title: "Gerar uma instância nova",
    description:
      "Cada download cria um pacote isolado, com bridge própria, token embutido e identificação pronta para aquela máquina.",
  },
  {
    step: "02",
    title: "Iniciar o agent-local do pacote",
    description:
      "O iniciador do pacote sobe a bridge local e usa vuno-agent.exe quando o binário já está presente e válido.",
  },
  {
    step: "03",
    title: "Copiar o conector para o MT5",
    description:
      "No terminal MetaTrader 5, copie VunoRemoteBridge.mq5 e a pasta vuno-bridge para MQL5/Experts e compile o EA.",
  },
  {
    step: "04",
    title: "Preencher só o bridge root",
    description:
      "No gráfico, o EA recebe apenas o InpBridgeRoot informado pelo pacote. URL, token e IDs já seguem dentro do runtime local.",
  },
];

const zipItems = [
  "runtime/config.json já preenchido com a chave da instância",
  "agent-local com iniciador para Windows e fallback controlado",
  "EA VunoRemoteBridge.mq5 e a pasta vuno-bridge",
  "LEIA-PRIMEIRO com sequência operacional da instalação",
];

const retiredItems = [
  "Configurar WebRequest ou URL permitida dentro do MT5",
  "Copiar UserID, OrganizationID, RobotID ou RobotToken no gráfico",
  "Manter uma tela global de parâmetros igual para todos os robôs",
];

const faqItems = [
  {
    question: "O bot já vem em executável?",
    answer:
      "O pacote já vem preparado para iniciar pelo executável local quando agent-local/dist/vuno-agent.exe está presente e atualizado. Se esse binário não estiver disponível, o iniciador cai para o modo Python do próprio pacote.",
  },
  {
    question: "A chave já vem junto com o pacote?",
    answer:
      "Sim. O runtime/config.json sai preenchido com a chave da instância e os identificadores necessários. No MT5, você não cola token; só informa o InpBridgeRoot do pacote.",
  },
  {
    question: "Onde entram os parâmetros de cada robô?",
    answer:
      "A rota global de parâmetros foi descontinuada para não sustentar um modelo errado. A próxima etapa é levar a configuração fina para a própria instância do robô, em vez de reaproveitar um formulário único por usuário.",
  },
];

export default function InstallationOverview({ access }: { access: InstallationAccess | null }) {
  const visualHybridEnabled = Boolean(
    access?.features?.["robot.visual_hybrid"] && access?.features?.["robot.visual_shadow"]
  );

  const planLine = access?.hasActivePlan
    ? "Seu plano atual já libera a criação de instâncias operacionais dentro do fluxo oficial por pacote."
    : access?.isTrialing
    ? `Seu trial segue ativo por ${access.trialDaysLeft} dia(s). Gere a instância, valide em demo e só depois avance para operação plena.`
    : "A instalação pode ser preparada agora, mas os módulos operacionais continuam sujeitos à ativação do plano.";

  return (
    <>
      <section className="relative overflow-hidden rounded-[28px] border border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(16,185,129,0.16),_transparent_28%),#020617] p-6 md:p-8">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-[linear-gradient(180deg,rgba(56,189,248,0.12),rgba(2,6,23,0))] blur-3xl lg:block" />
        <div className="relative grid gap-6 lg:grid-cols-[1.35fr_0.95fr]">
          <div>
            <span className="inline-flex rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-200">
              Pacote por instância
            </span>
            <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-tight text-white md:text-4xl">
              Instalação MT5 sem token manual no gráfico
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 md:text-base">
              O fluxo oficial agora nasce por instância. Cada robô tem um pacote próprio, com chave embutida,
              bridge local e inicialização preferencial pelo executável do agent-local quando ele já está disponível.
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              {[
                "Chave embutida no pacote",
                "Bridge local entre MT5 e backend",
                "vuno-agent.exe quando disponível",
                visualHybridEnabled ? "Shadow visual liberado" : "Shadow visual por plano",
              ].map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-slate-700 bg-slate-950/70 px-3 py-1 text-xs text-slate-300"
                >
                  {item}
                </span>
              ))}
            </div>

            <p className="mt-5 max-w-2xl text-sm text-slate-400">{planLine}</p>

            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="#gerar-pacote"
                className="rounded-xl border border-sky-400/30 bg-sky-400/15 px-4 py-2 text-sm font-semibold text-sky-100 transition hover:bg-sky-400/25"
              >
                Gerar pacote
              </Link>
              <Link
                href="/app/dashboard"
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800"
              >
                Ver heartbeat
              </Link>
              <Link
                href="/app/auditoria"
                className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800"
              >
                Abrir auditoria
              </Link>
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-700/80 bg-slate-950/75 p-5 shadow-[0_20px_80px_rgba(2,6,23,0.45)]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Dentro do zip</p>
            <div className="mt-4 space-y-3">
              {zipItems.map((item) => (
                <div key={item} className="rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-sm text-slate-200">
                  {item}
                </div>
              ))}
            </div>
            <div className="mt-5 rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200">Parâmetros globais removidos</p>
              <p className="mt-2 text-sm leading-6 text-amber-50/90">
                A rota antiga foi descontinuada. O próximo passo do produto é levar ajustes finos para cada instância,
                sem voltar ao modelo único por usuário.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[26px] border border-slate-800 bg-slate-900 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Sequência oficial</p>
          <div className="mt-5 space-y-3">
            {setupFlow.map((item) => (
              <article key={item.step} className="flex gap-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-sky-500/15 text-sm font-semibold text-sky-200">
                  {item.step}
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-100">{item.title}</h2>
                  <p className="mt-1 text-sm leading-6 text-slate-400">{item.description}</p>
                </div>
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <section className="rounded-[26px] border border-slate-800 bg-slate-900 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Não precisa mais</p>
            <div className="mt-4 space-y-3">
              {retiredItems.map((item) => (
                <div key={item} className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-3 text-sm text-slate-300">
                  {item}
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[26px] border border-emerald-500/20 bg-emerald-500/10 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-200">Depois da instalação</p>
            <div className="mt-4 grid gap-3">
              {[
                "Validar heartbeat recente no dashboard",
                "Operar primeiro em modo demo",
                "Conferir auditoria e shadow visual quando o plano habilitar",
              ].map((item) => (
                <div key={item} className="rounded-2xl border border-emerald-400/20 bg-slate-950/35 px-4 py-3 text-sm text-emerald-50">
                  {item}
                </div>
              ))}
            </div>
          </section>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-[24px] border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Instância isolada</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Cada pacote representa um robô específico. Isso reduz colisão entre máquinas, bridges e tokens compartilhados.
          </p>
        </article>
        <article className="rounded-[24px] border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Executável primeiro</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            O iniciador local tenta subir o runtime empacotado antes de depender de instalação manual de Python na ponta.
          </p>
        </article>
        <article className="rounded-[24px] border border-slate-800 bg-slate-900 p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Próxima entrega</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            Configuração operacional por instância. O objetivo é cada robô carregar seus próprios parâmetros, sem reaproveitar um formulário global.
          </p>
        </article>
      </section>

      <section className="rounded-[26px] border border-slate-800 bg-slate-900 p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Dúvidas frequentes</p>
        <div className="mt-4 space-y-3">
          {faqItems.map((item, index) => (
            <details key={item.question} open={index === 0} className="group rounded-2xl border border-slate-800 bg-slate-950/70">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4 text-sm font-semibold text-slate-100">
                <span>{item.question}</span>
                <span className="text-slate-500 transition-transform group-open:rotate-45">+</span>
              </summary>
              <p className="px-4 pb-4 text-sm leading-6 text-slate-400">{item.answer}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  );
}