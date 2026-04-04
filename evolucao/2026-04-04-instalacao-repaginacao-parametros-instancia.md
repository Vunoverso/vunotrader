Data: 2026-04-04

Objetivo:
- Repaginar a página de instalação para refletir o fluxo oficial por pacote de instância.
- Remover a navegação para a tela global de parâmetros, que contrariava a direção de configuração por robô.

Arquivos impactados:
- web/src/app/app/instalacao/page.tsx
- web/src/components/app/installation-overview.tsx
- web/src/components/app/mt5-credentials-generator.tsx
- web/src/components/app/mt5-connection-checker.tsx
- web/src/components/app/app-sidebar.tsx
- web/src/app/app/dashboard/page.tsx
- web/src/app/app/assinatura/page.tsx
- web/src/app/app/parametros/page.tsx

Decisão:
- A instalação passou a enfatizar três fatos do produto: cada pacote cria uma instância isolada, a chave já vai embutida no runtime e o agent-local prioriza o executável quando o binário está presente.
- A rota /app/parametros deixou de ser ponto de navegação ativo e agora redireciona para /app/instalacao.
- Textos de dashboard, assinatura e validação de conexão foram ajustados para remover a premissa de token manual no EA e de parâmetros globais por usuário.

Alternativas descartadas:
- Manter a tela global de parâmetros até existir o modelo por instância.
  Motivo: isso preservaria um fluxo enganoso e manteria o produto sugerindo um comportamento que o backend raiz ainda não suporta corretamente.

Riscos ou observações:
- O projeto raiz ainda não possui persistência real de parâmetros por instância equivalente ao robot_instance_parameters existente em outras bases de referência.
- A próxima entrega precisa mover ajustes operacionais para uma camada ligada a robot_instances, sem reativar o formulário global legado.

Próximos passos:
- Definir schema e API de parâmetros por instância no projeto raiz.
- Expor a configuração individual dentro do painel de instâncias do robô.