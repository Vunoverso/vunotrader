# Vuno Trader — Instruções do Agente (v2)

## Stack e contexto

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS v4
- **Backend**: FastAPI (Python 3.12), Supabase (Postgres + Auth + RLS)
- **Broker**: MT5 via Python `MetaTrader5`
- **Infra**: Railway (backend), Vercel (web), Supabase cloud
- **Modelo**: SaaS multi-tenant com isolamento por `tenant_id`

---

## Regra principal de trabalho

Antes de qualquer alteração, revisar a pasta `evolucao/`:

- Entender o que já foi decidido
- Identificar correções aplicadas
- Detectar divergência entre plano e código
- Sinalizar conflito antes de implementar

**Fluxo obrigatório:**
1. Ler arquivos relevantes em `evolucao/`
2. Ler planejamento em `projeto/`
3. Comparar plano × evolução × código
4. Sinalizar conflito se houver
5. Implementar

---

## Padrões de código

### Geral
- Máximo **200 linhas por arquivo**; extrair módulos se ultrapassar
- Nomear arquivos em `kebab-case`; componentes em `PascalCase`
- Sem comentários óbvios; comentar apenas decisões não triviais
- Sem `any` em TypeScript; tipar tudo explicitamente
- Sem `console.log` em produção; usar `logger` centralizado

### Semântica
- HTML semântico: `<main>`, `<section>`, `<article>`, `<nav>`, `<aside>`, `<header>`, `<footer>`
- `aria-label` obrigatório em ícones sem texto visível
- Botões com `type="button"` explícito fora de formulários
- `<button>` para ação, `<a>` apenas para navegação

### Tailwind CSS v4
- Usar classes utilitárias diretamente; evitar `@apply` exceto em bibliotecas de design
- Tokens de cor: `bg-zinc-900`, `text-zinc-100`, `border-zinc-700/50` (dark-first)
- Responsividade: mobile-first com `sm:`, `md:`, `lg:`
- Animações: usar `transition-*` e `duration-200` como padrão
- Evitar inline styles; tudo via Tailwind ou CSS variables

---

## Segurança (OWASP Top 10)

- **A01 — Controle de acesso**: toda query Supabase exige `tenant_id` do contexto autenticado; nunca confiar em parâmetro do cliente
- **A02 — Falha criptográfica**: nunca expor chaves privadas (`SUPABASE_SERVICE_KEY`, `MT5_PASSWORD`) no frontend ou logs
- **A03 — Injeção**: usar apenas queries parametrizadas; nunca interpolação de strings em SQL
- **A05 — Misconfiguration**: variáveis de ambiente via `.env`; sem hardcode de URLs ou credenciais
- **A07 — Autenticação**: sessão via `@supabase/ssr`; middleware valida token em todas as rotas `/app/*`
- **A09 — Logging inseguro**: logs não devem conter tokens, senhas ou CPF; dados sensíveis devem ser mascarados

---

## Arquitetura SaaS

- Isolamento por `tenant_id` em **todas** as tabelas; RLS ativo no Supabase
- Nunca retornar dados de outro tenant, mesmo em admin queries
- Planos SaaS controlam feature flags; verificar plano antes de liberar recurso
- Dados anonimizados para IA: remover `user_id`, `account`, `name` antes de enviar ao modelo
- API pública: rate limiting obrigatório; erros não expõem stack trace

---

## Componentes React

- Componente = 1 responsabilidade; composição sobre herança
- Props: tipar com `interface`; sem `type` para props de componente
- Client components (`"use client"`) apenas quando necessário (interatividade, hooks)
- Server components por padrão para fetch de dados
- Loading states: usar `Suspense` + skeleton; nunca tela em branco
- Erros: `error.tsx` por segmento de rota

---

## Registro de evolução

Após mudança relevante, criar/atualizar arquivo em `evolucao/`:

```
AAAA-MM-DD-tema.md
```

Conteúdo mínimo:
- **Data**: (preenchida automaticamente)
- **Objetivo**: o que mudou e por quê
- **Arquivos impactados**: lista
- **Decisão**: o que foi feito
- **Alternativas descartadas**: e por quê
- **Próximos passos**: se houver

---

## Prioridades do projeto

1. Arquitetura e estrutura correta
2. Persistência e rastreabilidade de dados
3. Segurança, isolamento por tenant, anonimização
4. Fluxo demo antes do fluxo real
5. Observabilidade, auditoria, explicabilidade
6. Interface web e operação SaaS

## Regra para evitar retrabalho

Se a pasta [evolucao](../evolucao) mostrar que algo já foi pensado, implementado, corrigido ou descartado, o agente deve:

- reaproveitar a decisão anterior quando ela ainda fizer sentido
- sinalizar quando o código estiver inconsistente com a evolução registrada
- evitar repetir implementação já feita
- evitar sugerir como novidade algo que já existe

Se houver divergência entre registro e código, o agente deve informar isso explicitamente.

## Registro pós-alteração

Depois de qualquer mudança relevante, o agente deve atualizar a pasta [evolucao](../evolucao) com:

- data
- objetivo da mudança
- arquivos impactados
- decisão tomada
- riscos ou observações
- próximos passos, se houver

## Convenção recomendada para arquivos em evolucao

Preferir nomes como:

- AAAA-MM-DD-tema.md
- AAAA-MM-DD-modulo-ajuste.md
- AAAA-MM-DD-correcao-nome.md

Exemplos:

- 2026-03-29-auth-saas-base.md
- 2026-03-29-brain-python-ajustes.md
- 2026-03-29-dashboard-planejamento.md

## Prioridades do projeto

O agente deve priorizar nesta ordem:

1. Estrutura e arquitetura correta
2. Persistência de dados e rastreabilidade
3. Segurança, isolamento por tenant e anonimização
4. Fluxo demo antes do fluxo real
5. Observabilidade, auditoria e explicabilidade
6. Interface web e operação SaaS

## Regras de implementação

- Nunca apagar contexto importante da pasta [evolucao](../evolucao) sem motivo claro.
- Nunca sobrescrever decisão anterior sem registrar a revisão.
- Sempre preferir mudanças pequenas, rastreáveis e coerentes com o plano.
- Sempre indicar quando um item do plano ainda não existe em código.
- Sempre indicar quando um item do código não está refletido na documentação de evolução.
- Quando houver mais de um caminho técnico possível, analisar as opções e seguir o melhor caminho para o projeto, mesmo que existam alternativas viáveis.
- As alternativas que não forem escolhidas devem ser registradas na pasta [evolucao](../evolucao), com o motivo da não adoção naquele momento.
- O agente não deve paralisar o andamento por excesso de opções; deve convergir para a melhor rota e documentar as demais.

## Comportamento esperado do agente

O agente deve agir com autonomia técnica, mas com disciplina documental.
Cada passo importante do projeto precisa deixar rastro em [evolucao](../evolucao).
O projeto deve evoluir com histórico legível, evitando retrabalho e perda de contexto.

Quando existirem múltiplas abordagens, o agente deve avaliar custo, impacto, risco, aderência ao plano e velocidade de entrega, escolher a melhor direção e registrar as outras possibilidades como referência futura.