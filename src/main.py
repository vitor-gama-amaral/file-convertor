import os
import shutil
from pathlib import Path
from tempfile import mkdtemp

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

from flask import (
    Flask,
    after_this_request,
    jsonify,
    render_template,
    request,
    send_file,
)
from werkzeug.utils import secure_filename

try:
    from convertor.word2pdfconvertor import TransformadorWordToPDF
    from security.virus_total import VirusTotalClient, VirusTotalError
except ModuleNotFoundError:
    from src.convertor.word2pdfconvertor import TransformadorWordToPDF
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
    }
}

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
TMP_DIR = BASE_DIR.parent / ".tmp"
TMP_DIR.mkdir(exist_ok=True)


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

    tmp_path = Path(mkdtemp(dir=TMP_DIR))
    input_path = tmp_path / filename
    output_path = tmp_path / f"{input_path.stem}.pdf"

    input_path.write_bytes(uploaded_file.read())

    converter = TransformadorWordToPDF(str(input_path), str(output_path))
    converter.transform()

    @after_this_request
    def cleanup(response):
        shutil.rmtree(tmp_path, ignore_errors=True)
        return response

    return send_file(
        output_path,
        as_attachment=True,
        download_name=output_path.name,
        mimetype="application/pdf",
    )


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


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
