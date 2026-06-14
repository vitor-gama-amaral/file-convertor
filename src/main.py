import os
import shutil
from io import BytesIO
from pathlib import Path
from tempfile import gettempdir, mkdtemp

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from werkzeug.utils import secure_filename

try:
    from convertor.word2pdfconvertor import TransformadorWordToPDF
    from document_vault import (
        DocumentVaultError,
        DocumentVaultService,
        start_document_cleanup_scheduler,
    )
    from security.virus_total import VirusTotalClient, VirusTotalError
except ModuleNotFoundError:
    from src.convertor.word2pdfconvertor import TransformadorWordToPDF
    from src.document_vault import (
        DocumentVaultError,
        DocumentVaultService,
        start_document_cleanup_scheduler,
    )
    from src.security.virus_total import VirusTotalClient, VirusTotalError

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
if load_dotenv is not None:
    load_dotenv(ENV_PATH)
elif ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key and not key.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

UPLOAD_OPERATION = "docx_to_pdf"
SECURITY_OPERATION = "virus_scan"
VAULT_OPERATION = "temporary_pdf_link"
PDF_OPERATION = "pdf_tools"
OPERATIONS = {
    UPLOAD_OPERATION: {
        "slug": "word-para-pdf",
        "title": "Word para PDF",
        "subtitle": "Transforme arquivos .docx em PDF com download imediato.",
        "accept": ".docx",
        "button": "Selecionar arquivo Word",
        "description": (
            "Envie seu documento .docx e receba o PDF convertido logo em seguida."
        ),
        "template": "operation.html",
        "icon": "PDF",
    },
    SECURITY_OPERATION: {
        "slug": "verificar-virus",
        "title": "Verificar virus",
        "subtitle": "Consulte a VirusTotal para avaliar possiveis ameacas.",
        "accept": ".doc,.docx,.pdf,.txt,.png,.jpg,.jpeg",
        "button": "Selecionar arquivo",
        "description": (
            "Envie um arquivo para consultar a VirusTotal e verificar se existe "
            "algum alerta de seguranca."
        ),
        "template": "security_check.html",
        "icon": "SEC",
    },
    VAULT_OPERATION: {
        "slug": "link-temporario-pdf",
        "title": "Link temporario",
        "subtitle": "Guarde um PDF validado e gere um link curto por 24 horas.",
        "accept": ".pdf",
        "button": "Selecionar PDF",
        "description": (
            "Envie um PDF pronto para registrar no cofre temporario e compartilhar "
            "um link seguro de download."
        ),
        "template": "document_vault.html",
        "icon": "LINK",
    },
    PDF_OPERATION: {
        "slug": "editar-pdf",
        "title": "Editar PDF",
        "subtitle": "Una varios PDFs ou separe um intervalo de paginas.",
        "accept": ".pdf",
        "button": "Selecionar PDF",
        "description": (
            "Combine documentos PDF em um unico arquivo ou extraia apenas as "
            "paginas que voce precisa."
        ),
        "template": "pdf_tools.html",
        "icon": "PDF",
    },
}

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
TMP_DIR = Path(gettempdir()) / "file-convertor"
TMP_DIR.mkdir(exist_ok=True)
DOCUMENT_VAULT_DIR = Path(os.environ.get("DOCUMENT_VAULT_DIR", TMP_DIR / "vault"))
app.config["DOCUMENT_VAULT_DIR"] = str(DOCUMENT_VAULT_DIR)


@app.get("/")
def index():
    return render_template("index.html", operations=OPERATIONS)


@app.get("/operacoes/<slug>")
def operation_page(slug):
    operation_key = next(
        (key for key, value in OPERATIONS.items() if value["slug"] == slug),
        None,
    )
    if operation_key is None:
        return jsonify({"error": "Operacao invalida."}), 404

    return render_template(
        OPERATIONS[operation_key]["template"],
        operation_key=operation_key,
        operation=OPERATIONS[operation_key],
    )


def get_document_vault_service() -> DocumentVaultService:
    service = app.extensions.get("document_vault")
    if service is None:
        service = DocumentVaultService.from_env(DOCUMENT_VAULT_DIR)
        app.extensions["document_vault"] = service
    return service


def validate_uploaded_file_security(content: bytes, filename: str):
    api_key = os.environ.get("VIRUSTOTAL_API_KEY")
    if not api_key:
        return jsonify({"error": "Configure a variavel VIRUSTOTAL_API_KEY."}), 500

    try:
        result = VirusTotalClient(api_key).scan_file(content, filename)
    except VirusTotalError as error:
        return jsonify({"error": str(error)}), 502

    if result.status == "queued":
        return (
            jsonify(
                {
                    "error": (
                        "A VirusTotal ainda esta processando este arquivo. "
                        "Tente novamente em alguns instantes."
                    )
                }
            ),
            409,
        )

    if result.status != "safe":
        return jsonify({"error": result.message}), 422

    return None


@app.post("/api/convert")
def convert_file():
    operation = request.form.get("operation")
    uploaded_file = request.files.get("file")

    if operation != UPLOAD_OPERATION:
        return jsonify({"error": "Operacao invalida."}), 400

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Selecione um arquivo .docx."}), 400

    filename = secure_filename(uploaded_file.filename)
    if not filename.lower().endswith(".docx"):
        return jsonify({"error": "Apenas arquivos .docx sao permitidos."}), 400

    content = uploaded_file.read()
    if not content:
        return jsonify({"error": "O arquivo enviado esta vazio."}), 400

    security_error = validate_uploaded_file_security(content, filename)
    if security_error is not None:
        return security_error

    tmp_path = Path(mkdtemp(dir=TMP_DIR))
    input_path = tmp_path / filename
    output_path = tmp_path / f"{input_path.stem}.pdf"

    try:
        input_path.write_bytes(content)

        converter = TransformadorWordToPDF(str(input_path), str(output_path))
        converter.transform()

        registration = get_document_vault_service().store_pdf(
            output_path,
            output_path.name,
        )
    except DocumentVaultError as error:
        return jsonify({"error": str(error)}), 500
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

    return (
        jsonify(
            {
                "download_url": url_for(
                    "document_page",
                    token=registration.token,
                    _external=True,
                ),
                "expires_at": registration.record.expires_at.isoformat(),
                "filename": registration.record.filename,
                "file_size": registration.record.file_size,
            }
        ),
        201,
    )


@app.post("/api/documents")
def register_document():
    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Selecione um arquivo PDF."}), 400

    filename = secure_filename(uploaded_file.filename)
    if not filename.lower().endswith(".pdf"):
        return jsonify({"error": "Apenas arquivos PDF podem ser registrados."}), 400

    tmp_path = Path(mkdtemp(dir=TMP_DIR))
    input_path = tmp_path / filename

    try:
        content = uploaded_file.read()
        if not content:
            return jsonify({"error": "O arquivo enviado esta vazio."}), 400

        input_path.write_bytes(content)
        registration = get_document_vault_service().store_pdf(input_path, filename)
    except DocumentVaultError as error:
        return jsonify({"error": str(error)}), 500
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

    return (
        jsonify(
            {
                "download_url": url_for(
                    "document_page",
                    token=registration.token,
                    _external=True,
                ),
                "expires_at": registration.record.expires_at.isoformat(),
                "filename": registration.record.filename,
                "file_size": registration.record.file_size,
            }
        ),
        201,
    )


@app.get("/d/<token>")
def document_page(token):
    return render_template("document.html", token=token)


@app.get("/api/documents/<token>")
def document_status(token):
    try:
        lookup = get_document_vault_service().lookup(token)
    except DocumentVaultError as error:
        return jsonify({"error": str(error)}), 500

    if lookup.status != "available" or lookup.record is None:
        return (
            jsonify(
                {
                    "status": "expired",
                    "message": "O documento expirou e foi removido.",
                }
            ),
            404,
        )

    return jsonify(
        {
            "status": "available",
            "document": lookup.record.to_public_dict(),
            "download_url": url_for("download_document", token=token),
        }
    )


@app.get("/api/documents/<token>/download")
def download_document(token):
    try:
        lookup = get_document_vault_service().lookup(token)
    except DocumentVaultError as error:
        return jsonify({"error": str(error)}), 500

    if lookup.status != "available" or lookup.record is None:
        return redirect(url_for("document_page", token=token))

    return send_file(
        lookup.record.stored_path,
        as_attachment=True,
        download_name=lookup.record.filename,
        mimetype=lookup.record.mime_type,
    )


def _read_uploaded_pdf(uploaded_file):
    filename = secure_filename(uploaded_file.filename or "")
    if not filename:
        raise ValueError("Selecione um arquivo PDF.")

    if not filename.lower().endswith(".pdf"):
        raise ValueError("Apenas arquivos PDF sao permitidos.")

    content = uploaded_file.read()
    if not content:
        raise ValueError("O arquivo enviado esta vazio.")

    try:
        reader = PdfReader(BytesIO(content))
        page_count = len(reader.pages)
    except (PdfReadError, ValueError, TypeError) as error:
        raise ValueError("Nao foi possivel ler o PDF enviado.") from error

    if page_count == 0:
        raise ValueError("O PDF enviado nao possui paginas.")

    return filename, reader


def _write_pdf_response(writer, download_name):
    output = BytesIO()
    writer.write(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/pdf",
    )


@app.post("/api/pdf/merge")
def merge_pdf_files():
    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        uploaded_files = request.files.getlist("files[]")

    uploaded_files = [file for file in uploaded_files if file and file.filename]
    if len(uploaded_files) < 2:
        return jsonify({"error": "Envie pelo menos dois arquivos PDF."}), 400

    writer = PdfWriter()

    try:
        for uploaded_file in uploaded_files:
            _filename, reader = _read_uploaded_pdf(uploaded_file)
            for page in reader.pages:
                writer.add_page(page)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return _write_pdf_response(writer, "pdf-unificado.pdf")


@app.post("/api/pdf/split")
def split_pdf_file():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Selecione um arquivo PDF."}), 400

    try:
        start_page = int(request.form.get("start_page", ""))
        end_page = int(request.form.get("end_page", ""))
    except ValueError:
        return jsonify({"error": "Informe paginas inicial e final validas."}), 400

    if start_page < 1 or end_page < 1:
        return jsonify({"error": "As paginas devem ser maiores que zero."}), 400

    if start_page > end_page:
        return (
            jsonify({"error": "A pagina inicial deve ser menor ou igual a final."}),
            400,
        )

    try:
        filename, reader = _read_uploaded_pdf(uploaded_file)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    page_count = len(reader.pages)
    if end_page > page_count:
        return jsonify(
            {
                "error": (
                    f"O intervalo solicitado vai ate a pagina {end_page}, "
                    f"mas o PDF possui apenas {page_count} paginas."
                )
            }
        ), 400

    writer = PdfWriter()
    for page_number in range(start_page - 1, end_page):
        writer.add_page(reader.pages[page_number])

    output_name = f"{Path(filename).stem}-paginas-{start_page}-{end_page}.pdf"
    return _write_pdf_response(writer, output_name)


@app.post("/api/security-scan")
def security_scan():
    operation = request.form.get("operation")
    uploaded_file = request.files.get("file")

    if operation != SECURITY_OPERATION:
        return jsonify({"error": "Operacao invalida."}), 400

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({"error": "Selecione um arquivo para verificar."}), 400

    api_key = os.environ.get("VIRUSTOTAL_API_KEY")
    if not api_key:
        return jsonify({"error": "Configure a variavel VIRUSTOTAL_API_KEY."}), 500

    content = uploaded_file.read()
    if not content:
        return jsonify({"error": "O arquivo enviado esta vazio."}), 400

    try:
        result = VirusTotalClient(api_key).scan_file(content, uploaded_file.filename)
    except VirusTotalError as error:
        return jsonify({"error": str(error)}), 502

    return jsonify(result.to_dict())


@app.get("/api/security-analysis/<analysis_id>")
def security_analysis(analysis_id):
    api_key = os.environ.get("VIRUSTOTAL_API_KEY")
    sha256 = request.args.get("sha256", "")

    if not api_key:
        return jsonify({"error": "Configure a variavel VIRUSTOTAL_API_KEY."}), 500

    if not sha256:
        return jsonify({"error": "Informe o hash SHA-256 do arquivo."}), 400

    try:
        result = VirusTotalClient(api_key).get_analysis_result(analysis_id, sha256)
    except VirusTotalError as error:
        return jsonify({"error": str(error)}), 502

    return jsonify(result.to_dict())


def maybe_start_document_cleanup_scheduler():
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        start_document_cleanup_scheduler(app)


def main():
    maybe_start_document_cleanup_scheduler()
    app.run(debug=True)


maybe_start_document_cleanup_scheduler()


if __name__ == "__main__":
    main()
