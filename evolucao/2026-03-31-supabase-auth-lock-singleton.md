# 2026-03-31 - Mitigacao de lock do Supabase Auth no frontend

## Data
2026-03-31

## Objetivo
Reduzir warnings de lock do GoTrue no navegador e evitar concorrencia de sessao causada por multiplas instancias do cliente Supabase em componentes client-side.

## Arquivos impactados
- `web/src/lib/supabase/client.ts`

## Decisao tomada
Foi adotado padrao singleton para `createClient()` no browser:
- reutiliza a mesma instancia de `SupabaseClient` durante a sessao da pagina
- evita criacao repetida de clientes em polling/acoes de UI
- reduz contenção de lock em `sb-...-auth-token`

## Riscos e observacoes
- O warning pode ainda aparecer em cenarios de extensoes de navegador, multiplas abas agressivas ou listeners externos.
- A mitigacao nao altera a logica de autenticacao nem o schema.
- Esta mudanca nao resolve handshake MT5 diretamente; apenas estabiliza camada de sessao web.

## Alternativas consideradas (nao adotadas nesta etapa)
1. Remover/alterar listeners de auth em todas as telas.
Motivo: custo maior e risco de regressao no fluxo de recuperacao de senha.

2. Desabilitar Strict Mode globalmente.
Motivo: esconderia sintomas em desenvolvimento sem tratar causa principal de multiplas instancias.

## Proximos passos
1. Monitorar se o warning reduziu em producao e homologacao.
2. Se persistir, auditar paginas com polling e centralizar subscricoes de auth em provider unico.
