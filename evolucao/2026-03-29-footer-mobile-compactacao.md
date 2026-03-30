# Ajuste de Footer Mobile

## Data

2026-03-29

## Objetivo

Reduzir altura excessiva e melhorar organizacao visual do footer em telas mobile.

## Problema observado

Os blocos de links no footer estavam em colunas verticais no mobile, aumentando demais a altura da tela e piorando a experiencia.

## Solucao aplicada

- links do footer no mobile migrados para formato de chips com quebra de linha
- colunas verticais mantidas apenas no desktop
- links internos convertidos para Link do Next.js
- espacamentos ajustados para reduzir altura total do bloco

## Arquivo impactado

- [web/src/components/marketing/site-footer.tsx](../web/src/components/marketing/site-footer.tsx)

## Resultado esperado

- footer mais compacto no mobile
- leitura mais rapida dos links
- menor scroll vertical no fim da home

## Ajuste complementar

- removidos os links Dashboard e Parametros da secao Produto no footer institucional para simplificar a navegacao publica