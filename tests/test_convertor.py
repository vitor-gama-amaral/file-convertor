from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from src.convertor.word2pdfconvertor import TransformadorWordToPDF


def test_converter():
    pasta = Path("tests/arquivos")
    pasta.mkdir(exist_ok=True)

    entrada = pasta / "teste.docx"
    saida = pasta / "teste.pdf"

    with ZipFile(entrada, "w", ZIP_DEFLATED) as arquivo:
        arquivo.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        arquivo.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )
        arquivo.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p>
<w:r>
<w:t>Teste simples</w:t>
</w:r>
</w:p>
</w:body>
</w:document>""",
        )

    conv = TransformadorWordToPDF(str(entrada), str(saida))
    conv.transform()
