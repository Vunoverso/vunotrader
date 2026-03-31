export const navItems = [
  { label: "Recursos", href: "#recursos" },
  { label: "Como funciona", href: "#como-funciona" },
  { label: "Planos", href: "#planos" },
  { label: "FAQ", href: "#faq" },
];

export const heroMetrics = [
  { value: "Demo-first", label: "Valida no seguro antes do real" },
  { value: "Auditável", label: "Cada decisão tem motivo registrado" },
  { value: "Rastreável", label: "Execução, custo e resultado ligados" },
];

export const featureCards = [
  {
    title: "Motor de decisao auditavel",
    description:
      "O sistema registra por que entrou, confianca da decisao, risco calculado e pos-analise vinculada ao resultado real. Nao e IA que opera — e decisao explicavel.",
    iconKey: "brain",
    gradient: "from-violet-500 to-indigo-700",
  },
  {
    title: "Controle de risco por instancia",
    description:
      "Cada robo tem politica propria: modo autorizado (demo/real), teto de risco e token de autenticacao. A promocao demo-real e controlada pela plataforma, nao pelo usuario.",
    iconKey: "book",
    gradient: "from-cyan-500 to-sky-700",
  },
  {
    title: "Operacao SaaS com governanca",
    description:
      "Planos, billing, isolamento por tenant, custo de IA por operacao e flywheel de dados anonimizados para melhoria continua do motor de decisao.",
    iconKey: "chart",
    gradient: "from-emerald-500 to-teal-700",
  },
];

export const workflowSteps = [
  {
    eyebrow: "01",
    title: "Configurar conta e politica do robo",
    description:
      "Defina metas de profit, limite de perda, risco por trade e modo autorizado. A politica demo/real e controlada pela plataforma — o robo nao decide sozinho.",
  },
  {
    eyebrow: "02",
    title: "Validar no demo com trilha completa",
    description:
      "Cada decisao gerada em demo fica registrada com sinal, confianca, custo de IA e resultado. Isso e a base para promover ao real com criterio.",
  },
  {
    eyebrow: "03",
    title: "Operar real com auditoria continua",
    description:
      "No real, o teto de risco e aplicado automaticamente. O dashboard mostra o estado do motor, ultima decisao e custo por operacao em tempo real.",
  },
];

export const planCards = [
  {
    name: "Starter",
    price: "R$ 99",
    description: "Para quem esta comeando: 1 estrategia ativa, modo demo, trilha de decisao basica.",
    bullets: ["1 instancia de robo", "modo demo habilitado", "auditoria de decisoes", "dashboard base"],
  },
  {
    name: "Pro",
    price: "R$ 249",
    description: "Para operacao estruturada: modo real liberado, multiplas estrategias, auditoria completa.",
    bullets: ["multiplas instancias", "demo + real habilitados", "custo de IA por operacao", "exportacao de trilha"],
    featured: true,
  },
  {
    name: "Scale",
    price: "R$ 599",
    description: "Para escala: limites altos, API, webhooks e governanca de IA com flywheel de dados.",
    bullets: ["limites expansivos", "API + webhooks", "anonimizacao e flywheel", "suporte prioritario"],
  },
];

export const faqItems = [
  {
    question: "O sistema garante lucro automatico?",
    answer:
      "Nao. O Vuno e um motor de decisao e controle operacional — nao uma promessa de resultado. Ele automatiza a execucao, registra cada decisao com justificativa e protege o usuario com politica de risco. Resultado depende da estrategia configurada.",
  },
  {
    question: "Como funciona a protecao demo-first?",
    answer:
      "Cada instancia de robo tem uma politica de modo: demo, real ou ambos. A habilitacao do modo real e controlada pela plataforma — o robo nao pode operar na conta real sem autorizacao explicita e teto de risco configurado.",
  },
  {
    question: "Por que o sistema explica cada decisao?",
    answer:
      "Porque rastreabilidade e o diferencial central. Cada sinal gerado tem confianca, risco calculado, justificativa textual e resultado vinculado. Com isso, voce sabe se o robo esta errando por qual motivo — e pode corrigir a estrategia com evidencia.",
  },
  {
    question: "Os dados dos clientes podem treinar a IA interna?",
    answer:
      "Sim, com opt-in, anonimizacao completa, trilha de consentimento e separacao entre dado operacional do cliente e dataset interno agregado. O cliente controla o consentimento pelo painel.",
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