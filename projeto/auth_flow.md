# Fluxo de Auth e Login

## Caminho escolhido

O sistema usa Supabase Auth como provedor principal de autenticacao.

O backend FastAPI atua como camada de dominio, seguranca e orquestracao do SaaS.

## Fluxos principais

### Cadastro

1. Usuario envia email, senha, nome e nome da organizacao para o backend.
2. Backend chama signup no Supabase Auth.
3. Trigger no banco cria user_profiles.
4. Backend cria a organizacao padrao e o membership owner.

### Login

1. Usuario envia email e senha.
2. Backend chama sign_in_with_password.
3. Backend devolve access token e refresh token.

### Recuperacao de senha

1. Usuario envia email.
2. Backend chama reset_password_email.
3. Supabase envia email de recuperacao.

### Atualizacao de senha

1. Usuario confirma fluxo de recuperacao ou esta autenticado.
2. Frontend envia access token, refresh token e nova senha.
3. Backend atualiza senha no Supabase Auth.

### Sessao autenticada

1. Frontend envia bearer token.
2. Backend valida token com Supabase.
3. Backend carrega memberships do usuario.

## Seguranca adotada

- auth centralizado no Supabase
- RLS para isolamento por tenant
- trusted hosts
- CORS controlado
- headers de seguranca
- service role isolada no backend

## Alternativas consideradas e nao adotadas agora

### Auth proprio com JWT local

Nao adotado porque aumenta complexidade, superficie de risco e custo de manutencao.

### Backend stateful com sessao em banco

Nao adotado porque o Supabase Auth ja resolve sessao, refresh e recuperacao com menos atrito.