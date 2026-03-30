# Plano Trader

## Objetivo

Construir um robô trader com cérebro externo em Python, execução no MT5, memória inteligente, aprendizado em conta demo e promoção controlada para conta real.

Também construir uma plataforma SaaS completa com login, administração de contas, planos, home institucional e painel web de operação.

## Princípios

- Demo é ambiente de treino.
- Real é ambiente controlado.
- Toda entrada precisa ter motivo registrado.
- Toda saída precisa gerar pós-análise.
- O modelo real só pode ser atualizado por versão aprovada.

## Arquitetura Geral

### 1. Camada de Execução

- MT5 EA em MQL5.
- Modos de operação: observer, demo, real.
- Envia candles, indicadores, contexto e resultado para o cérebro Python.

### 2. Camada de Inteligência

- Serviço Python para análise.
- Geração de sinal: BUY, SELL, HOLD.
- Geração de confiança, risco sugerido e explicação da decisão.
- Busca de casos parecidos no histórico.

### 3. Camada de Memória

- Banco relacional no Supabase para trades, decisões, resultados e versões de modelo.
- Banco vetorial futuro para memória semântica e recuperação de casos.
- Armazenamento de imagens, screenshots e vídeos no Supabase Storage.

### 4. Camada de Treino

- Pipeline de treino com dados do demo.
- Reprocessamento de trades passados.
- Validação temporal.
- Promoção de modelo apenas se bater critérios mínimos.

### 5. Camada de Observabilidade

- Painel com histórico de trades.
- Taxa de acerto por setup, ativo, sessão e timeframe.
- Motivos de win e loss.
- Comparação entre demo e real.

### 6. Camada Web (Portal do Usuário)

- Dashboard web para acompanhar o robô em tempo real.
- Visão de operações: quantidade, win rate, loss rate, PnL, drawdown.
- Página de estudos: cadastro de URLs de vídeos, uploads de PDFs e organização por tema.
- Página de parâmetros: meta de profit, limite de perda, risco por trade, horários e modos.
- Página de auditoria: motivo da entrada, motivo de win/loss e explicação da IA por operação.

### 8. Camada SaaS (Auth, Planos e Billing)

- Login com Supabase Auth (email/senha, recuperação e confirmação de conta).
- Gestão de contas com perfis, empresas e permissões por papel.
- Planos SaaS com limites por recurso (trades, IA, storage, usuários e automações).
- Assinatura, ciclo de cobrança, status e bloqueio automático por inadimplência.
- Controle de acesso por tenant para isolar dados de cada cliente.

### 9. Camada Institucional (Site público)

- Home institucional com proposta de valor e CTA de teste.
- Páginas: recursos, preços, FAQ, contato e política de privacidade.
- Área autenticada separada da área pública.

### 10. Camada de Privacidade e Anonimização

- Todos os dados usados para treino global da IA devem ser anonimizados.
- Remover identificadores diretos antes de alimentar datasets internos.
- Separar dados operacionais do cliente e dados agregados de aprendizado.
- Permitir opt-in e opt-out do uso de dados para melhoria de IA.

### 7. Camada IA com Tokens

- Serviço de IA para explicar entradas, gerar pós-análise e classificar padrões.
- Registro de consumo de tokens por operação, por usuário e por dia.
- Limites de custo por plano e bloqueio automático ao atingir teto.
- Modo híbrido: usa regras locais quando IA estiver indisponível ou acima do limite.

## Modos de Operação

### Observer

- Analisa o mercado.
- Gera sinal.
- Não envia ordem.
- Salva tudo para avaliação.

### Demo

- Analisa e executa em conta demo.
- Aprende com resultados.
- Ajusta ranking de setups.
- Alimenta o dataset principal.

### Real

- Usa somente modelo aprovado.
- Continua registrando tudo.
- Não atualiza pesos automaticamente em produção.
- Gera sugestões para próxima versão do modelo.

## O que o robô deve armazenar por trade

- trade_id
- timestamp de entrada
- timestamp de saída
- modo: observer, demo ou real
- símbolo
- timeframe
- direção: buy ou sell
- preço de entrada
- stop loss
- take profit
- lote
- spread
- volatilidade
- indicadores calculados
- score da estratégia
- confiança do modelo
- motivo textual da entrada
- setup detectado
- screenshot do gráfico
- resultado: win, loss ou breakeven
- pnl financeiro
- pnl em pontos
- motivo textual do win ou loss
- versão do modelo usada
- quantidade de tokens consumidos na análise
- custo estimado da análise

## Estrutura Inteligente de Análise

Cada decisão precisa produzir quatro blocos:

### 1. Contexto

- Tendência
- Volatilidade
- Região técnica
- Sessão do mercado
- Força do sinal

### 2. Motivo da entrada

- Quais sinais confirmaram a operação
- Quais riscos estavam presentes
- Por que o robô decidiu entrar

### 3. Resultado

- Se bateu TP, SL ou saída manual
- Quanto tempo ficou aberto
- Se o trade respeitou o plano

### 4. Pós-análise

- Ganhou por quê
- Perdeu por quê
- Entrou cedo, tarde ou errado
- Stop estava curto ou longo
- Mercado estava lateral, tendencial ou instável

## Uso de vídeos e mídia

Vídeos não devem entrar direto como treino bruto do modelo operacional.

Eles devem virar conhecimento estruturado:

- transcrição
- frames-chave
- resumo técnico
- tags de setup
- lições extraídas
- exemplos de contexto

Esse material pode ser salvo no Supabase Storage e indexado depois para RAG.

## Portal Web (escopo funcional)

### Indicadores principais

- total de trades
- win rate e loss rate
- lucro líquido e lucro por período
- drawdown atual e máximo
- operações por ativo e timeframe
- precisão por setup

### Módulo administrativo

- gestão de usuários da conta
- gestão de permissões (owner, admin, analyst, viewer)
- status de assinatura e uso do plano
- auditoria de acessos e ações críticas

### Módulo comercial SaaS

- onboarding de novos clientes
- seleção e upgrade/downgrade de planos
- uso atual versus limite do plano
- bloqueios por cota excedida com aviso prévio

### Módulo de estudos

- campo para adicionar URL de vídeo
- upload de PDF de estudo
- tags por tema (price action, risco, psicologia, etc.)
- associação de materiais com setups

### Módulo de parâmetros

- meta de profit diária, semanal e mensal
- limite de perda diária
- limite de drawdown
- risco por operação
- limite de operações por dia
- horários permitidos de operação
- seleção de modo: observer, demo ou real

### Módulo de inteligência

- explicação da IA para cada entrada
- explicação da IA para cada win/loss
- recomendações automáticas de ajuste
- histórico de mudanças sugeridas e aplicadas

## IA e custos de tokens

É possível adicionar análise com IA por token de forma controlada.

### Regras de governança

- teto diário de tokens por usuário
- teto diário de custo em moeda
- fallback para análise local quando bater limite
- log de cada chamada com provider e modelo
- limite por plano SaaS
- limite por tenant e por usuário
- desligamento seletivo de funcionalidades caras

### Estratégia de uso eficiente

- análise completa com IA apenas em eventos relevantes
- resumo local em operações simples
- pós-análise detalhada em lote, fora do horário de mercado
- cache de explicações para cenários repetidos

## Supabase

### Tabelas iniciais

- strategies
- model_versions
- market_snapshots
- trade_decisions
- executed_trades
- trade_outcomes
- lessons_learned
- media_assets
- user_parameters
- ai_usage_logs
- study_materials
- study_tags
- study_material_tags
- user_profiles
- organizations
- organization_members
- saas_plans
- saas_plan_limits
- saas_subscriptions
- billing_events
- anonymized_trade_events

### Buckets sugeridos

- trade-screenshots
- training-videos
- chart-frames
- model-artifacts

## Critérios para subir do demo para real

- quantidade mínima de trades válidos
- drawdown máximo aceitável
- profit factor mínimo
- win rate por setup
- consistência por semana
- estabilidade em diferentes horários

## Etapas de desenvolvimento

### Fase 1. Base operacional

- Ajustar o EA para modos observer, demo e real.
- Padronizar mensagens entre MT5 e Python.
- Criar identificador único por decisão.

### Fase 2. Banco e memória

- Conectar Python ao Supabase.
- Criar schema inicial.
- Salvar decisões, execuções e resultados.

### Fase 2.1. Base SaaS

- Implementar autenticação e sessão.
- Implementar estrutura multi-tenant.
- Implementar entidades de plano e assinatura.
- Implementar permissões por papel.

### Fase 3. Pós-análise inteligente

- Gerar explicação de entrada.
- Gerar explicação de win e loss.
- Classificar setups e regimes de mercado.

### Fase 4. Treinamento real

- Remover dados sintéticos.
- Treinar com histórico do demo.
- Validar com janela temporal.
- Versionar modelos.

### Fase 5. Mídia e conhecimento

- Ingerir vídeos.
- Extrair transcrição e frames.
- Construir base RAG para consulta.

### Fase 6. Promoção controlada para real

- Definir regras de promoção.
- Congelar versão aprovada.
- Liberar com risco reduzido.

### Fase 7. Institucional e comercial

- Construir home institucional.
- Publicar página de preços e planos.
- Integrar fluxo de cadastro e onboarding.

### Fase 8. Privacidade e IA global

- Criar pipeline de anonimização.
- Criar dataset agregado de aprendizado.
- Garantir trilha de consentimento e compliance.

## Estrutura sugerida de projeto

### Projeto 1. Execução MT5

- EA principal
- controle de risco
- envio de contexto

### Projeto 2. Brain Python

- análise
- score
- inferência
- explicação

### Projeto 3. Data Platform

- Supabase
- ingestão
- histórico
- relatórios

### Projeto 4. Treino e avaliação

- pipelines
- experimentos
- validação temporal
- promoção de modelos

### Projeto 5. Knowledge Layer

- vídeos
- imagens
- RAG
- memória semântica

### Projeto 6. SaaS Core

- autenticação
- multi-tenant
- planos e assinatura
- billing e permissões

### Projeto 7. Institucional

- landing page
- pricing
- faq
- contato

### Projeto 8. Data Privacy

- anonimização
- consentimento
- políticas de retenção

## Próxima entrega recomendada

1. Criar schema do Supabase.
2. Adaptar o Python Brain para persistir decisões e resultados.
3. Adaptar o EA para operar em observer e demo.
4. Criar primeiro painel de análise de win e loss.
5. Criar tela web de parâmetros e metas do usuário.
6. Criar módulo de estudos com URLs e PDFs.
7. Criar módulo de monitoramento de tokens e custos de IA.
8. Criar autenticação e administração de contas.
9. Criar base de planos SaaS e assinaturas.
10. Criar home institucional e página de preços.
11. Criar pipeline de anonimização para treino interno da IA.