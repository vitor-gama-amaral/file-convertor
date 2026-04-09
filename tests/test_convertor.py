from io import BytesIO
from unittest.mock import MagicMock

from src.main import UPLOAD_OPERATION, app


def test_home_page_loads():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Word para PDF" in html
    assert "/operacoes/word-para-pdf" in html


def test_operation_page_loads():
    client = app.test_client()

    response = client.get("/operacoes/word-para-pdf")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Enviar arquivo" in html
    assert 'value="docx_to_pdf"' in html


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
