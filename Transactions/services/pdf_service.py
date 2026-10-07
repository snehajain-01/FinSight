from pypdf import PdfReader


def extract_text_from_pdf(pdf_path):

    reader = PdfReader(
        pdf_path
    )

    extracted_text = ""


    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:

            extracted_text += page_text + "\n"


    return extracted_text