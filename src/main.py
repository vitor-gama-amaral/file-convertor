from convertor.word2pdfconvertor import TransformadorWordToPDF


def main():
    file_path = "teste.docx" 
    
    converter = TransformadorWordToPDF(file_path)
    converter.transform()

if __name__ == "__main__":
    main()