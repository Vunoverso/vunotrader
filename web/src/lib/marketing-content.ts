export const navItems = [
  { label: "Recursos", href: "#recursos" },
  { label: "Como funciona", href: "#como-funciona" },
  { label: "Planos", href: "#planos" },
  { label: "FAQ", href: "#faq" },
];

export const heroMetrics = [
  { value: "Demo-first", label: "Aprende primeiro em ambiente seguro" },
  { value: "RLS", label: "Isolamento por tenant no banco" },
  { value: "IA + MT5", label: "Execucao automatica com rastreio" },
];

export const featureCards = [
  {
    title: "Cerebro externo auditavel",
    description:
      "Toda decisao do robo pode carregar contexto, confianca, risco sugerido e pos-analise para win e loss.",
    iconKey: "brain",
    gradient: "from-violet-500 to-indigo-700",
  },
  {
    title: "Estudos em video e PDF",
    description:
      "O usuario adiciona URLs, PDFs e materiais tecnicos para construir uma base de conhecimento pesquisavel.",
    iconKey: "book",
    gradient: "from-cyan-500 to-sky-700",
  },
  {
    title: "Operacao SaaS pronta para crescer",
    description:
      "Login, administracao da conta, planos, billing, parametros do robo e visao consolidada do uso de IA.",
    iconKey: "chart",
    gradient: "from-emerald-500 to-teal-700",
  },
];

export const workflowSteps = [
  {
    eyebrow: "01",
    title: "Configurar conta e estrategia",
    description:
      "Defina metas, risco, ativos, horarios e modo observer, demo ou real em uma camada controlada por tenant.",
  },
  {
    eyebrow: "02",
    title: "Alimentar a memoria do robo",
    description:
      "Envie estudos, videos, PDFs e feedback operacional para o cerebro construir contexto e analises melhores.",
  },
  {
    eyebrow: "03",
    title: "Acompanhar e promover modelos",
    description:
      "Use dashboard, auditoria e regras de promocao para levar somente versoes validadas do demo para o real.",
  },
];

export const planCards = [
  {
    name: "Starter",
    price: "R$ 99",
    description: "Para validar o robo com foco em observacao, demo e onboarding rapido.",
    bullets: ["1 robo", "1 usuario admin", "limite inicial de IA", "dashboard base"],
  },
  {
    name: "Pro",
    price: "R$ 249",
    description: "Para operacao estruturada com mais usuarios, mais IA e trilha mais forte de auditoria.",
    bullets: ["multiplos robos", "mais membros", "analise IA ampliada", "modulo de estudos"],
    featured: true,
  },
  {
    name: "Scale",
    price: "R$ 599",
    description: "Para operacao de escala com limites maiores, governanca e automacoes premium.",
    bullets: ["limites altos", "suporte prioritario", "uso intensivo de IA", "camada enterprise"],
  },
];

export const faqItems = [
  {
    question: "O robo aprende direto na conta real?",
    answer:
      "O aprendizado principal acontece em observer e demo. Na conta real, o sistema registra tudo, mas a promocao de um novo modelo continua controlada.",
  },
  {
    question: "Posso definir metas e travas de risco?",
    answer:
      "Sim. O projeto foi desenhado para metas de profit, limite de perda, drawdown, horario, ativos e limite de operacoes por dia.",
  },
  {
    question: "Os dados dos clientes podem treinar a IA interna?",
    answer:
      "Sim, com anonimização, trilha de consentimento e separacao entre dado operacional do cliente e dataset interno agregado.",
  },
];

export const footerLinkGroups = [
  {
    title: "Institucional",
    links: [
      { label: "Home", href: "/" },
      { label: "Recursos", href: "#recursos" },
      { label: "Planos", href: "#planos" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    title: "Produto",
    links: [
      { label: "Entrar", href: "/auth/login" },
      { label: "Criar conta", href: "/auth/cadastro" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Politica de privacidade", href: "/politica-privacidade" },
      { label: "Termos de uso", href: "/termos" },
      { label: "Contato", href: "/contato" },
      { label: "Suporte", href: "mailto:suporte@vunostudio.com.br" },
    ],
  },
];