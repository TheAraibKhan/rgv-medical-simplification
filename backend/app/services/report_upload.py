from __future__ import annotations

import io
import shutil
import unicodedata
from dataclasses import dataclass


class ReportExtractionError(ValueError):
    """A report could not be safely decoded into text."""


@dataclass(frozen=True)
class ExtractedReport:
    source_type: str
    text: str
    page_count: int | None = None


def extract_report(filename: str, content: bytes) -> ExtractedReport:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not content:
        raise ReportExtractionError("The uploaded file is empty.")

    if suffix == "txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReportExtractionError("TXT reports must be valid UTF-8 text.") from exc
        source_type = "TXT"
        page_count = None
    elif suffix == "pdf":
        text = _extract_pdf(content)
        source_type = "PDF"
        page_count = None
    elif suffix == "docx":
        text = _extract_docx(content)
        source_type = "DOCX"
        page_count = None
    elif suffix in {"png", "jpg", "jpeg"}:
        text = _extract_image(content)
        source_type = "PNG" if suffix == "png" else "JPG"
        page_count = None
    else:
        raise ReportExtractionError("Unsupported file type. Upload a PDF, TXT, or DOCX report.")

    if not text.strip():
        raise ReportExtractionError(
            f"No text could be extracted from this {source_type} file. "
            "For scanned PDFs or images, use a locally installed OCR tool or upload a text-based report."
        )
    if not is_readable_report_text(text):
        raise ReportExtractionError(
            f"Text was found in this {source_type} file, but it could not be decoded into readable report text. "
            "It was not analyzed. Try a searchable PDF with embedded text, paste readable report text, "
            "or run local OCR and create a searchable PDF."
        )
    if source_type == "PDF":
        page_count = _pdf_page_count(content)
    return ExtractedReport(source_type=source_type, text=text, page_count=page_count)


def is_readable_report_text(text: str) -> bool:
    visible_characters = [character for character in text if not character.isspace()]
    if not visible_characters:
        return False

    categories = [unicodedata.category(character) for character in visible_characters]
    word_characters = sum(category[0] in {"L", "N", "M"} for category in categories)
    readable_characters = sum(
        category[0] in {"L", "N", "M"} or category[0] == "P"
        for category in categories
    )
    return (
        word_characters >= 3
        and word_characters / len(visible_characters) >= 0.1
        and readable_characters / len(visible_characters) >= 0.65
    )


def _extract_pdf(content: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=True)
        pages = [
            page.extract_text(extraction_mode="layout") or ""
            if page.get_contents() is not None
            else ""
            for page in reader.pages
        ]
        return "\n\f\n".join(pages)
    except Exception as exc:
        raise ReportExtractionError(
            "The PDF could not be read. Check that it is a valid, text-based PDF."
        ) from exc


def _pdf_page_count(content: bytes) -> int:
    try:
        from pypdf import PdfReader

        return len(PdfReader(io.BytesIO(content), strict=True).pages)
    except Exception as exc:
        raise ReportExtractionError(
            "The PDF could not be read. Check that it is a valid, text-based PDF."
        ) from exc


def _extract_docx(content: bytes) -> str:
    try:
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        document = Document(io.BytesIO(content))
        blocks: list[str] = []
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                blocks.append(block.text)
            elif isinstance(block, Table):
                blocks.extend(
                    " | ".join(cell.text for cell in row.cells)
                    for row in block.rows
                )
        return "\n".join(blocks)
    except Exception as exc:
        raise ReportExtractionError(
            "The DOCX could not be read. Check that it is a valid Word document."
        ) from exc


def _extract_image(content: bytes) -> str:
    if shutil.which("tesseract") is None:
        raise ReportExtractionError(
            "Local OCR is not available. Install Tesseract and pytesseract, or upload a PDF, TXT, or DOCX."
        )
    try:
        import pytesseract
        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            return pytesseract.image_to_string(image)
    except ImportError as exc:
        raise ReportExtractionError(
            "Local OCR is not available. Install pytesseract, or upload a PDF, TXT, or DOCX."
        ) from exc
    except Exception as exc:
        raise ReportExtractionError(
            "Local OCR could not extract text from this image. Try a clearer PNG or JPG."
        ) from exc
