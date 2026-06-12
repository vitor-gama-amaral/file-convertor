# Changelog

Todas as mudancas relevantes deste projeto serao registradas aqui.

## [Nao publicado]

### Adicionado

- Operacao de edicao de PDF com uniao de multiplos arquivos e separacao por intervalo de paginas
- Rotas `/api/pdf/merge` e `/api/pdf/split` com validacao de arquivos e paginas
- Interface web para upload multiplo, ordenacao de PDFs e formulario de recorte
- Testes automatizados para os principais fluxos de merge e split

## [0.2.0] - 2026-05-15

### Adicionado

- Deploy publico da aplicacao na Vercel
- Ponto de entrada `src/index.py` para compatibilidade com a Vercel

### Alterado

- Versao minima do Python ajustada para `>=3.12`
- Diretorio temporario da aplicacao ajustado para ambiente serverless
- README atualizado com o link da aplicacao publicada

## [0.1.0] - 2026-04-11

### Adicionado

- Aplicacao web Flask para conversao de arquivos Word (`.docx`) em PDF (`.pdf`)
- Interface para upload de arquivo e download imediato do PDF gerado
- Suite de testes automatizados com 3 cenarios da funcionalidade principal
- Cenario de sucesso com arquivo valido
- Cenario de erro do usuario com extensao invalida
- Cenario de variacao importante com extensao `.DOCX` em maiusculas

### Alterado

- README atualizado para refletir a stack atual, a execucao da aplicacao e os tres cenarios de teste
- Documentacao de instalacao ajustada para incluir `flask` entre as dependencias

### Corrigido

- Workflow de CI ajustado para instalar `flask` antes de executar os testes
- Falha de importacao no GitHub Actions durante a coleta do `pytest`
