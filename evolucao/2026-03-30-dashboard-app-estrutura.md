# 2026-03-30 — Dashboard App (estrutura inicial)

## Objetivo
Criar a estrutura autenticada do painel `/app` com sidebar, layout, dashboard e páginas placeholder para todas as seções do sistema.

## Arquivos criados

| Arquivo | Descrição |
|---|---|
| `web/src/lib/supabase/server.ts` | `createServerClient` para Server Components com cookies Next.js |
| `web/src/components/app/app-sidebar.tsx` | Sidebar dark com nav (Dashboard, Operações, Parâmetros, Estudos, Auditoria) e botão Sair |
| `web/src/app/app/layout.tsx` | Layout Server Component — valida sessão, redireciona para login se usuário não autenticado, monta sidebar + topbar |
| `web/src/app/app/dashboard/page.tsx` | Dashboard com cards de métricas (total trades, win rate, PnL, posições abertas), tabela vazia de ops recentes e 3 cards de status (Brain, MT5, Plano) |
| `web/src/app/app/operacoes/page.tsx` | Placeholder "Em breve" |
| `web/src/app/app/parametros/page.tsx` | Placeholder "Em breve" |
| `web/src/app/app/estudos/page.tsx` | Placeholder "Em breve" |
| `web/src/app/app/auditoria/page.tsx` | Placeholder "Em breve" |

## Decisões

- **Layout com dupla proteção**: middleware (`middleware.ts`) + guard no Server Component do layout — garante redirecionamento mesmo se o middleware falhar.
- **Dados do dashboard como placeholder**: sem chamadas ao banco ainda. Estrutura pronta para substituição quando o brain Python estiver conectado e enviando trades para o Supabase.
- **Sidebar client-side**: necessário para `usePathname` (active state) e `signOut`. Layout é Server Component.
- **Topbar com badge de modo do robô**: preparada para atualizar em tempo real via polling ou WebSocket futuro.
- **Framer-motion instalado** mas não usado ainda nesta etapa (instalado anteriormente, disponível para animações futuras).

## Pendências desta camada

- Página `/app/parametros` real: formulário completo com meta de profit, limite de perda, risco por trade, horários e modo do robô
- Página `/app/operacoes` real: tabela paginada de trades do Supabase
- Página `/app/estudos` real: upload de PDFs e URLs de vídeos
- Página `/app/auditoria` real: trilha de decisões por trade (entregue em 2026-03-30)
- Topbar com nome do usuário e foto (buscar de `user_profiles`)
- Indicador de status do brain em tempo real

## Próximos passos sugeridos

1. Implementar `/app/parametros` com formulário real e persistência no banco
2. Conectar Brain Python ao Supabase (trades, sinais, decisões)
3. Popular `/app/operacoes` com query na tabela `trades`

## Atualizacao 2026-03-30 - Auditoria funcional

- `web/src/app/app/auditoria/page.tsx` saiu de placeholder e agora consulta dados reais de `trade_decisions` com joins em `executed_trades` e `trade_outcomes`.
- Entregue visao de trilha por decisao com: sinal, confianca, risco, modo, motivo da entrada, resultado, PnL e pos-analise.
- Incluido sumario no topo (decisoes, com resultado, win rate e ultima analise) e lista expansivel por item para facilitar leitura no mobile.
- Estado vazio amigavel para quando ainda nao houver trilha de auditoria.

## Atualizacao 2026-03-30 - Auditoria com filtros e exportacao

- Criado componente cliente `web/src/components/app/auditoria-table.tsx`.
- Adicionados filtros por resultado (WIN/LOSS/Breakeven/Sem resultado), modo (observer/demo/real) e periodo (hoje/7d/30d).
- Adicionada busca por ativo (`EURUSD`, `XAUUSD`, etc.).
- Adicionada exportacao CSV da trilha filtrada de auditoria.

## Atualizacao 2026-03-30 - Auditoria com ordenacao, paginacao e XLSX

- Ampliado `web/src/components/app/auditoria-table.tsx` com ordenacao por data e PnL, incluindo controle de direcao.
- Adicionada paginacao client-side para a trilha filtrada, com navegacao entre paginas e resumo de itens exibidos.
- Adicionada exportacao XLSX da visao filtrada/ordenada usando a dependencia `xlsx` no frontend.
- Mantida a exportacao CSV com o mesmo recorte aplicado na tela para consistencia operacional.

## Atualizacao 2026-03-30 - Admin planos e logs IA

- Criadas as rotas `web/src/app/app/admin/planos/page.tsx` e `web/src/app/app/admin/logs-ia/page.tsx` para cobrir a frente de planos SaaS e observabilidade de uso de IA prevista no blueprint.
- A pagina de planos agora mostra catalogo, limites por plano, MRR estimado, assinaturas recentes e permite atualizar preco, status e limites via action server em `web/src/app/app/admin/planos/actions.ts`.
- A pagina de logs IA entrega metricas de volume/custo, filtros por provider, tipo de tarefa e periodo, alem de tabela paginada com consumo por organizacao.
- Corrigido `web/src/app/app/admin/page.tsx` para usar `total_tokens` e `estimated_cost` reais de `ai_usage_logs`, eliminando dependencia de coluna inexistente (`tokens_used`).
- Sidebar admin ampliada com atalhos para `Planos` e `Logs IA`, e os atalhos da home admin passaram a apontar para rotas reais em vez de placeholders.
