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
