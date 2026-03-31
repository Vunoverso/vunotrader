# 2026-03-31 - Instalacao: painel Minhas Instancias

## Objetivo
Adicionar gerenciamento direto de instancias do robô na página de instalação para reduzir dependência de suporte manual.

## Arquivos impactados
- `web/src/app/api/mt5/robot-credentials/instances/route.ts`
- `web/src/components/app/mt5-robot-instances-panel.tsx`
- `web/src/app/app/instalacao/page.tsx`

## Implementacao
1. Endpoint `GET /api/mt5/robot-credentials/instances`
- autenticado via cookie/session
- resolve `profile_id` e `organization_id` do usuário
- lista até 20 instâncias do usuário na organização

2. Endpoint `PATCH /api/mt5/robot-credentials/instances`
- ações suportadas: `pause`, `revoke`, `activate`
- atualiza status da instância com escopo por `profile_id + organization_id`

3. UI `Mt5RobotInstancesPanel`
- lista instâncias com:
  - nome
  - status
  - modos permitidos
  - flag de real habilitado
  - heartbeat relativo
- ações por instância:
  - pausar
  - revogar
  - reativar
- botão atualizar estado

4. Integração na instalação
- painel adicionado em `/app/instalacao` logo após o bloco de geração de credenciais

## Resultado
A jornada de onboarding ficou completa no painel:
1. gerar credenciais
2. gerenciar instâncias
3. validar conexão com heartbeat

## Próximos passos
1. Adicionar confirmação modal para revogação.
2. Mostrar histórico de rotação de token por instância.
3. Expor filtro por status (ativo/pausado/revogado) quando houver volume maior.
