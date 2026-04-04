# Evolucao - Configuracao de Ambiente com Supabase

Data: 2026-04-02

## Objetivo

Habilitar uso de variaveis de ambiente locais para o backend bootstrap e evitar vazamento de segredo em versionamento.

## Arquivos impactados

- .gitignore
- backend/run-server.ps1
- backend/.env
- backend/.env.example

## Decisao

Foi adotado carregamento automatico de `backend/.env` no script `backend/run-server.ps1` antes de subir o Uvicorn.

Tambem foram adicionadas regras no `.gitignore` para ignorar arquivos `*.env` e `*.env.*`, mantendo apenas exemplos (`*.env.example`) versionaveis.

## Alternativas descartadas

- manter configuracao apenas por variaveis de sistema global: descartado por aumentar friccao local e chance de erro de ambiente.
- gravar segredo em arquivos versionados: descartado por risco de exposicao.

## Validacao executada

- revisao do script de inicializacao para parse de linhas `KEY=VALUE` com suporte a comentarios
- validacao de gravacao dos arquivos de ambiente local e exemplo

## Riscos e observacoes

- as chaves recebidas devem ser tratadas como sensiveis; se foram expostas em canais nao seguros, recomenda-se rotacao imediata.

## Proximos passos

1. padronizar uso de `SUPABASE_SERVICE_ROLE_KEY` nos modulos que consumirem Supabase
2. adicionar verificacao de variaveis obrigatorias no startup do backend
