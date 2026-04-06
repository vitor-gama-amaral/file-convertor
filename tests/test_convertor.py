import os
import pytest
from docx import Document
from src.convertor.word2pdfconvertor import TransformadorWordToPDF 

def test_conversion_creates_file(tmp_path):
    input_path = os.path.join(tmp_path, "teste.docx")
    doc = Document()
    doc.add_paragraph("Teste de conversão real.")
    doc.save(input_path)
    
    output_path = os.path.join(tmp_path, "teste.pdf")
    
    conv = TransformadorWordToPDF()
    conv.transform(input_path, output_path)
    
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0