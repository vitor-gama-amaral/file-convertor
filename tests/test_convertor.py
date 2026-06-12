from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.document_vault import DocumentVaultLookup, DocumentVaultRecord
from src.main import SECURITY_OPERATION, UPLOAD_OPERATION, VAULT_OPERATION, app
from src.security.virus_total import VirusTotalResult


def build_safe_virus_total_result():
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


def build_document_record(stored_path="C:/tmp/contrato.pdf"):
    return DocumentVaultRecord(
        id="document-123",
        token_hash="token-hash",
        filename="contrato.pdf",
        stored_path=stored_path,
        mime_type="application/pdf",
        file_size=17,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )


def test_convert_returns_generated_download_link(monkeypatch):
    client = app.test_client()
    fake_vault = MagicMock()
    fake_vault.store_pdf.return_value = SimpleNamespace(
        token="abc123token",
        record=build_document_record(),
    )

    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "fake-key")
    monkeypatch.setattr("src.main.Path.write_bytes", lambda *_args, **_kwargs: 17)
    monkeypatch.setattr(
        "src.main.TransformadorWordToPDF.transform",
        lambda self: self.output_path,
    )
    monkeypatch.setattr(
        "src.main.VirusTotalClient.scan_file",
        lambda *_args, **_kwargs: build_safe_virus_total_result(),
    )
    monkeypatch.setattr("src.main.get_document_vault_service", lambda: fake_vault)

    response = client.post(
        "/api/convert",
        data={
            "operation": UPLOAD_OPERATION,
            "file": (BytesIO(b"fake docx content"), "contrato.docx"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.json["download_url"].endswith("/d/abc123token")
    assert response.json["filename"] == "contrato.pdf"
    assert response.json["file_size"] == 17
    fake_vault.store_pdf.assert_called_once()


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


def test_convert_accepts_uppercase_docx_extension_and_returns_link(monkeypatch):
    client = app.test_client()
    fake_vault = MagicMock()
    fake_vault.store_pdf.return_value = SimpleNamespace(
        token="upper-token",
        record=build_document_record(),
    )

    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "fake-key")
    monkeypatch.setattr("src.main.Path.write_bytes", lambda *_args, **_kwargs: 17)
    monkeypatch.setattr(
        "src.main.TransformadorWordToPDF.transform",
        lambda self: self.output_path,
    )
    monkeypatch.setattr(
        "src.main.VirusTotalClient.scan_file",
        lambda *_args, **_kwargs: build_safe_virus_total_result(),
    )
    monkeypatch.setattr("src.main.get_document_vault_service", lambda: fake_vault)

    response = client.post(
        "/api/convert",
        data={
            "operation": UPLOAD_OPERATION,
            "file": (BytesIO(b"fake docx content"), "RELATORIO.DOCX"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.json["download_url"].endswith("/d/upper-token")
    fake_vault.store_pdf.assert_called_once()


def test_convert_rejects_file_when_virus_total_is_not_configured(monkeypatch):
    client = app.test_client()
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)

    response = client.post(
        "/api/convert",
        data={
            "operation": UPLOAD_OPERATION,
            "file": (BytesIO(b"fake docx content"), "contrato.docx"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 500
    assert response.json == {"error": "Configure a variavel VIRUSTOTAL_API_KEY."}


def test_home_page_shows_temporary_link_card():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Link temporario" in response.data
    assert b"/operacoes/link-temporario-pdf" in response.data


def test_temporary_link_page_renders_upload_form():
    client = app.test_client()

    response = client.get("/operacoes/link-temporario-pdf")

    assert response.status_code == 200
    assert b"Gerar link temporario" in response.data
    assert VAULT_OPERATION.encode("utf-8") not in response.data


def test_register_document_returns_generated_download_link(monkeypatch):
    client = app.test_client()
    fake_vault = MagicMock()
    fake_vault.store_pdf.return_value = SimpleNamespace(
        token="pdf-token",
        record=build_document_record(),
    )

    monkeypatch.setattr("src.main.Path.write_bytes", lambda *_args, **_kwargs: 17)
    monkeypatch.setattr("src.main.get_document_vault_service", lambda: fake_vault)

    response = client.post(
        "/api/documents",
        data={"file": (BytesIO(b"%PDF-1.4\nfake pdf\n"), "contrato.pdf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    assert response.json["download_url"].endswith("/d/pdf-token")
    assert response.json["filename"] == "contrato.pdf"
    fake_vault.store_pdf.assert_called_once()


def test_register_document_rejects_invalid_extension():
    client = app.test_client()

    response = client.post(
        "/api/documents",
        data={"file": (BytesIO(b"not a pdf"), "contrato.docx")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.json == {"error": "Apenas arquivos PDF podem ser registrados."}


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


def test_document_status_returns_available_document(monkeypatch):
    client = app.test_client()
    record = build_document_record()
    fake_vault = MagicMock()
    fake_vault.lookup.return_value = DocumentVaultLookup(
        status="available",
        record=record,
    )

    monkeypatch.setattr("src.main.get_document_vault_service", lambda: fake_vault)

    response = client.get("/api/documents/public-token")

    assert response.status_code == 200
    assert response.json["status"] == "available"
    assert response.json["document"]["filename"] == "contrato.pdf"
    assert response.json["download_url"] == "/api/documents/public-token/download"


def test_document_status_returns_expired_message(monkeypatch):
    client = app.test_client()
    fake_vault = MagicMock()
    fake_vault.lookup.return_value = DocumentVaultLookup(status="expired")

    monkeypatch.setattr("src.main.get_document_vault_service", lambda: fake_vault)

    response = client.get("/api/documents/expired-token")

    assert response.status_code == 404
    assert response.json == {
        "status": "expired",
        "message": "O documento expirou e foi removido.",
    }


def test_document_download_sends_file_when_token_is_valid(monkeypatch):
    client = app.test_client()
    fake_send_file = MagicMock()
    fake_send_file.return_value = app.response_class(
        b"%PDF-1.4\nfake pdf\n",
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=contrato.pdf"},
    )
    fake_vault = MagicMock()
    fake_vault.lookup.return_value = DocumentVaultLookup(
        status="available",
        record=build_document_record(),
    )

    monkeypatch.setattr("src.main.get_document_vault_service", lambda: fake_vault)
    monkeypatch.setattr("src.main.send_file", fake_send_file)

    response = client.get("/api/documents/public-token/download")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    fake_send_file.assert_called_once_with(
        "C:/tmp/contrato.pdf",
        as_attachment=True,
        download_name="contrato.pdf",
        mimetype="application/pdf",
    )
