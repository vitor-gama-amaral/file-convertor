import shutil
from pathlib import Path
from tempfile import mkdtemp

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
except ModuleNotFoundError:
    from src.convertor.word2pdfconvertor import TransformadorWordToPDF

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_OPERATION = "docx_to_pdf"
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
        "operation.html",
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


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
