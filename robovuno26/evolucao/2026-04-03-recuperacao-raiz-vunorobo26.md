Data: 2026-04-03

# Recuperacao da pasta raiz vunorobo26

## Objetivo

Restaurar a estrutura do projeto apos a pasta raiz ter ficado reduzida a um unico README.

## Origem usada para recuperacao

- pasta fonte: E:\robotrader
- pasta restaurada: E:\vunorobo26

## Arquivos e pastas impactados

- .github/
- .gitignore
- .vscode/
- agent-local/
- backend/
- dados/
- evolucao/
- mt5/
- projeto/
- projeto.md.txt
- pyproject.toml
- robo/
- runtime-e2e-last.json
- scripts/
- tests/

## Decisao tomada

- a estrutura do projeto foi copiada de E:\robotrader para E:\vunorobo26
- o arquivo README.md existente em E:\vunorobo26 foi preservado
- a pasta .venv nao foi copiada por ser artefato recriavel de ambiente

## Observacoes e riscos

- nao havia repositorio Git disponivel em E:\vunorobo26 nem em E:\robotrader no momento da recuperacao
- o README preservado em E:\vunorobo26 difere do README da pasta fonte E:\robotrader
- como a recuperacao foi feita por copia entre pastas irmas, ainda vale validar se havia mudancas locais nao refletidas em E:\robotrader

## Proximos passos

- validar abertura do backend e do agente local
- comparar o README atual com a documentacao tecnica restaurada para alinhar eventual divergencia
- recriar o ambiente virtual quando necessario