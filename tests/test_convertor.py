from io import BytesIO
from unittest.mock import MagicMock

from pypdf import PdfReader, PdfWriter

from src.main import SECURITY_OPERATION, UPLOAD_OPERATION, app
from src.security.virus_total import VirusTotalResult


def make_pdf(page_count):
    output = BytesIO()
    writer = PdfWriter()

    for _page in range(page_count):
        writer.add_blank_page(width=72, height=72)

    writer.write(output)
    output.seek(0)
    return output.getvalue()


def test_convert_returns_generated_pdf(monkeypatch):
    client = app.test_client()
    fake_send_file = MagicMock()
    fake_send_file.return_value = app.response_class(
        b"%PDF-1.4\nfake pdf\n",
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=contrato.pdf"},
    )

    monkeypatch.setattr("src.main.Path.write_bytes", lambda *_args, **_kwargs: 17)
    monkeypatch.setattr(
        "src.main.TransformadorWordToPDF.transform",
        lambda self: self.output_path,
    )
    monkeypatch.setattr("src.main.send_file", fake_send_file)

    response = client.post(
        "/api/convert",
        data={
            "operation": UPLOAD_OPERATION,
            "file": (BytesIO(b"fake docx content"), "contrato.docx"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "contrato.pdf" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"%PDF-1.4")
    fake_send_file.assert_called_once()


def test_convert_rejects_invalid_extension():
    client = app.test_client()

    response = client.post(
        "/api/convert",
        data={
            "operation": UPLOAD_OPERATION,
            "file": (BytesIO(b"invalid"), "imagem.png"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Apenas arquivos .docx sao permitidos."}


def test_convert_accepts_uppercase_docx_extension(monkeypatch):
    client = app.test_client()
    fake_send_file = MagicMock()
    fake_send_file.return_value = app.response_class(
        b"%PDF-1.4\nfake pdf\n",
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=RELATORIO.pdf"},
    )

    monkeypatch.setattr("src.main.Path.write_bytes", lambda *_args, **_kwargs: 17)
    monkeypatch.setattr(
        "src.main.TransformadorWordToPDF.transform",
        lambda self: self.output_path,
    )
    monkeypatch.setattr("src.main.send_file", fake_send_file)

    response = client.post(
        "/api/convert",
        data={
            "operation": UPLOAD_OPERATION,
            "file": (BytesIO(b"fake docx content"), "RELATORIO.DOCX"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "RELATORIO.pdf" in response.headers["Content-Disposition"]
    fake_send_file.assert_called_once()


def test_security_scan_requires_api_key(monkeypatch):
    client = app.test_client()
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)

    response = client.post(
        "/api/security-scan",
        data={
            "operation": SECURITY_OPERATION,
            "file": (BytesIO(b"fake docx content"), "contrato.docx"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.json == {"error": "Configure a variavel VIRUSTOTAL_API_KEY."}


def test_security_scan_returns_virus_total_result(monkeypatch):
    client = app.test_client()
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "fake-key")

    def fake_scan_file(_self, content, filename):
        assert content == b"fake docx content"
        assert filename == "contrato.docx"
        return VirusTotalResult(
            status="safe",
            message="Nenhuma ameaca foi encontrada na ultima analise conhecida.",
            sha256="abc123",
            stats={
                "harmless": 10,
                "malicious": 0,
                "suspicious": 0,
                "undetected": 2,
            },
        )

    monkeypatch.setattr("src.main.VirusTotalClient.scan_file", fake_scan_file)

    response = client.post(
        "/api/security-scan",
        data={
            "operation": SECURITY_OPERATION,
            "file": (BytesIO(b"fake docx content"), "contrato.docx"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json == {
        "status": "safe",
        "message": "Nenhuma ameaca foi encontrada na ultima analise conhecida.",
        "sha256": "abc123",
        "stats": {
            "harmless": 10,
            "malicious": 0,
            "suspicious": 0,
            "undetected": 2,
        },
        "analysis_id": None,
    }


def test_pdf_merge_returns_single_pdf_with_all_pages():
    client = app.test_client()

    response = client.post(
        "/api/pdf/merge",
        data={
            "files": [
                (BytesIO(make_pdf(2)), "primeiro.pdf"),
                (BytesIO(make_pdf(3)), "segundo.pdf"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "pdf-unificado.pdf" in response.headers["Content-Disposition"]
    assert len(PdfReader(BytesIO(response.data)).pages) == 5


def test_pdf_merge_requires_at_least_two_files():
    client = app.test_client()

    response = client.post(
        "/api/pdf/merge",
        data={"files": [(BytesIO(make_pdf(1)), "unico.pdf")]},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Envie pelo menos dois arquivos PDF."}


def test_pdf_merge_rejects_non_pdf_extension():
    client = app.test_client()

    response = client.post(
        "/api/pdf/merge",
        data={
            "files": [
                (BytesIO(make_pdf(1)), "documento.pdf"),
                (BytesIO(b"not a pdf"), "imagem.png"),
            ],
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Apenas arquivos PDF sao permitidos."}


def test_pdf_split_returns_selected_page_range():
    client = app.test_client()

    response = client.post(
        "/api/pdf/split",
        data={
            "file": (BytesIO(make_pdf(5)), "relatorio.pdf"),
            "start_page": "2",
            "end_page": "4",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "relatorio-paginas-2-4.pdf" in response.headers["Content-Disposition"]
    assert len(PdfReader(BytesIO(response.data)).pages) == 3


def test_pdf_split_rejects_page_range_outside_document():
    client = app.test_client()

    response = client.post(
        "/api/pdf/split",
        data={
            "file": (BytesIO(make_pdf(5)), "relatorio.pdf"),
            "start_page": "1",
            "end_page": "10",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {
        "error": (
            "O intervalo solicitado vai ate a pagina 10, "
            "mas o PDF possui apenas 5 paginas."
        )
    }


def test_pdf_split_rejects_inverted_range():
    client = app.test_client()

    response = client.post(
        "/api/pdf/split",
        data={
            "file": (BytesIO(make_pdf(5)), "relatorio.pdf"),
            "start_page": "4",
            "end_page": "2",
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {
        "error": "A pagina inicial deve ser menor ou igual a final."
    }


def test_security_analysis_returns_completed_result(monkeypatch):
    client = app.test_client()
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "fake-key")

    def fake_get_analysis_result(_self, analysis_id, sha256):
        assert analysis_id == "analysis-123"
        assert sha256 == "abc123"
        return VirusTotalResult(
            status="safe",
            message="Nenhuma ameaca foi encontrada na ultima analise conhecida.",
            sha256=sha256,
            stats={
                "harmless": 10,
                "malicious": 0,
                "suspicious": 0,
                "undetected": 2,
            },
        )

    monkeypatch.setattr(
        "src.main.VirusTotalClient.get_analysis_result",
        fake_get_analysis_result,
    )

    response = client.get("/api/security-analysis/analysis-123?sha256=abc123")

    assert response.status_code == 200
    assert response.json == {
        "status": "safe",
        "message": "Nenhuma ameaca foi encontrada na ultima analise conhecida.",
        "sha256": "abc123",
        "stats": {
            "harmless": 10,
            "malicious": 0,
            "suspicious": 0,
            "undetected": 2,
        },
        "analysis_id": None,
    }
