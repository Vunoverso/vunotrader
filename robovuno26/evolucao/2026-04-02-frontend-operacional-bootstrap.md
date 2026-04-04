# Evolucao - Frontend Operacional no Bootstrap Local

Data: 2026-04-02

## Objetivo

Substituir a pagina estatica inicial por um frontend operacional completo no sistema principal (fora de `vuno-trader22`), usando os endpoints ja existentes do backend FastAPI.

## Arquivos impactados

- backend/static/index.html
- backend/static/js/app.js

## Decisao

Foi implementada uma SPA estatica com as seguintes areas:

1. Autenticacao e sessao
- cadastro com tenant opcional
- login e logout
- restauracao de sessao com token salvo em localStorage

2. Dashboard
- metricas de instancias e eventos
- resumo operacional do tenant atual
- feed resumido dos ultimos eventos

3. Instancias
- criacao de robot instance (DEMO/REAL)
- exibicao do token retornado na criacao
- tabela com status e ultimo heartbeat

4. Parametros
- leitura e escrita de user_parameters
- formulario completo com validacao de tipos no cliente

5. Auditoria
- consulta de audit_events com limite configuravel
- tabela com tipo de evento, referencia de usuario/robo e payload

## Alternativas descartadas

- migrar agora para frontend React/Next dedicado: descartado para manter velocidade no bootstrap atual e reaproveitar o backend estatico existente.
- criar endpoints novos antes do frontend: descartado nesta etapa para priorizar entrega imediata em cima dos contratos ja disponiveis.

## Validacao executada

- compilacao Python do backend: `python -m compileall backend/app`
- carregamento dos novos arquivos estaticos sem erro de escrita

## Riscos e observacoes

- a aplicacao ainda depende de token bearer em localStorage (adequado ao bootstrap atual, mas nao ideal para producao SaaS final).
- o frontend opera sobre os endpoints existentes; visoes analiticas mais profundas ainda dependem de endpoints adicionais.

## Proximos passos

1. adicionar endpoint de resumo operacional dedicado (decisoes, resultados e PnL agregado)
2. incluir filtros de periodo na auditoria
3. evoluir para frontend autenticado dedicado quando a fase SaaS final iniciar
