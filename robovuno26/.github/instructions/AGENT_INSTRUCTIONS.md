# Vuno Trader — Instruções do Agente

## O que é este projeto

Motor de decisão operacional para MT5. SaaS multi-tenant onde cada usuário tem isolamento total por `tenant_id`.

O sistema não promete lucro. Ele registra, audita e explica cada decisão de trading.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind v4 |
| Backend | FastAPI, Python 3.12 |
| Banco | Supabase (Postgres + Auth + RLS) |
| Broker | MT5 via EA em MQL5 |
| Deploy | Vercel (web), Railway (brain) |

---

## Estrutura de pastas

```
vuno-trader/
├── web/src/
│   ├── app/
│   │   ├── login/page.tsx          → autenticação
│   │   └── app/
│   │       ├── layout.tsx          → layout autenticado com sidebar
│   │       ├── dashboard/page.tsx  → status, métricas, decisões recentes
│   │       ├── operacoes/page.tsx  → trades + auditoria
│   │       └── parametros/
│   │           ├── page.tsx        → página de parâmetros
│   │           ├── ParametersForm.tsx → formulário de risco
│   │           └── RobotPanel.tsx  → token e heartbeat do EA
│   ├── components/
│   │   ├── layout/Sidebar.tsx
│   │   └── ui/
│   │       ├── SignalBadge.tsx     → badge BUY/SELL/HOLD
│   │       └── StatusDot.tsx      → indicador online/offline
│   ├── lib/
│   │   ├── supabase-client.ts     → cliente browser
│   │   └── supabase-server.ts     → cliente SSR
│   ├── middleware.ts               → proteção de rotas
│   └── types/index.ts             → tipos globais
├── brain/
│   ├── main.py                    → FastAPI: /decide /heartbeat /health
│   ├── requirements.txt
│   └── VunoTrader.mq5             → EA para MetaEditor
└── infra/supabase/
    └── schema.sql                 → 5 tabelas + RLS + trigger
```

---

## Banco de dados

**5 tabelas. RLS ativo em todas. Toda query exige `tenant_id`.**

| Tabela | Propósito |
|---|---|
| `profiles` | Usuário + `tenant_id` (1 usuário = 1 tenant) |
| `robot_instances` | Token de autenticação + timestamp do heartbeat |
| `user_parameters` | Stop, take, risco por operação, modo demo/real |
| `trade_decisions` | Signal, confidence, rationale, regime, custo IA |
| `trade_results` | Resultado real: símbolo, direção, lucro, status |

**Regra absoluta:** nunca criar query sem filtrar por `tenant_id`.

---

## Contrato do brain

**POST /decide**

Headers:
```
x-brain-secret: <BRAIN_SECRET>
x-tenant-id: <uuid>
x-robot-id: <uuid>
```

Body:
```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "close_prices": [1.08, 1.082, ...],
  "mode": "demo"
}
```

Resposta:
```json
{
  "signal": "BUY",
  "confidence": 72.5,
  "rationale": "SMA5 acima de SMA20 com confirmação de preço.",
  "regime": "tendência_alta",
  "risk_ok": true,
  "timestamp": "2026-04-02T12:00:00Z"
}
```

**POST /heartbeat**
```json
{
  "robot_token": "...",
  "symbol": "EURUSD",
  "account": "***123"
}
```

---

## Variáveis de ambiente

**Web (.env.local):**
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_BRAIN_URL=
```

**Brain (.env):**
```
BRAIN_SECRET=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
FRONTEND_URL=
```

---

## Segurança — regras inegociáveis

1. Frontend usa apenas `anon key`. Nunca `service role` no browser.
2. Toda leitura e escrita no Supabase filtra por `tenant_id` do usuário autenticado.
3. RLS ativo em todas as tabelas. Nunca desativar.
4. Brain protegido por `x-brain-secret` em todo endpoint.
5. Logs não expõem token, senha, account real ou chave.
6. Modo real exige confirmação explícita no painel. Nunca ativar silenciosamente.
7. Conta MT5 anonimizada antes de qualquer transmissão.

---

## Padrões de código

### TypeScript
- Sem `any`. Tipar tudo com os tipos em `src/types/index.ts`.
- Props de componente sempre com `interface`, não `type`.
- Server Components por padrão. `"use client"` só quando necessário.

### Arquivos
- Máximo 200 linhas por arquivo. Se passar, extrair componente ou hook.
- Nomes de arquivo: `kebab-case`. Componentes: `PascalCase`.
- Sem `console.log`. Usar `logger` centralizado no brain.

### HTML e acessibilidade
- HTML semântico: `<main>`, `<section>`, `<article>`, `<nav>`, `<header>`.
- `<button>` para ação. `<a>` apenas para navegação.
- `aria-label` em ícones sem texto visível.
- Todo formulário com `<label>` explícito e `id` correspondente.
- Estados obrigatórios em toda tela: loading, empty, error.

### Tailwind
- Utilitários direto no JSX. Sem `@apply` fora de biblioteca de design.
- Tema dark-first: `bg-zinc-950`, `text-zinc-100`, `border-zinc-800`.
- Mobile-first com `sm:`, `md:`, `lg:`.
- Fonte: IBM Plex Sans (corpo) + IBM Plex Mono (dados numéricos).

---

## Componentes disponíveis

| Componente | Uso |
|---|---|
| `<SignalBadge signal="BUY" />` | Badge colorido do sinal |
| `<StatusDot online={true} />` | Indicador de conexão do robô |
| `<Sidebar />` | Navegação lateral (já no layout) |

---

## Fluxo funcional

```
Usuário cria conta
  → Supabase cria profile + user_parameters automático (trigger)
  → Usuário acessa dashboard
  → Gera token em Parâmetros → Robô
  → Instala EA no MT5 com token + URL do brain
  → EA envia heartbeat a cada 30s
  → A cada nova barra H1: EA envia candles → brain responde signal
  → Sistema grava decisão em trade_decisions
  → EA executa trade → resultado vai para trade_results
  → Dashboard e Operações exibem tudo por tenant
```

---

## O que já existe (não recriar)

- [x] Schema SQL completo com RLS
- [x] Auth com Supabase SSR + middleware de proteção
- [x] Layout autenticado com sidebar
- [x] Dashboard com métricas e últimas decisões
- [x] Página de Operações com tabela de trades e auditoria
- [x] Página de Parâmetros com formulário de risco e painel do robô
- [x] Brain FastAPI com `/decide`, `/heartbeat`, `/health`
- [x] EA MQL5 com heartbeat, coleta de candles e chamada ao brain

---

## O que ainda não existe (próximas fases)

- [ ] Comparativo demo vs real no dashboard
- [ ] Alertas simples (email ou push) por drawdown
- [ ] Melhoria de onboarding para primeiro acesso
- [ ] Lógica avançada no brain (além de cruzamento de médias)
- [ ] Suporte a múltiplos robôs por tenant

---

## Regra para evitar retrabalho

Antes de qualquer implementação:
1. Verificar se o componente ou lógica já existe na estrutura acima.
2. Se existir: reaproveitar ou estender. Não recriar do zero.
3. Se houver divergência entre o que existe e o que o usuário pede: sinalizar antes de implementar.
4. Mudanças que afetam segurança, isolamento de tenant ou RLS precisam de confirmação explícita.

---

## Glossário

| Termo | Significado |
|---|---|
| tenant | Usuário isolado. Cada conta é seu próprio tenant. |
| brain | Serviço Python que decide BUY/SELL/HOLD |
| EA | Expert Advisor — robô rodando no MT5 |
| heartbeat | Ping periódico do EA para indicar que está vivo |
| signal | Sinal do brain: BUY, SELL ou HOLD |
| rationale | Texto explicando por que o brain tomou aquela decisão |
| confidence | Percentual de certeza do brain (0–100) |
| regime | Contexto do mercado: tendência_alta, tendência_baixa, lateral |
