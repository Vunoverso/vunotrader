## Data
- 2026-04-03

## Objetivo
- Corrigir um desalinhamento de migrations em bases SQLite legadas que impedia a subida consistente do backend correto e acabava mascarando o problema como 401 no agente local.

## Arquivos impactados
- backend/app/migrations.py

## Decisao tomada
- O runner de migrations passou a reconciliar migrations que ja estao refletidas no schema, mesmo quando o registro formal em `schema_migrations` ficou inconsistente.
- A reconciliacao cobre os blocos mais sensiveis desta fase:
  - `runtime_policy_and_vpe_controls`
  - `robot_instances_bridge_and_symbols`
- Com isso, o backend deixa de tentar reaplicar `ALTER TABLE` em colunas que ja existem e consegue subir normalmente na base atual do workspace.

## Contexto encontrado
- A base local tinha as colunas de runtime policy e de instrumentacao de robo ja presentes em `user_parameters` e `robot_instances`.
- Apesar disso, `schema_migrations` registrava apenas `0001`, `0002` e uma versao legado `0003` para `runtime_policy_and_vpe_controls`, enquanto os arquivos atuais esperavam `0004` e `0005`.
- Esse desencontro fazia o runner considerar `0004` e `0005` como pendentes, provocando erro de coluna duplicada na inicializacao.
- Na pratica, isso levou o agent-local a falar com um backend em 8000 que nao estava alinhado com o token/base que ele usava, resultando em `401 Instancia do robo invalida`.

## Alternativas descartadas
- Corrigir apenas a tabela `schema_migrations` manualmente nesta maquina: descartado, porque resolveria o ambiente atual mas deixaria o codigo vulneravel ao mesmo problema em outras bases legadas.
- Tornar cada SQL de migracao idempotente diretamente no arquivo `.sql`: descartado por agora, porque o problema real estava no registro historico, nao no desenho das migrations novas.

## Validacao executada
- `python -m app.migrations status` passou a marcar `0004` e `0005` como aplicadas na base atual.
- O backend do workspace voltou a subir sem erro de coluna duplicada.
- O token do agent-local em `agent-local/runtime/config.json` voltou a ser aceito em `GET /api/agent/runtime-config` e `POST /api/agent/heartbeat` na porta 8000.

## Riscos e observacoes
- A reconciliacao atual e intencionalmente focada nas migrations legadas ja conhecidas desta fase do projeto.
- Se novos renomes de migration acontecerem no futuro, o historico deve ser preservado ou a regra de reconciliacao precisa ser atualizada junto.

## Proximos passos
- Reiniciar o agent-local para retomar o ciclo normal de runtime-config, decision e heartbeat sem 401.
- Evitar renomear versoes de migration ja aplicadas em ambientes reais sem criar estrategia formal de compatibilidade.