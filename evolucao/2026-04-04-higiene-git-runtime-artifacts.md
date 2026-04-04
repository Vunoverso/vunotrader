Data: 2026-04-04

Objetivo:
- Concluir o push pendente sem subir tokens locais, dumps de runtime, binarios gerados e artefatos temporarios de teste.

Arquivos impactados:
- .gitignore
- robovuno26/.gitignore
- web/src/app/app/instalacao/page.tsx

Decisao:
- O push final desta etapa deve incluir apenas codigo, documentacao e a correcao valida da pagina de instalacao.
- Artefatos locais de runtime MT5, builds PyInstaller, bancos locais, logs, snapshots arquivados e arquivos temporarios de smoke ficaram explicitamente ignorados para nao contaminarem o historico.
- Arquivos temporarios antigos antes rastreados na raiz podem sair do repositorio sem perda funcional, porque nao fazem parte do contrato de produto nem do fluxo oficial de instalacao.

Alternativas descartadas:
- Subir o runtime local e o build do executavel para "fechar" o repositorio.
  Motivo: isso vazaria token local, caminhos de maquina, dados de operacao e adicionaria artefatos reproduziveis ao historico.
- Subir PDFs e materiais externos colocados em robovuno26/projeto.
  Motivo: nao fazem parte do sistema executavel e misturam material de referencia externo com o codigo do produto.

Riscos ou observacoes:
- Quem precisar do executavel local deve gera-lo pelo fluxo de empacotamento do agent-local, nao a partir de um binario versionado manualmente.
- A raiz ainda carregava arquivos temporarios versionados; esta etapa trata esse passivo para evitar novo staging acidental.

Proximos passos:
- Se o executavel passar a ser um artefato oficial de distribuicao, versionar o pipeline de build/publicacao em vez do binario local.
- Implementar parametros operacionais por instancia no projeto raiz, conforme a direcao ja registrada na repaginacao da instalacao.