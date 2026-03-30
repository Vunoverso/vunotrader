import { CtaBanner } from "@/components/marketing/cta-banner";
import { FaqAccordion } from "@/components/marketing/faq-accordion";
import { FeatureCard } from "@/components/marketing/feature-card";
import { MarketHeroBackground } from "@/components/marketing/market-hero-background";
import { MetricPill } from "@/components/marketing/metric-pill";
import { SectionShell } from "@/components/marketing/section-shell";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { AnimateOnView, StaggerContainer, StaggerItem } from "@/components/ui/animate-on-view";
import { faqItems, featureCards, heroMetrics, planCards, workflowSteps } from "@/lib/marketing-content";

// Icons
function BrainIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-1.5-2.29V8.5A2.5 2.5 0 0 1 9.5 6a2.5 2.5 0 0 1 0-4z"/>
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 1.5-2.29V8.5A2.5 2.5 0 0 0 14.5 6a2.5 2.5 0 0 0 0-4z"/>
    </svg>
  );
}
function BookIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
    </svg>
  );
}
function ChartIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  );
}

const iconMap: Record<string, React.ReactNode> = {
  brain: <BrainIcon />,
  book: <BookIcon />,
  chart: <ChartIcon />,
};

export default function Home() {
  return (
    <main className="flex-1 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.30),_transparent_30%),linear-gradient(180deg,#f8fcff_0%,#eef6ff_38%,#ffffff_100%)] text-slate-950">
      <SiteHeader />

      {/* HERO */}
      <section id="top" className="relative isolate overflow-hidden py-20 sm:py-24">
        <MarketHeroBackground />

        <div className="relative z-10 mx-auto grid w-full max-w-6xl gap-12 px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
          <AnimateOnView direction="up" delay={0.05}>
            <div className="inline-flex rounded-full border border-sky-200 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-sky-800 shadow-sm">
              SaaS de robo trader com IA controlada
            </div>
            <h1 className="mt-8 max-w-4xl text-5xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-7xl">
              O ecossistema para operar, estudar e evoluir seu robô com mais critério.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
              Reúna MT5, cérebro Python, memória inteligente, painel SaaS e trilha auditável para levar o robô do demo ao real com governança.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <a
                href="/auth/cadastro"
                className="inline-flex items-center justify-center rounded-full bg-sky-700 px-6 py-3 text-sm font-semibold text-white transition hover:bg-sky-800 active:scale-95"
              >
                Criar conta e configurar robô
              </a>
              <a
                href="#recursos"
                className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white/80 px-6 py-3 text-sm font-semibold text-slate-800 transition hover:border-slate-400 hover:bg-white active:scale-95"
              >
                Ver arquitetura da plataforma
              </a>
            </div>
            <StaggerContainer className="mt-10 grid gap-4 sm:grid-cols-3" staggerDelay={0.08}>
              {heroMetrics.map((metric) => (
                <StaggerItem key={metric.value}>
                  <MetricPill value={metric.value} label={metric.label} />
                </StaggerItem>
              ))}
            </StaggerContainer>
          </AnimateOnView>

          <AnimateOnView direction="left" delay={0.18}>
            <div className="relative">
              <div className="absolute inset-x-8 top-8 h-40 rounded-full bg-cyan-300/40 blur-3xl" />
              <div className="relative overflow-hidden rounded-[36px] border border-white/70 bg-slate-950 p-6 text-white shadow-[0_32px_120px_rgba(15,23,42,0.28)]">
                <div className="flex items-center justify-between rounded-[28px] border border-white/10 bg-white/5 px-5 py-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-cyan-200">Modo ativo</p>
                    <p className="mt-2 text-2xl font-semibold">Demo supervisionado</p>
                  </div>
                  <div className="relative flex items-center gap-1.5 rounded-full bg-emerald-400/20 px-3 py-1 text-xs font-semibold text-emerald-200">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                    </span>
                    online
                  </div>
                </div>

                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-[28px] bg-white/6 p-5">
                    <p className="text-sm text-slate-300">Win rate observado</p>
                    <p className="mt-3 text-4xl font-semibold">68.4%</p>
                  </div>
                  <div className="rounded-[28px] bg-white/6 p-5">
                    <p className="text-sm text-slate-300">Análises da IA</p>
                    <p className="mt-3 text-4xl font-semibold">1.248</p>
                  </div>
                </div>

                <div className="mt-5 rounded-[28px] border border-cyan-300/20 bg-gradient-to-br from-cyan-400/15 to-sky-500/10 p-5">
                  <p className="text-sm text-cyan-100">Resumo operacional</p>
                  <p className="mt-3 text-lg leading-8 text-slate-100">
                    Cada trade gera contexto, motivo, risco, imagem, resultado e uma leitura de porque ganhou ou perdeu.
                  </p>
                </div>
              </div>
            </div>
          </AnimateOnView>
        </div>
      </section>

      {/* RECURSOS */}
      <SectionShell
        id="recursos"
        eyebrow="Recursos"
        title="Uma base única para operar, estudar e escalar"
        description="Componentes reutilizáveis para o site institucional e o app autenticado."
      >
        <StaggerContainer className="grid gap-6 lg:grid-cols-3" staggerDelay={0.12}>
          {featureCards.map((card) => (
            <StaggerItem key={card.title}>
              <FeatureCard
                title={card.title}
                description={card.description}
                icon={iconMap[card.iconKey]}
                gradient={card.gradient}
              />
            </StaggerItem>
          ))}
        </StaggerContainer>
      </SectionShell>

      {/* COMO FUNCIONA */}
      <SectionShell
        id="como-funciona"
        eyebrow="Fluxo"
        title="Um caminho claro do estudo ao real"
        description="O produto foi pensado para evitar salto cego para a conta real e reforçar rastreabilidade em cada etapa."
        className="bg-white/55"
      >
        <StaggerContainer className="grid gap-6 lg:grid-cols-3" staggerDelay={0.1}>
          {workflowSteps.map((step) => (
            <StaggerItem key={step.eyebrow}>
              <article className="rounded-[28px] border border-sky-100 bg-white p-7 shadow-[0_18px_60px_rgba(15,23,42,0.06)] transition-shadow hover:shadow-[0_24px_70px_rgba(15,23,42,0.11)]">
                <p className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-700">{step.eyebrow}</p>
                <h3 className="mt-4 text-2xl font-semibold text-slate-950">{step.title}</h3>
                <p className="mt-4 text-base leading-7 text-slate-600">{step.description}</p>
              </article>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </SectionShell>

      {/* PLANOS */}
      <SectionShell
        id="planos"
        eyebrow="Planos"
        title="Estrutura SaaS pronta para onboarding e escala"
        description="Planos flexíveis para validar, operar e escalar seu robô trader com IA."
      >
        <StaggerContainer className="grid gap-6 lg:grid-cols-3" staggerDelay={0.1}>
          {planCards.map((plan) => (
            <StaggerItem key={plan.name}>
              <article
                className={`group relative rounded-[30px] p-7 transition-transform duration-300 hover:-translate-y-1 ${
                  plan.featured
                    ? "border border-sky-500 bg-slate-950 text-white shadow-[0_20px_80px_rgba(14,116,144,0.25)]"
                    : "border border-white/70 bg-white/85 text-slate-950 shadow-[0_20px_80px_rgba(15,23,42,0.08)]"
                }`}
              >
                {plan.featured && (
                  <div className="absolute inset-0 rounded-[30px] bg-sky-500/5 opacity-0 transition-opacity group-hover:opacity-100" />
                )}
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="text-2xl font-semibold">{plan.name}</h3>
                    <p className={`mt-3 text-sm leading-7 ${plan.featured ? "text-slate-300" : "text-slate-600"}`}>
                      {plan.description}
                    </p>
                  </div>
                  {plan.featured ? (
                    <span className="rounded-full bg-sky-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sky-200">
                      destaque
                    </span>
                  ) : null}
                </div>
                <p className="mt-8 text-4xl font-semibold tracking-tight">{plan.price}</p>
                <p className={`text-sm ${plan.featured ? "text-slate-400" : "text-slate-400"}`}>/mês</p>
                <div className="mt-6 space-y-3">
                  {plan.bullets.map((bullet) => (
                    <div key={bullet} className={`flex items-center gap-2.5 rounded-2xl px-4 py-3 text-sm ${plan.featured ? "bg-white/8 text-slate-100" : "bg-slate-50 text-slate-700"}`}>
                      <svg className={`h-4 w-4 flex-shrink-0 ${plan.featured ? "text-sky-400" : "text-sky-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {bullet}
                    </div>
                  ))}
                </div>
                <a
                  href="/auth/cadastro"
                  className={`mt-7 block w-full rounded-full py-3 text-center text-sm font-semibold transition active:scale-95 ${
                    plan.featured
                      ? "bg-sky-500 text-white hover:bg-sky-400"
                      : "border border-slate-300 text-slate-800 hover:border-slate-400 hover:bg-white"
                  }`}
                >
                  Começar agora
                </a>
              </article>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </SectionShell>

      {/* FAQ */}
      <SectionShell
        id="faq"
        eyebrow="FAQ"
        title="Perguntas que influenciam a adoção"
        description="Respostas diretas sobre o funcionamento, segurança e modelo de dados da plataforma."
        className="bg-white/55"
      >
        <AnimateOnView direction="up">
          <FaqAccordion items={faqItems} />
        </AnimateOnView>
      </SectionShell>

      <AnimateOnView direction="up">
        <CtaBanner />
      </AnimateOnView>
      <SiteFooter />
    </main>
  );
}
