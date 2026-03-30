# 2026-06-30 — Brain Python: Integração com Supabase

## Objetivo
Conectar o `vunotrader_brain.py` ao Supabase para persistir todas as decisões e resultados de trades no banco de dados, eliminando a dependência exclusiva do CSV local.

## Arquivos impactados
- `vunotrader_brain.py` — principal

## Decisão tomada

### Nova classe `SupabaseLogger`
Adicionada antes da classe `MT5Bridge`. Responsável por:
- `log_decision()` → insere em `trade_decisions`
- `log_trade_open()` → insere em `executed_trades` com status `open`
- `log_trade_close()` → atualiza `executed_trades` para `closed` + insere em `trade_outcomes`

**Design de segurança:**
- Credenciais lidas exclusivamente de variáveis de ambiente (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`)
- Nunca hardcoded
- `supabase-py` é opcional via `try/import` — brain opera sem banco se biblioteca não estiver instalada

### `MT5Bridge` atualizado
- `__init__` agora recebe `db: SupabaseLogger`
- `_open_trades` dict adicionado para mapear `ticket → (decision_id, executed_trade_id)` — permite fechar corretamente
- `_handle_market_data` persiste TODAS as decisões (inclusive HOLDs), incluindo `symbol`, `timeframe`, `mode`, `user_id`, `organization_id` lidos do payload do MT5; retorna `decision_id` na resposta
- `_handle_trade_result` recebe `decision_id` do MT5, cria `executed_trade`, fecha imediatamente com resultado; mantém retroalimentação do CSV para o modelo de ML

### Protocolo MT5 → Brain (campo novo)
O EA MQL5 deve passar no payload de `MARKET_DATA`:
```json
{
  "type": "MARKET_DATA",
  "symbol": "WINM25",
  "timeframe": "M5",
  "mode": "demo",
  "user_id": "<uuid do usuário>",
  "organization_id": "<uuid da org>",
  "candles": [...]
}
```

E no payload de `TRADE_RESULT`:
```json
{
  "type": "TRADE_RESULT",
  "ticket": "123456",
  "decision_id": "<uuid retornado pelo brain>",
  "entry_price": 130000.0,
  "stop_loss": 129500.0,
  "take_profit": 130800.0,
  "lot": 1.0,
  "profit": 425.0,
  "points": 85,
  "user_id": "<uuid>",
  "organization_id": "<uuid>"
}
```

## Instalação
```bash
pip install supabase python-dotenv
```

Variáveis necessárias (`.env` na raiz ou ambiente):
```
SUPABASE_URL=https://mztrtovhjododrkzkehk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
```

## Retrocompatibilidade
- CSV local (`VunoTrader_history.csv`) continua sendo populado — modelo de ML não é afetado
- Brain opera normalmente mesmo sem Supabase configurado (graceful degradation)

## Riscos
- EA MQL5 (`VunoTrader_v2.mq5`) precisa ser atualizado para enviar `user_id`, `organization_id` e `decision_id` nos payloads — **pendente**
- Service Role Key não deve ser exposta no código ou versionada

## Próximos passos
1. Atualizar `VunoTrader_v2.mq5` para incluir `user_id`, `org_id` nos payloads e repassar `decision_id` do brain para `TRADE_RESULT`
2. Criar `.env` com as credenciais na máquina onde o brain rodar
3. `/app/auditoria` — tabela de decisões por trade no painel web
4. `/app/estudos` — upload de PDFs/vídeos

## Atualizacao 2026-03-30 - Fechamento da integracao MT5 <-> Brain com IDs

### Objetivo da mudanca
- Fechar a integracao de identidade e rastreabilidade entre EA MT5 e brain Python, garantindo persistencia consistente no Supabase.

### Arquivos impactados
- `VunoTrader_v2.mq5`
- `web/public/downloads/VunoTrader_v2.mq5`
- `vunotrader_brain.py`

### Implementacao realizada

#### EA MT5 (`VunoTrader_v2.mq5`)
- Adicionada validacao obrigatoria de identidade (`UserID` e `OrganizationID`) com formato UUID.
- Nova funcao `IdentityReady()` bloqueia envio de sinal/trade sem IDs validos e mostra aviso unico no log.
- Incluida protecao para ignorar sinal de entrada quando `decision_id` nao vier na resposta do brain.
- Reforco no fechamento de trade: extracao do `decision_id` via comment do deal com fallback para `ORDER_COMMENT`.
- Payload `TRADE_RESULT` agora envia explicitamente `mode` alem de `user_id`, `organization_id` e `decision_id`.

#### Brain Python (`vunotrader_brain.py`)
- Adicionada funcao `_normalize_uuid()` para validar e normalizar UUIDs recebidos do MT5.
- `_handle_market_data` agora retorna `HOLD` com motivo claro quando `user_id` estiver ausente/invalido.
- `log_decision()` passou a recusar persistencia quando `user_id` invalido.
- `_handle_trade_result` agora valida `decision_id`; sem valor valido, responde ACK e nao tenta persistir dado inconsistente.

### Resultado
- Integracao MT5 -> Brain -> Supabase fechada com validacao de identidade por tenant.
- Todas as ordens que entram no ciclo agora exigem contexto de usuario/organizacao e `decision_id` rastreavel.
- Reducao de risco de linhas orfas em `executed_trades`/`trade_outcomes` sem relacao com `trade_decisions`.

### Riscos/observacoes
- O EA precisa ser recompilado no MT5 apos update do arquivo para as validacoes entrarem em vigor.
- Se o usuario nao configurar IDs no EA, o robo permanece em bloqueio seguro (sem enviar ordens para o brain).

### Proximos passos revisados
1. Compilar e publicar a nova versao do EA em ambiente demo.
2. Validar ciclo completo com 1 operacao real de teste (decision -> open -> close) e confirmar IDs no Supabase.
3. Atualizar onboarding da tela `/app/instalacao` com instrucoes de onde obter `UserID` e `OrganizationID`.

## Validacao executada em 2026-03-30 (ciclo demo completo)

### Ambiente e premissas
- Brain executado localmente com variaveis carregadas de `backend/.env`.
- Supabase conectado com sucesso (`Persistência de trades ativa`).
- Identidade usada no teste:
  - `user_id`: `96fd6e0d-ae81-4eeb-b6fd-37279373a7db`
  - `organization_id`: `24affdc3-dc7b-4672-b20d-65033949bb76`

### Evidencias do ciclo
- `MARKET_DATA` processado com sucesso e decisao registrada:
  - `decision_id`: `4a36f246-df0f-46a5-8598-f34a36afb5c9`
  - HTTP `201 Created` em `trade_decisions`
- `TRADE_RESULT` processado com sucesso:
  - `executed_trade_id`: `631243a9-8f86-45b2-b66a-fb9a6397762b`
  - HTTP `201 Created` em `executed_trades`
  - HTTP `200 OK` no fechamento (`PATCH` status=closed)
  - HTTP `201 Created` em `trade_outcomes`

### Resultado
- Integracao validada ponta a ponta no fluxo demo:
  - `trade_decisions` ✅
  - `executed_trades` ✅
  - `trade_outcomes` ✅

### Observacao
- A recompilacao do EA no MetaTrader nao foi executada neste host porque `metaeditor64.exe` nao esta instalado/disponivel no ambiente atual.

## Atualizacao 2026-03-30 - Robustez de imports opcionais no Brain

### Objetivo da mudanca
- Reduzir ruido de diagnostico no editor quando dependencias opcionais nao estao instaladas no ambiente ativo.

### Arquivos impactados
- `vunotrader_brain.py`

### Decisao tomada
- O import de `brainpy` foi alterado para carregamento dinamico via `importlib.import_module("brainpy")`.
- Quando o pacote nao existe no ambiente, o brain continua operando em modo degradado (ja previsto), sem interromper o processo.

### Riscos/observacoes
- O aviso de `brainpy` no Pylance tende a desaparecer com esse padrao.
- Os avisos de `sklearn.*` continuam dependentes do interpretador Python selecionado e da instalacao de `scikit-learn` no ambiente ativo.

### Proximos passos
1. Garantir que o VS Code esteja apontando para o ambiente que contem `scikit-learn`.
2. Se necessario, instalar `scikit-learn` no ambiente ativo para remover os avisos restantes.
