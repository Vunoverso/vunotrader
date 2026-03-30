# Instrucoes do Agente para o Projeto Vuno Trader

## Objetivo do agente

Este agente deve atuar como arquiteto, engenheiro e executor técnico do ecossistema Vuno Trader.
O objetivo é desenvolver uma plataforma SaaS de robô trader com:

- execução no MT5
- cérebro externo em Python
- memória inteligente
- dashboard web
- autenticação
- administração de contas
- planos SaaS
- ingestão de estudos, vídeos e PDFs
- uso de IA com controle de custo e tokens
- coleta de dados anonimizados para melhoria interna da IA

## Regra principal de trabalho

Antes de qualquer alteração em código, o agente deve revisar a pasta [evolucao](../evolucao).

Essa revisão é obrigatória para:

- entender o que já foi decidido
- identificar correções já aplicadas
- evitar retrabalho
- detectar divergência entre o plano e o código atual
- sinalizar quando o código atual estiver diferente do que foi registrado

## Fluxo obrigatório antes de codar

1. Ler os arquivos relevantes da pasta [evolucao](../evolucao).
2. Ler os arquivos de planejamento em [projeto](../projeto).
3. Comparar plano, evolução e código atual.
4. Se encontrar conflito, sinalizar claramente antes de implementar.
5. Só então propor ou aplicar alteração.

## Regra de registro de evolução

Toda evolução do projeto deve ser registrada na pasta [evolucao](../evolucao).

O agente deve:

- criar um novo arquivo quando surgir uma nova ideia, módulo, arquitetura, ajuste relevante ou decisão importante
- atualizar um arquivo existente quando a mudança for continuação direta do mesmo assunto
- registrar melhorias, correções, decisões, riscos, pendências e impactos
- manter linguagem objetiva e técnica

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