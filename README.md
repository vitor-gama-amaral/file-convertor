# File Convertor (Conversor de Arquivos)

## Descrição do projeto

O File Convertor é um sistema de conversão de arquivos criado para oferecer aos trabalhadores uma ferramenta própria de conversão de documentos, com foco em mais segurança e mais velocidade no processo. (A garantia que, por exemplo, o iLovePDF não pode garantir)

## Problema real

Em muitos cenários de trabalho, funcionários precisam converter arquivos com rapidez, mas acabam dependendo de sites externos ou ferramentas de terceiros. Isso pode gerar riscos de segurança, exposição de dados sensíveis e perda de tempo no fluxo de trabalho.

## Proposta da solução

A proposta deste projeto é disponibilizar um conversor próprio para uso interno, permitindo transformar arquivos Word em PDF de maneira mais controlada, rápida e segura.

## Público-alvo

O público-alvo deste projeto são trabalhadores e equipes que precisam converter documentos no dia a dia com mais segurança, especialmente em ambientes onde os arquivos podem conter informações importantes ou sensíveis.

## Funcionalidades principais

- Conversão de arquivos `.docx` para `.pdf`
- Execução local, sem depender de plataformas online
- Teste automatizado simples para validar a conversão

## Tecnologias utilizadas

- Python 3.14+
- `pypandoc`
- `docx2pdf`
- `pytest`
- `ruff`

## Instalação

### Opção 1: usando Poetry

```bash
poetry install
```

:::info

Necessário instalação do Poetry: https://python-poetry.org

:::

### Opção 2: usando pip

```bash
pip install pypandoc docx2pdf pytest docx ruff
```

## Execução

Para executar o projeto:

```bash
python src/main.py
```

## Como rodar os testes

Execute o comando abaixo na raiz do projeto:

```bash
python -m pytest -q
```

## Como rodar o lint

Execute o comando abaixo na raiz do projeto:

```bash
python -m ruff check .
```

## Versão atual

`0.1.0`

## Autor

Vitor Gama Amaral

## Repositório público

[https://github.com/vitor-gama-amaral/file-convertor](https://github.com/vitor-gama-amaral/file-convertor)
