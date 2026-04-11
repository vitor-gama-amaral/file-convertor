# File Convertor

## Descricao do projeto

O File Convertor e uma aplicacao web para conversao de arquivos focada em uso interno. Nesta versao, a funcionalidade principal permite transformar documentos Word (`.docx`) em arquivos PDF (`.pdf`) de forma local, com mais controle sobre os dados enviados e recebidos.

## Problema real

Em muitos ambientes de trabalho, equipes precisam converter documentos com rapidez, mas acabam recorrendo a sites externos. Isso pode gerar risco de exposicao de dados sensiveis, dependencia de terceiros e perda de tempo no fluxo operacional.

## Proposta da solucao

O projeto oferece um conversor proprio para uso interno, reduzindo a necessidade de ferramentas online e centralizando a conversao de arquivos em uma aplicacao simples de manter e testar.

## Publico-alvo

Equipes e profissionais que precisam converter documentos com mais seguranca, especialmente quando os arquivos contem informacoes importantes ou sensiveis.

## Funcionalidades principais

- Conversao de arquivos `.docx` para `.pdf` (Mais operações nas próximas versões)
- Interface web com upload e download imediato do arquivo convertido
- Validacao do tipo de arquivo enviado
- Execucao local, sem depender de plataformas online
- Testes automatizados para o fluxo principal de conversao

## Tecnologias utilizadas

- Python 3.14+
- Flask
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
pip install flask pypandoc docx2pdf pytest docx ruff
```

## Execucao

Para executar o projeto:

```bash
python src/main.py
```

A aplicacao inicia um servidor Flask local com a funcionalidade de conversao Word para PDF.

## Como rodar os testes

Execute na raiz do projeto:

```bash
python -m pytest -q
```

Atualmente a suite cobre 3 cenarios da funcionalidade principal:

- Cenário de sucesso: envio de um arquivo `.docx` valido e retorno do PDF
- Erro de uso: envio de um arquivo com extensao invalida
- Variaçao importante: envio de arquivo com extensao `.DOCX` em maiusculas

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

## Versao atual

`0.1.0`

## Autor

Vitor Gama Amaral

## Repositorio publico

[GitHub - vitor-gama-amaral/file-convertor](https://github.com/vitor-gama-amaral/file-convertor)
