# 2026-03-31 - Instalacao: geracao de RobotID/RobotToken no painel

## Objetivo
Remover friccao do onboarding: permitir gerar credenciais de conexao MT5 diretamente na UI, sem depender de script manual.

## Arquivos impactados
- `web/src/app/api/mt5/robot-credentials/route.ts`
- `web/src/components/app/mt5-credentials-generator.tsx`
- `web/src/app/app/instalacao/page.tsx`

## Implementacao
1. Criada rota `POST /api/mt5/robot-credentials`:
- exige usuario autenticado
- identifica `profile_id` e `organization_id`
- pausa instancias ativas antigas do usuario
- cria nova `robot_instance` com token hash e retorna token em texto apenas nesta resposta

2. Criado componente `Mt5CredentialsGenerator`:
- opcao de modo `demo` ou `real`
- botao para gerar credenciais
- exibe e permite copiar:
  - `UserID`
  - `OrganizationID`
  - `RobotID`
  - `RobotToken`
- aviso explicito de token exibido uma unica vez

3. Integrado na pagina `/app/instalacao`:
- passo 3 do guia atualizado para apontar para o novo bloco de geracao

## Seguranca
- token salvo no banco apenas como hash SHA-256.
- token em texto nao e persistido nem recuperavel apos a resposta.

## Proximos passos
1. Adicionar botao de rotacao/revogacao explicito por instancia.
2. Exibir historico de instancias no painel admin.
3. Vincular modo real a confirmacao adicional de risco no frontend.

## Atualizacao 2026-03-31 - Escolha de tipo de robo e instrucoes de uso

### Objetivo
Deixar explicito na instalacao que o usuario pode escolher entre dois conectores:

- fluxo oficial com EA no MT5
- fluxo avancado com bot Python no CMD

Tambem foi incluido um guia curto de como usar cada opcao para reduzir duvida no onboarding.

### Arquivo impactado
- `web/src/app/app/instalacao/page.tsx`

### Implementacao
1. Nova secao **"Escolha o tipo de robo"** com dois cards comparativos.
2. Cada card informa:
- perfil de uso
- quando escolher
- passo a passo rapido de operacao
3. Para o caminho Python CMD, foram incluidos comandos de partida:
- instalacao de dependencias
- checagem de status
- execucao com `run-engine` em `dry-run`

### Decisao tecnica
Foi escolhida uma UX de comparativo no proprio onboarding (sem criar nova pagina) para manter o fluxo linear e reduzir cliques.

Alternativa nao adotada nesta etapa:
- criar wizard separado por tipo de conector.
Motivo: aumentaria complexidade de navegacao sem necessidade imediata.

### Observacoes
- O fluxo EA segue como recomendado por ser integrado a heartbeat, instancias e auditoria.
- O fluxo CMD fica como opcao avancada para usuarios tecnicos.

## Atualizacao 2026-03-31 - Correcao de handshake EA -> Brain (UserID)

### Problema identificado
O onboarding entrega `UserID` com `auth_user_id` (id de autenticacao), mas a validacao do brain consultava `robot_instances.profile_id` diretamente com esse valor.

Na pratica, isso causava falso negativo de autorizacao (`Robo nao encontrado`) e impedia heartbeat (`last_seen_at`) mesmo com RobotID/RobotToken corretos no EA.

### Arquivo impactado
- `vunotrader_brain.py`

### Correcao aplicada
Na funcao `validate_robot_identity`:

1. o brain agora tenta resolver `profile_id` a partir de `user_profiles.auth_user_id`;
2. quando encontra, usa esse `profile_id` resolvido na validacao de `robot_instances`;
3. mantem fallback para compatibilidade quando `UserID` ja vier como `profile_id`.

### Impacto esperado
- conexao MT5 passa a validar corretamente com credenciais geradas na UI;
- heartbeat volta a atualizar `robot_instances.last_seen_at`;
- dashboard e instalacao conseguem sair de OFF quando EA e brain estao ativos.

### Observacao
O warning de lock do Supabase no navegador foi mitigado em ajuste separado via singleton do client browser; essa parte nao interfere no handshake MT5 -> brain.
