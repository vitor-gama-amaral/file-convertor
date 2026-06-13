# File Convertor

## Descricao do projeto

O File Convertor e uma aplicacao web para conversao de arquivos focada em uso
interno. Nesta versao, a funcionalidade principal permite transformar documentos
Word (`.docx`) em arquivos PDF (`.pdf`), validar arquivos com a VirusTotal e
gerar links temporarios para compartilhamento seguro.

## Problema real

Em muitos ambientes de trabalho, equipes precisam converter documentos com
rapidez, mas acabam recorrendo a sites externos. Isso pode gerar risco de
exposicao de dados sensiveis, dependencia de terceiros e perda de tempo no fluxo
operacional.

## Proposta da solucao

O projeto oferece um conversor proprio para uso interno, reduzindo a necessidade
de ferramentas online e centralizando a conversao de arquivos em uma aplicacao
simples de manter e testar.

## Publico-alvo

Equipes e profissionais que precisam converter documentos com mais seguranca,
especialmente quando os arquivos contem informacoes importantes ou sensiveis.

## Funcionalidades principais

- Conversao de arquivos `.docx` para `.pdf`
- Uniao de dois ou mais arquivos PDF em um unico documento
- Separacao de paginas de um PDF por intervalo numerico
- Verificacao de seguranca de arquivos com analise pela VirusTotal
- Geracao de link temporario para download seguro do PDF convertido ou enviado
- Cofre de documentos com persistencia em Supabase/Postgres
- Card dedicado para registrar PDFs ja prontos no cofre temporario
- Limpeza automatica diaria de documentos expirados
- Validacao do tipo de arquivo enviado
- Execucao local, sem depender de plataformas online
- Testes automatizados para os principais fluxos da aplicacao

## Tecnologias utilizadas

- Python 3.12+
- Flask
- Supabase/Postgres
- VirusTotal API
- `pypdf`
- `pypandoc`
- `docx2pdf`
- `pytest`
- `ruff`

## Instalacao

### Opcao 1: usando Poetry

```bash
poetry install
```

Necessario ter o Poetry instalado: [python-poetry.org](https://python-poetry.org)

### Opcao 2: usando pip

```bash
pip install -r requirements.txt
```

Crie um arquivo `.env` na raiz a partir do exemplo versionado:

```bash
cp .env.example .env
```

No Windows PowerShell, caso nao tenha `cp` disponivel:

```powershell
Copy-Item .env.example .env
```

## Configuracao

A conversao segura usa a VirusTotal API antes de registrar o PDF no cofre.
Configure a variavel de ambiente `VIRUSTOTAL_API_KEY` com a chave da sua conta
da VirusTotal.

No PowerShell:

```powershell
$env:VIRUSTOTAL_API_KEY="sua-chave-aqui"
```

O sistema primeiro consulta o hash SHA-256 do arquivo na VirusTotal. Se o hash
ainda nao existir na base, o arquivo e enviado para uma nova analise.

Para habilitar o cofre de documentos, aplique o modelo
[`supabase/document_vault.sql`](supabase/document_vault.sql) no SQL Editor do
Supabase e configure:

```powershell
$env:SUPABASE_URL="https://seu-projeto.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY="sua-service-role-key"
```

`SUPABASE_URL` deve ser apenas a URL base do projeto. Nao inclua `/rest/v1`,
porque a aplicacao monta esse caminho automaticamente.

Variaveis opcionais:

- `DOCUMENT_VAULT_TTL_HOURS`: validade do link em horas. Padrao: `24`
- `DOCUMENT_VAULT_DIR`: diretorio local dos PDFs temporarios. Padrao: pasta temporaria do sistema
- `DOCUMENT_CLEANUP_INTERVAL_SECONDS`: intervalo da limpeza automatica. Padrao: `86400`
- `SUPABASE_DOCUMENT_TABLE`: nome da tabela no Supabase. Padrao: `document_vault`

## Execucao

Para executar o projeto:

```bash
python src/main.py
```

A aplicacao inicia um servidor Flask local com as funcionalidades de conversao
Word para PDF, verificacao de seguranca de arquivos, card para gerar link de
PDF pronto e paginas temporarias de download.

Principais rotas:

- `/operacoes/word-para-pdf`: valida, converte e gera link temporario
- `/operacoes/link-temporario-pdf`: registra um PDF pronto e gera link temporario
- `/d/<token>`: pagina publica de download temporario

## Como rodar os testes

Execute na raiz do projeto:

```bash
python -m pytest -q
```

Atualmente a suite cobre:

- Cenario de sucesso: envio de um arquivo `.docx` valido e retorno do link temporario
- Erro de uso: envio de um arquivo com extensao invalida
- Variacao importante: envio de arquivo com extensao `.DOCX` em maiusculas
- Uniao de PDFs com validacao de quantidade e extensao
- Separacao de PDFs com validacao do intervalo de paginas
- Integracao com a funcionalidade de verificacao de virus usando mock da API
- Validacao da configuracao da chave `VIRUSTOTAL_API_KEY`
- Card e pagina de criacao de link temporario para PDF
- Consulta e download de documento por link publico
- Remocao de documentos expirados do banco e do disco

## Como rodar o lint

Execute na raiz do projeto:

```bash
python -m ruff check .
```

## CI

O workflow em [`.github/workflows/ci.yml`](.github/workflows/ci.yml) executa:

- Instalacao das dependencias via `requirements.txt`
- Instalacao do `pandoc` no ambiente Windows
- Validacao com `ruff`
- Execucao dos testes com `pytest`

## Deploy

Aplicacao publicada na Vercel:
[https://file-convertor-npusuolth-vitor-gama-amarals-projects.vercel.app](https://file-convertor-npusuolth-vitor-gama-amarals-projects.vercel.app)


## Versao atual

`0.3.0`

## Autor

Vitor Gama Amaral

## Repositorio publico

[GitHub - vitor-gama-amaral/file-convertor](https://github.com/vitor-gama-amaral/file-convertor)
