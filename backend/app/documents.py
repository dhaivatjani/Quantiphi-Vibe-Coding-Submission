"""Extract job-description text from an uploaded PDF or plain-text file."""
import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .matcher import MAX_JD_LENGTH

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 20


class DocumentError(Exception):
    pass


def extract_text(filename: str, data: bytes) -> str:
    if len(data) > MAX_UPLOAD_BYTES:
        raise DocumentError("File is larger than 5 MB.")
    name = (filename or "").lower()
    if name.endswith(".pdf") or data.startswith(b"%PDF"):
        try:
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages[:MAX_PDF_PAGES])
        except (PdfReadError, ValueError, KeyError):
            raise DocumentError("This PDF couldn't be read. Try another file or paste the text.")
    elif name.endswith(".txt"):
        text = data.decode("utf-8", errors="replace")
    else:
        raise DocumentError("Upload a PDF or .txt file.")
    text = text.strip()
    if not text:
        raise DocumentError("No text found in this file. Scanned PDFs aren't supported; paste the text instead.")
    return text[:MAX_JD_LENGTH]
