# Evolução - Refatoração Modular da Ponte MT5

Data: 2026-04-02

## Objetivo

Reduzir o tamanho e o acoplamento do EA principal do MT5, preservando o comportamento atual da ponte local.

## Arquivos impactados

- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-json.mqh
- mt5/vuno-bridge/vuno-bridge-paths.mqh
- mt5/vuno-bridge/vuno-bridge-market.mqh
- mt5/vuno-bridge/vuno-bridge-execution.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh

## Decisão

O EA foi quebrado em módulos por responsabilidade:

- json: parsing e escape de payload
- paths: diretórios da bridge local
- market: indicadores, spread, risco e contexto local
- execution: lote, stops e envio protegido de ordem
- io: snapshot, leitura de comando e exportação de feedback

O arquivo principal passou a ficar focado apenas em inputs, estado global e ciclo de vida do EA.

## Alternativas descartadas

- manter o arquivo monolítico: descartado por ultrapassar a regra de tamanho e dificultar manutenção
- reescrever a ponte do zero: descartado porque a lógica atual já estava estável e precisava apenas de separação estrutural

## Validação executada

- VS Code não apontou erros nos arquivos MQL5 editados
- contagem final de linhas ficou abaixo de 200 por arquivo
- o arquivo principal ficou com 50 linhas

## Riscos e observações

- a compilação no MetaEditor ainda precisa ser validada na máquina com MT5 instalado
- a modularização preserva a lógica atual, mas o próximo passo natural é separar também contratos e parâmetros do executor

## Próximos passos

1. compilar o EA no MetaEditor
2. ligar a instância MT5 real ao backend da Fase 1
3. extrair parâmetros operacionais do EA para contrato configurável