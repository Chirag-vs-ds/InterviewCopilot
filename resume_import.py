"""Text-only local résumé extraction. No OCR, cloud calls or persistent copies."""
from pathlib import Path


def extract_resume(path):
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Resume is larger than 20 MB. Paste the relevant text instead.")
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDF. Paste the text or import an unlocked copy.")
        if len(reader.pages) > 50:
            raise ValueError("Resume exceeds 50 pages. Paste relevant text instead.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif path.suffix.lower() == ".docx":
        from docx import Document
        from docx.text.paragraph import Paragraph
        def blocks(container):
            for block in container.iter_inner_content():
                if isinstance(block, Paragraph):
                    yield block.text
                else:
                    for row in block.rows:
                        for cell in row.cells:
                            yield from blocks(cell)
        document = Document(path)
        text = "\n".join(blocks(document))
    else:
        raise ValueError("Choose a PDF or DOCX resume.")
    if not text.strip():
        raise ValueError("No readable text found. For a scanned PDF, paste text into the source box.")
    if len(text) > 150000:
        raise ValueError("Too much text. Paste only relevant resume sections instead.")
    return text.strip()
