# File Convertor

## Descricao do projeto

O File Convertor e uma aplicacao web para conversao de arquivos focada em uso
interno. Nesta versao, a funcionalidade principal permite transformar documentos
Word (`.docx`) em arquivos PDF (`.pdf`) de forma local, com mais controle sobre
os dados enviados e recebidos.

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
- Verificacao de seguranca de arquivos com analise pela VirusTotal
- Interface web com upload e download imediato do arquivo convertido
- Validacao do tipo de arquivo enviado
- Execucao local, sem depender de plataformas online
- Testes automatizados para os principais fluxos da aplicacao

## Tecnologias utilizadas

- Python 3.14+
- Flask
- VirusTotal API
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

## Configuracao da API

A funcionalidade de verificacao de virus usa a VirusTotal API. Para habilitar a
consulta, configure a variavel de ambiente `VIRUSTOTAL_API_KEY` com a chave da
sua conta da VirusTotal.

No PowerShell:

```powershell
$env:VIRUSTOTAL_API_KEY="sua-chave-aqui"
```

O sistema primeiro consulta o hash SHA-256 do arquivo na VirusTotal. Se o hash
ainda nao existir na base, o arquivo e enviado para uma nova analise.

## Execucao

Para executar o projeto:

```bash
python src/main.py
```

A aplicacao inicia um servidor Flask local com as funcionalidades de conversao
Word para PDF e verificacao de seguranca de arquivos.

## Como rodar os testes

Execute na raiz do projeto:

```bash
python -m pytest -q
```

Atualmente a suite cobre:

- Cenario de sucesso: envio de um arquivo `.docx` valido e retorno do PDF
- Erro de uso: envio de um arquivo com extensao invalida
- Variacao importante: envio de arquivo com extensao `.DOCX` em maiusculas
- Integracao com a funcionalidade de verificacao de virus usando mock da API
- Validacao da configuracao da chave `VIRUSTOTAL_API_KEY`

## Como rodar o lint

Execute na raiz do projeto:

```bash
python -m ruff check .
```

## CI

O workflow em [`.github/workflows/ci.yml`](C:/Users/Adm/file-convertor/.github/workflows/ci.yml:1) executa:

- Instalacao das dependencias do projeto, incluindo `flask`
- Instalacao do `pandoc` no ambiente Windows
- Validacao com `ruff`
- Execucao dos testes com `pytest`

## Deploy

Aplicacao publicada na Vercel:
[https://file-convertor-npusuolth-vitor-gama-amarals-projects.vercel.app](https://file-convertor-npusuolth-vitor-gama-amarals-projects.vercel.app)


## Versao atual

`0.2.0`

## Autor

Vitor Gama Amaral

## Repositorio publico

[GitHub - vitor-gama-amaral/file-convertor](https://github.com/vitor-gama-amaral/file-convertor)
