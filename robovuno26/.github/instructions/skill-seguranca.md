# Habilidade: Segurança e Isolamento de Tenant

## Quando usar
Sempre que tocar em autenticação, autorização, RLS, queries ao banco ou exposição de dados.

## Regras inegociáveis

### Isolamento de tenant
- Todo acesso ao banco filtra por `tenant_id` do usuário autenticado.
- `tenant_id` vem sempre do servidor (`profiles` via `auth.uid()`), nunca do cliente.
- Nunca confiar em `tenant_id` passado como parâmetro pelo frontend.

### Chaves e segredos
- Frontend usa apenas `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- `SUPABASE_SERVICE_KEY` existe apenas no brain (Railway). Nunca no browser.
- `BRAIN_SECRET` existe apenas no brain e no EA. Nunca exposto no frontend.
- Sem hardcode de URLs ou credenciais no código.

### Logs
- Nunca logar: token, senha, `service_key`, account real do MT5, CPF, e-mail.
- Conta MT5 sempre como `***XXX` (últimos 3 dígitos).

### Modo real
- Modo real exige confirmação explícita do usuário no painel.
- Nunca ativar modo real silenciosamente por código.
- Exibir aviso visual `role="alert"` quando modo real estiver ativo.

### Endpoints do brain
- Todo endpoint protegido por `x-brain-secret`.
- Erros retornam mensagem genérica — sem stack trace, sem detalhes internos.

## Checklist antes de fazer PR

- [ ] Toda query tem `.eq('tenant_id', tenantId)`?
- [ ] `tenant_id` veio do servidor, não do cliente?
- [ ] Algum log expõe dado sensível?
- [ ] Frontend usa `service role` em algum lugar?
- [ ] Novo endpoint tem autenticação?
- [ ] Nova tabela tem RLS ativo?
- [ ] Modo real tem confirmação explícita?

## Exemplo: errado vs certo

```ts
// ❌ ERRADO — tenant_id vindo do cliente
const tenantId = searchParams.get('tenant_id')
const { data } = await supabase.from('trade_decisions').eq('tenant_id', tenantId)

// ✅ CERTO — tenant_id do usuário autenticado no servidor
const { data: { user } } = await supabase.auth.getUser()
const { data: profile } = await supabase
  .from('profiles').select('tenant_id').eq('id', user!.id).single()
const { data } = await supabase
  .from('trade_decisions').eq('tenant_id', profile!.tenant_id)
```
