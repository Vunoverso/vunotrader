# Ligação da Instância MT5 Real

Data: 2026-04-02

## Objetivo

Conectar a instância real do MT5 ao backend da Fase 1 usando a ponte local por arquivos e o agente local.

## Pré-requisitos

- backend rodando
Observação operacional:

- uma instância representa uma conta ou terminal MT5
- não é preciso renomear o arquivo do EA por instância
- o isolamento entre instâncias passa pelo token e pelo `InpBridgeRoot`/bridge da própria instância
- token da robot instance gerado no SaaS
- agente local instalado
- MetaTrader 5 instalado na mesma máquina do agente

## Passo 1 - Configurar o token da instância
.\configure-mt5-bridge.ps1
Edite o arquivo agent-local/runtime/config.json e preencha:

O script passa a preferir automaticamente o `bridge_name` salvo no `runtime/config.json` do pacote da instância.

Esse bridge aponta para:

- %APPDATA%\MetaQuotes\Terminal\Common\Files\<bridge_da_instancia>\in
- %APPDATA%\MetaQuotes\Terminal\Common\Files\<bridge_da_instancia>\out
- %APPDATA%\MetaQuotes\Terminal\Common\Files\<bridge_da_instancia>\feedback

```powershell
cd agent-local
- InpBridgeRoot = mesmo bridge mostrado no pacote baixado para aquela instância
```

Por padrão, isso aponta para:

- %APPDATA%\MetaQuotes\Terminal\Common\Files\VunoBridge\in
- %APPDATA%\MetaQuotes\Terminal\Common\Files\VunoBridge\out
- %APPDATA%\MetaQuotes\Terminal\Common\Files\VunoBridge\feedback

## Passo 3 - Configurar o EA
Com isso, um unico EA anexado no grafico atual passa a cuidar tambem desses ativos extras no mesmo timeframe do grafico. Se quiser o mesmo ativo em timeframes diferentes, continue usando um grafico separado para cada timeframe.

Se a instância foi criada com ativos predefinidos no painel, use um desses ativos como gráfico principal e preencha os demais em `InpAdditionalSymbols`.
No MetaEditor, compile:

- mt5/VunoRemoteBridge.mq5

Ao anexar no gráfico, alinhe estes inputs:

- InpBridgeRoot = VunoBridge
- InpAdditionalSymbols = lista opcional de ativos extras separados por virgula
- InpSnapshotCandles = quantidade de candles enviados no snapshot do timeframe operacional
- InpHigherTimeframe = timeframe de confirmacao enviado ao backend
- InpHigherTimeframeCandles = quantidade de candles enviados do timeframe de confirmacao
- InpAllowRealTrading = false enquanto estiver em homologação

Exemplo de multiplos ativos:

- `InpAdditionalSymbols = GBPUSD,XAUUSD,US30`

Com isso, um unico EA anexado no grafico atual passa a cuidar tambem desses ativos extras no mesmo timeframe do grafico. Se quiser o mesmo ativo em timeframes diferentes, continue usando um grafico separado para cada timeframe.

## Passo 4 - Sincronizar parâmetros operacionais

O agente local passa a gerar automaticamente o arquivo:

- out/runtime.settings.json

Esse contrato leva para o EA:

- risco por trade
- spread máximo
- lote base
- stop e take padrão
- limite de posições por símbolo
- respiro entre uma entrada e a próxima no mesmo ativo
- idade máxima do comando
- desvio de execução
- retries
- pausa de novas ordens
- fallback local
- modo da instância

## Passo 5 - Subir o agente local

```powershell
cd agent-local
.\run-agent.ps1
```

## Resultado esperado

- heartbeat chegando no backend
- snapshots sendo consumidos
- comandos .command.json aparecendo na pasta out
- runtime.settings.json sincronizado na pasta out
- feedbacks fechados indo para a pasta feedback e depois para o backend

## Observação de segurança

Para conta real, manter o EA com InpAllowRealTrading = false até validar:

- heartbeat
- parâmetros operacionais
- fluxo de decisão
- leitura correta do runtime.settings.json

Só depois liberar execução real explicitamente.