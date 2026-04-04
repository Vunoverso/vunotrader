---
name: vuno-evolucao-execucao
description: 'Workflow para planejar, implementar, revisar e documentar mudancas no Vuno Trader com disciplina documental. Use quando for evoluir modulo, corrigir bug, revisar arquitetura, comparar plano com codigo, verificar divergencias entre documentacao e implementacao, registrar decisoes, riscos, pendencias e proximos passos em evolucao.'
argument-hint: 'Descreva a mudanca, modulo ou objetivo a evoluir no Vuno Trader'
user-invocable: true
---

# Vuno Evolucao e Execucao

## O que esta skill faz

Padroniza a forma de trabalhar no Vuno Trader para manter rastreabilidade tecnica, coerencia arquitetural e registro de decisoes antes e depois de qualquer mudanca relevante.

## Quando usar

- Implementar nova funcionalidade no web, brain, infra ou EA
- Corrigir bug ou regressao com impacto funcional
- Revisar divergencia entre documentacao, plano e codigo atual
- Fazer ajuste arquitetural, refatoracao ou endurecimento de seguranca
- Registrar uma decisao tecnica importante ou uma alternativa descartada

## Leituras obrigatorias

1. Ler [AGENT_INSTRUCTIONS.md](../../instructions/AGENT_INSTRUCTIONS.md).
2. Ler os arquivos relevantes em `evolucao/`.
3. Ler os arquivos relevantes em `projeto/`, quando existirem.
4. Ler o codigo atual dos modulos impactados antes de editar.

Se `evolucao/` ou `projeto/` nao existirem, sinalize a ausencia explicitamente e registre essa lacuna ao final da mudanca.

## Procedimento

### 1. Mapear o contexto

- Identifique o modulo afetado: `web/`, `brain/`, `infra/` ou `brain/VunoTrader.mq5`.
- Localize as decisoes ja registradas sobre esse assunto.
- Liste as restricoes tecnicas e de seguranca que nao podem ser quebradas.

### 2. Comparar plano, evolucao e codigo

- Verifique se o comportamento esperado esta documentado.
- Compare a documentacao com a implementacao atual.
- Aponte divergencias antes de editar quando houver conflito entre plano e codigo.

### 3. Escolher a rota tecnica

- Se houver mais de uma abordagem viavel, escolha a melhor com base em arquitetura, risco, custo de manutencao e velocidade de entrega.
- Registre tambem as alternativas nao adotadas e o motivo.
- Evite retrabalho: nao reimplemente algo ja previsto, corrigido ou descartado em `evolucao/`.

### 4. Implementar com escopo minimo e rastreavel

- Faca a menor mudanca necessaria para resolver a causa raiz.
- Preserve as regras do projeto: isolamento por `tenant_id`, RLS ativo, segredos fora do frontend e rastreabilidade operacional.
- Mantenha aderencia aos contratos existentes do brain e da interface web.

### 5. Validar

- Execute a validacao mais adequada para o modulo alterado: leitura critica, build, lint, teste, verificacao manual ou combinacao desses itens.
- Se algo nao puder ser validado, declare a lacuna explicitamente.

### 6. Registrar em evolucao

Crie ou atualize um arquivo em `evolucao/` com nome no formato `AAAA-MM-DD-tema.md` contendo:

- data
- objetivo da mudanca
- arquivos impactados
- decisao tomada
- riscos ou observacoes
- proximos passos, se houver

## Regras de decisao

- Se o codigo atual divergir do que esta em `evolucao/`, informe isso explicitamente.
- Se a mudanca for continuacao direta de um tema existente, atualize o arquivo relacionado em vez de abrir um novo sem necessidade.
- Se o item do plano ainda nao existir em codigo, deixe isso claro.
- Se o codigo fizer algo relevante sem reflexo documental, registre a ausencia.

## Criterios de conclusao

- O contexto relevante foi lido antes da implementacao.
- Divergencias entre documentacao e codigo foram apontadas.
- A mudanca respeita seguranca, tenant e contratos do sistema.
- Existe registro em `evolucao/` para a alteracao executada.
- Riscos, pendencias e proximos passos ficaram explicitos.

## Resultado esperado

Ao final, a entrega deve produzir codigo coerente com o plano do Vuno Trader e um rastro documental suficiente para qualquer proxima iteracao continuar sem perda de contexto.