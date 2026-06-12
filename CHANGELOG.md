# Changelog

Todas as mudancas relevantes deste projeto serao registradas aqui.

## [0.3.0] - 2026-06-12

### Adicionado

- Cofre temporario de PDFs com registro em Supabase/Postgres
- Link publico curto para download de PDFs convertidos
- Card e pagina para gerar link temporario de PDFs ja prontos
- Tela de destino para validar links ativos ou expirados
- Limpeza automatica diaria de registros e arquivos expirados
- Modelo SQL versionado em `supabase/document_vault.sql`
- Testes automatizados para registro, consulta, download e limpeza do cofre

### Alterado

- Conversao Word para PDF agora valida o arquivo na VirusTotal antes de gerar o link
- Fluxo de conversao passou a retornar JSON com link temporario em vez de iniciar download imediato
- Workflow de CI passou a instalar dependencias via `requirements.txt`

### Corrigido

- Normalizacao de `SUPABASE_URL` quando configurada com `/rest/v1`
- Normalizacao do nome da tabela quando configurado como `public.document_vault`

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
