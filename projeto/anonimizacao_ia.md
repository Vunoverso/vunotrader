# Politica de Anonimizacao para IA Interna

## Objetivo

Permitir uso interno dos dados de trade para melhorar a IA sem expor identidade de usuarios.

## Regras obrigatorias

- nunca usar nome, email, telefone ou documento no dataset de treino global
- transformar identificadores em hash
- remover texto livre que contenha dados pessoais
- manter trilha de consentimento do usuario

## Campos anonimizados

- user_id -> anonymous_user_hash
- organization_id -> anonymous_org_hash
- ticket de corretora -> removido
- texto de justificativa -> versao redigida

## Pipeline

### Etapa 1. Coleta bruta

Dados chegam nas tabelas operacionais com isolamento por tenant.

### Etapa 2. Sanitizacao

Remocao de PII e padronizacao de campos.

### Etapa 3. Anonimizacao

Aplicar hash irreversivel com salt rotativo.

### Etapa 4. Publicacao interna

Inserir na tabela anonymized_trade_events para analise e treino.

### Etapa 5. Governanca

Auditoria de qualidade e checagem de compliance.

## Consentimento

- opt-in para uso de dados em melhoria de IA
- opt-out disponivel no painel
- historico de consentimento com data/hora

## Retencao

- dados operacionais: conforme necessidade contratual
- dados anonimizados para IA: janela longa com revisao periodica
- exclusao sob solicitacao: respeitar regras legais aplicaveis

## Uso permitido

- analise estatistica agregada
- melhoria de modelos internos
- deteccao de padroes de win/loss

## Uso proibido

- reidentificacao de usuarios
- venda de dados individuais
- compartilhamento externo sem base legal
