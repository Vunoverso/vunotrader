# 2026-03-30 — Modulo Estudos: upload base (URL + PDF)

## Objetivo
Tirar o placeholder de /app/estudos e entregar fluxo funcional inicial para cadastrar materiais de estudo (video por URL e PDF via upload), com persistencia no Supabase.

## Arquivos impactados
- web/src/app/app/estudos/page.tsx
- web/src/components/app/estudos-manager.tsx

## Implementacao
1. `page.tsx` virou Server Component real:
- Le usuario autenticado via Supabase Auth
- Busca profile por `auth_user_id`
- Resolve `organization_id` via `organization_members`
- Carrega ate 100 itens de `study_materials` por organizacao
- Renderiza `EstudosManager` com `userId`, `organizationId` e `initialItems`

2. Criado `EstudosManager` (Client Component):
- Formulario para adicionar video por URL (`material_type=video_url`)
- Formulario para upload de PDF (`material_type=pdf`)
- Upload no Supabase Storage bucket `training-videos` (ou `NEXT_PUBLIC_SUPABASE_STUDY_BUCKET`)
- Atualizacao de `storage_path` apos upload
- Listagem dos materiais cadastrados com badge por tipo e data
- Mensagens de sucesso/erro e tratamento de usuario sem organizacao vinculada

## Decisoes
- Bucket padrao definido como `training-videos` por aderencia ao planejamento existente.
- Fluxo de PDF cria o registro no banco antes do upload para manter rastreabilidade por `material_id` no caminho do arquivo.
- Em caso de falha no upload, remove o registro criado para evitar item quebrado sem arquivo.

## Riscos/Observacoes
- Se o bucket nao existir ou sem policy, o upload de PDF falha com mensagem explicita.
- Tags (`study_tags`, `study_material_tags`) nao foram implementadas nesta etapa inicial para reduzir risco de bloqueio por RLS/policies faltantes.

## Proximos passos
1. Adicionar campo de tags com upsert seguro em `study_tags` + vinculo em `study_material_tags`
2. Gerar signed URL para abrir PDFs diretamente no painel
3. Integrar resumo/extração de texto (summary/extracted_text) via pipeline async
4. Implementar /app/auditoria com join entre decisions, trades e outcomes

## Atualizacao da evolucao (2026-03-30)

### Entrega realizada
- Implementado worker separado de ingestao em `backend/app/workers/study_ingestion_worker.py`
- Worker busca materiais pendentes em `study_materials` (`summary`/`extracted_text` nulos)
- Para PDF: baixa arquivo no Supabase Storage e extrai texto com `pypdf`
- Para video URL: gera texto base por heuristica (titulo/fonte)
- Gera resumo heuristico e atualiza `study_materials.summary` e `study_materials.extracted_text`
- Registra uso em `ai_usage_logs` com provider `local-worker` e custo zero

### Dependencias e docs
- Adicionado `pypdf` em `backend/requirements.txt`
- Documentado no `backend/README.md` como executar em modo `--once` e loop continuo

### Validacao
- Comando executado com sucesso:
	- `python -m app.workers.study_ingestion_worker --once`
- Resultado observado: leitura do Supabase funcionando e ciclo encerrado sem erro (`Nenhum material pendente`)

## Atualizacao da evolucao (2026-03-30 - pipeline IA + status de processamento)

### Objetivo da mudanca
- Substituir o resumo heuristico por pipeline de IA com transcricao real de videos e extracao semantica para RAG.
- Expor no painel de estudos o status de processamento: pendente, processando, processado e erro.

### Arquivos impactados
- supabase/migrations/20260330_000003_study_ingestion_pipeline.sql
- projeto/supabase_schema.sql
- backend/requirements.txt
- backend/app/workers/study_ingestion_worker.py
- web/src/app/app/estudos/page.tsx
- web/src/components/app/estudos-manager.tsx

### Decisao tomada
- Adotado pipeline assincrono com worker dedicado para ingestao de materiais, preservando responsividade do app.
- Definido ciclo de status em `study_materials` (`pending`, `processing`, `processed`, `error`) para observabilidade de ponta a ponta.
- Criada tabela `study_material_chunks` para armazenar blocos semanticos, resumo por chunk, palavras-chave e embedding para uso em RAG.
- Frontend atualizado para mostrar badge de status, erro de processamento e timestamp de processamento, com botao de atualizacao manual.

### Riscos e observacoes
- Pipeline depende de `OPENAI_API_KEY` e de acesso externo (API de transcricao de YouTube e modelos OpenAI).
- Custos de token podem subir conforme volume e tamanho dos materiais; logs em `ai_usage_logs` ajudam no controle.
- Necessario aplicar migration no ambiente Supabase antes de processar novos materiais com o worker atualizado.

### Alternativas consideradas e nao adotadas
- Manter heuristica local sem IA: descartado por baixa qualidade semantica para RAG.
- Processar sincrono no request web: descartado por risco de timeout e pior UX.

### Proximos passos
1. Aplicar migration em todos os ambientes (dev/homolog/prod).
2. Executar validacao do worker com material real (video YouTube e PDF) e acompanhar `processing_status`.
3. Evoluir para auto-refresh de status no frontend (polling leve ou realtime) para reduzir refresh manual.

## Atualizacao da evolucao (2026-03-30 - autonomia de status no painel)

### Objetivo da mudanca
- Tornar o acompanhamento de processamento mais autonomo no frontend, reduzindo dependencia de refresh manual.

### Arquivo impactado
- web/src/components/app/estudos-manager.tsx

### Decisao tomada
- Implementado polling leve de status a cada 15s, acionado apenas quando houver materiais em `pending` ou `processing`.
- Mantido botao `Atualizar status` como fallback manual para controle imediato pelo usuario.

### Riscos e observacoes
- Polling periodico aumenta chamadas ao banco quando houver fila ativa; mitigado por ativacao condicional apenas com itens pendentes/processando.
- No ambiente atual, migration de ingestao ainda nao aplicada no banco remoto (coluna `processing_status` ausente).
- No ambiente atual, worker nao conclui pipeline sem `OPENAI_API_KEY` configurada.

### Proximos passos
1. Aplicar migration `20260330_000003_study_ingestion_pipeline.sql` no projeto Supabase remoto.
2. Configurar `OPENAI_API_KEY` no ambiente do backend.
3. Reexecutar `python -m app.workers.study_ingestion_worker --once` para validar processamento real completo.

## Atualizacao da evolucao (2026-03-30 - aplicacao remota e validacao real)

### Objetivo da mudanca
- Aplicar a migration de pipeline de estudos no Supabase remoto e validar o worker contra um material real.

### Validacao executada
- Migration `20260330_000003_study_ingestion_pipeline.sql` aplicada manualmente no SQL Editor do projeto `mztrtovhjododrkzkehk`.
- Confirmacao via backend: consulta de `study_materials.processing_status` passou a responder sem erro de coluna inexistente.
- Inserido material de teste direto no banco com status `pending`.
- Worker executado em modo unico com `OPENAI_API_KEY` disponivel no processo local.

### Resultado observado
- O worker conseguiu carregar materiais pendentes e atualizar status no banco.
- O material de teste foi movido para `processing` e finalizado em `error`, com rastreabilidade correta no banco.
- Erro concreto de processamento: falha de parse na resposta da API de transcricao do YouTube (`xml.etree.ElementTree.ParseError: no element found: line 1, column 0`).

### Observacoes operacionais
- O pipeline agora esta funcional do ponto de vista de schema, leitura de fila e atualizacao de status.
- A etapa fragil atual esta na obtencao de transcript do YouTube para o video testado, nao mais no banco ou no ciclo do worker.
- O usuario autenticado no frontend durante a validacao estava sem `organization_id` vinculado, por isso o item de teste nao apareceu em `/app/estudos` nessa sessao web.

### Proximos passos
1. Tornar a captura de transcript mais resiliente (retry, validacao de payload vazio e fallback de provider/estrategia).
2. Validar novamente com um video confirmado com transcript disponivel ou com um PDF real no bucket.
3. Corrigir o vinculo organizacional do usuario atual do frontend para que o painel de estudos reflita os materiais da organizacao correta.

## Atualizacao da evolucao (2026-03-30 - linguagem de erro mais humana)

### Objetivo da mudanca
- Melhorar a clareza das mensagens de falha no processamento de estudos, evitando expor erros tecnicos brutos para o usuario final.

### Arquivos impactados
- backend/app/workers/study_ingestion_worker.py
- web/src/components/app/estudos-manager.tsx

### Decisao tomada
- O worker passou a traduzir excecoes tecnicas conhecidas para mensagens mais naturais antes de gravar em `processing_error`.
- O frontend tambem passou a humanizar mensagens antigas ja gravadas no banco, para nao depender apenas de reprocessamento.

### Resultado esperado
- Em vez de mensagens como `no element found: line 1, column 0`, o painel passa a mostrar orientacoes legiveis, por exemplo indicando falha temporaria na leitura da transcricao e sugerindo nova tentativa ou outro link.

## Atualizacao da evolucao (2026-03-30 - resilencia com retry e expansao de padroes de erro)

### Objetivo da mudanca
- Tornar o worker resiliente a falhas transitorias (rate limits, timeouts, conexao intermitente) através de retry com backoff exponencial.
- Expandir a cobertura de padroes de erro para identificar quando uma falha eh permanente vs. transitoria.
- Evitar reprocessamento desnecessario de materiais com erros nao-recuperaveis.

### Arquivos impactados
- supabase/migrations/20260330_000004_study_ingestion_retry_mechanism.sql (nova migration)
- backend/app/workers/study_ingestion_worker.py

### Decisoes tomadas

#### 1. Novos campos no schema
- `retry_count` (int, default 0): contador de tentativas fracassadas
- `next_retry_at` (timestamptz): timestamp agendado para proxima tentativa (null se nao agendado)
- `last_error_at` (timestamptz): timestamp do ultimo erro (para auditoria)
- Indice `idx_study_materials_retry_status` para otimizar queries de materiais prontos para retry

#### 2. Funcoes adicionadas ao worker

**`_is_transient_error(exc)`**: Classifica excecoes em permanentes vs. transitorias
- **Erros permanentes** (sem retry): PDF/storage nao encontrado, video privado, tipo de material invalido
- **Erros transitorios** (com retry): rate limits, timeouts, conexao intermitente, HTTP 5xx
- Padroes reconhecidos: `rate limit`, `timeout`, `socket.timeout`, `ConnectionError`, `urllib3`, etc.

**`_schedule_retry(material_id, retry_count, error, is_permanent)`**: Agenda ou rejeita retry
- Backoff exponencial: 2^retry_count segundos (1s, 2s, 4s, 8s, 16s, ...)
- Maximo de 5 tentativas antes de marcar erro permanente
- Estado fica como `error` temporario com `next_retry_at` agendado
- Erros permanentes sao finalizados imediatamente

**`_load_pending()` melhorada**: Carrega apenas materiais prontos para reprocessamento
- Filtra por `processing_status in ('pending', 'error')` E `next_retry_at <= now()`
- Evita reprocessamento em breve de falhas recentes
- Mantém ordem FIFO por `created_at`

**`_friendly_processing_error()` expandida**: 20+ padroes de erro mapeados
- Categorias: YouTube transcript, URLs/compat, PDF (vazio/corrompido), storage, IA/API, conexao/timeout
- Exemplos: "Video privado ou removido", "PDF corrompido", "Falha de conexao ao processar material"
- Fallback por `material_type` para mensagens genéricas

#### 3. Fluxo de processamento melhorado
- Sucesso: `processing_status = processed`, `retry_count = 0`, `next_retry_at = null`, `last_error_at = null`
- Falha transitoria: `processing_status = error`, `retry_count += 1`, `next_retry_at` agendado, `last_error_at = now()`
- Falha permanente: `processing_status = error`, `retry_count` congelado, `next_retry_at = null`, mensagem final

### Riscos e observacoes
- Backoff exponencial pode deixar materiais com retry agendado para minutos/horas; usuario vê como `error` mas sistema vai reprocessar automaticamente
- Migration precisa ser aplicada antes de nova execucao do worker para novos campos existirem
- `_load_pending()` agora retorna lista sem paginacao nativa; batch_size ainda limita a quantidade processada por ciclo

### Alternativas consideradas e nao adotadas
- **Circuit breaker global**: Ao inves de por material, desabilitar todo worker por periodo; descartado por ser muito agressivo
- **Exponential backoff com jitter**: Adicionar aleatoriedade; descartado por simplicidade e porque batch pequeno nao causa thundering herd
- **Persistent queue separada**: Manter fila externa; descartado por manter estado no banco e evitar dependencia extra

### Proximos passos
1. Aplicar migration `20260330_000004_study_ingestion_retry_mechanism.sql` em todos os ambientes
2. Testar worker com material que falha transitoriamente (ex: URL com rate limit manual)
3. Validar que `retry_count` e `next_retry_at` sao atualizados corretamente no banco
4. Monitorar logs para confirmar backoff exponencial em acao
5. Considerar alertas quando `retry_count > 3` para investigacao manual

## Resultado Prático (2026-03-30)

### Implementacao concluida
- ✅ Nova migration criada com 3 novos campos (`retry_count`, `next_retry_at`, `last_error_at`)
- ✅ Funcao `_is_transient_error()` classifica ~15+ padroes de erro
- ✅ Funcao `_schedule_retry()` implementa backoff exponencial (2^n segundos, max 5 tentativas)
- ✅ `_friendly_processing_error()` expandida para 20+ padroes de erro em 8 categorias
- ✅ Backwards compatibility: worker funciona com ou sem novos campos
- ✅ Fallback automático se coluna não existe, logando warning

### Padroes de erro expansao
**Categorias mapeadas:**
1. **YouTube transcript**: ParseError, empty transcript, unavailable video
2. **URLs/compatibilidade**: invalid video ID, private video, unsupported format
3. **PDF**: missing, empty, corrupted, permission denied
4. **Storage**: file not found, access denied
5. **API/IA**: OPENAI_API_KEY, rate limit, quota exceeded
6. **Conexao/Timeout**: connection error, socket timeout, HTTP 5xx
7. **Permanentes**: nao agendaveis para retry (malformed data, config missing)
8. **Transitorias**: agendaveis com backoff (network, API busy, temporary issues)

### Backoff exponencial
```
Retry 0: 1s   (2^0)
Retry 1: 2s   (2^1)
Retry 2: 4s   (2^2)
Retry 3: 8s   (2^3)
Retry 4: 16s  (2^4)
Final:   erro permanente selecionado
```

### Validacao realizada
- Sintaxe Python: ✅ Validada com `py_compile`
- Linting: ✅ Zero erros
- Backwards compatibility: ✅ Cai gracefully se coluna não existe
- Código pronto para: ✅ Aplicar migration + executar worker

### Proximas atividades
1. **Imediato**: Aplicar migration `20260330_000004_study_ingestion_retry_mechanism.sql` via SQL Editor do Supabase
2. **Curto prazo**: Executar worker e monitorar logs de `_schedule_retry` em acao
3. **Validação**: Testar com material que falha (YouTube video com API temporariamente indisponível)
4. **Produção**: Deploy com retry logic ativa, libera reprocessamento automático
