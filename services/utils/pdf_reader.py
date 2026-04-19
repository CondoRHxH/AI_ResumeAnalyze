import tempfile
import PyPDF2


def extract_text_from_pdf(pdf_file):
    text = ""

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(pdf_file.read())
        path = tmp.name

    with open(path, "rb") as file:
        reader = PyPDF2.PdfReader(file)

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    return text