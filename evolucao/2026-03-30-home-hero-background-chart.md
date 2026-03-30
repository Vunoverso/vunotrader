# Home Hero Background Chart

## Data

2026-03-30

## Objetivo

Adicionar um grafico financeiro animado e sutil no background da home institucional sem poluir a leitura do hero.

## Decisao

- usar SVG decorativo no hero em vez de biblioteca de chart ou feed em tempo real
- manter a animacao em camada de fundo, com opacidade baixa e foco visual no texto principal
- respeitar preferencia de reduced motion no CSS global

## Motivo da escolha

- menor custo de renderizacao para landing page publica
- controle fino da densidade visual sem introduzir ruido funcional
- reduz risco de regressao de layout em mobile comparado a canvas ou grafico real

## Arquivos afetados

- [web/src/app/page.tsx](../web/src/app/page.tsx)
- [web/src/components/marketing/market-hero-background.tsx](../web/src/components/marketing/market-hero-background.tsx)
- [web/src/app/globals.css](../web/src/app/globals.css)

## Riscos e observacoes

- a animacao precisa continuar discreta em telas menores e nao pode competir com CTAs
- se a identidade visual da home mudar para uma direcao mais agressiva, o SVG pode precisar de revisao de contraste
- a primeira iteracao ficou com leitura excessiva de linha decorativa e nao de candlestick, entao o fundo foi ajustado para corpos e pavios reais com opacidade baixa

## Proximos passos

- validar a home em viewport desktop e mobile
- ajustar intensidade do fundo conforme feedback visual real