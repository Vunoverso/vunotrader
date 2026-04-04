Data: 2026-04-03

# Painel com linguagem humana e atualizacao automatica

## Objetivo

Reduzir o tom tecnico do painel operacional para usuario leigo e eliminar a dependencia mental de F5 para acompanhar o sistema.

## Situacao encontrada

- o dashboard principal ainda expunha resumo e eventos em JSON cru
- varios textos da interface falavam como painel tecnico e usavam termos internos demais
- a sincronizacao dependia principalmente do botao manual de atualizar
- o usuario precisava recarregar ou clicar com frequencia para sentir que a tela estava viva

## Arquivos impactados

- backend/static/index.html
- backend/static/js/app.js

## Decisao tomada

- o texto do painel foi reescrito com linguagem mais direta e simples em dashboard, robos, protecoes, historico e tutorial
- o resumo operacional deixou de exibir JSON e passou a mostrar blocos de leitura humana
- o feed de eventos do dashboard e o historico deixaram de despejar payload cru como experiencia principal e passaram a resumir o que aconteceu em frases curtas
- foi adicionado refresh automatico no frontend com pulso visual, carimbo da ultima sincronizacao e nova tentativa automatica sem recarregar a pagina
- o refresh automatico pausa suavemente com a aba em segundo plano e sincroniza novamente ao voltar
- a area do ultimo robo criado passou a orientar o usuario pelo fluxo principal e manteve o token apenas como detalhe de suporte

## Alternativas descartadas

- auto refresh por reload completo da pagina: descartado porque pisaria em formularios, pioraria a experiencia e reforcaria a sensacao de pagina estatica
- manter JSON no dashboard e criar apenas textos ao redor: descartado porque o problema central era justamente obrigar leitura tecnica demais
- colocar um toggle manual para ligar refresh automatico: descartado nesta iteracao por adicionar friccao sem ganho real para o uso atual

## Validacao executada

- validacao de erros em backend/static/index.html
- validacao de erros em backend/static/js/app.js

## Riscos e observacoes

- o auto refresh evita sobrescrever o formulario de protecoes enquanto o usuario esta editando, mas outras areas continuam sendo atualizadas em segundo plano
- o historico ainda continua tecnico por natureza, embora agora resuma melhor os eventos mais comuns
- se o painel crescer muito, o ideal depois sera separar componentes da SPA estatica para reduzir acoplamento do arquivo unico

## Proximos passos

1. destacar no dashboard a ultima analise com ativo, timeframe e direcao em um bloco proprio
2. adicionar pequenos estados vazios guiados nas telas de robos e historico
3. avaliar extracao da SPA estatica em modulos menores quando o painel ganhar mais interacoes