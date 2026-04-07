import os

import pypandoc

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
bin_path = os.path.join(project_root, "bin", "wkhtmltopdf.exe")
wk_bin = os.path.abspath(bin_path)


class TransformadorWordToPDF:
    def __init__(self, input_path: str, output_path: str = None):
        self.input_path = input_path
        self.output_path = output_path or input_path.replace(".docx", ".pdf")

    def transform(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.input_path}")

        pypandoc.convert_file(
            self.input_path,
            "pdf",
            outputfile=self.output_path,
            extra_args=[f"--pdf-engine={wk_bin}"],
        )

        return self.output_path
