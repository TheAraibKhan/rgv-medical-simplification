import logging
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.schemas.common import CompareRequest, CompareResponse, ReportUploadResponse
from app.schemas.health import HealthResponse
from app.services.pipeline import pipeline
from app.services.report_upload import ReportExtractionError, extract_report, is_readable_report_text

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    active_mode = pipeline.active_mode
    return HealthResponse(
        service="rgv-medical-simplification",
        status="ok",
        mode=active_mode,
        llm_provider="vllm" if active_mode == "research" else "demo",
        verifier_provider=settings.verifier_provider if active_mode == "research" else "heuristic",
    )


@router.post("/compare", response_model=CompareResponse)
def compare(payload: CompareRequest) -> CompareResponse:
    if not is_readable_report_text(payload.report):
        raise HTTPException(
            status_code=422,
            detail=(
                "The report text does not appear readable, so it was not analyzed. "
                "Paste readable report text or upload a searchable PDF with embedded text."
            ),
        )
    try:
        return pipeline.compare(payload)
    except Exception as exc:
        logger.exception("Comparison pipeline failed (mode=%s)", pipeline.active_mode)
        raise HTTPException(
            status_code=503,
            detail="The comparison pipeline failed. Check the local model, retrieval snapshot, and verifier configuration.",
        ) from exc


@router.post("/report/upload", response_model=ReportUploadResponse)
async def upload_report(file: UploadFile = File(...)) -> ReportUploadResponse:
    filename = file.filename or ""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    supported_types = {"pdf", "txt", "docx", "png", "jpg", "jpeg"}
    if suffix not in supported_types:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a PDF, TXT, or DOCX report; images require local OCR.",
        )

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum upload size is {settings.max_upload_bytes // (1024 * 1024)} MB.",
        )

    try:
        extracted = extract_report(filename, content)
    except ReportExtractionError as exc:
        logger.warning("Report extraction rejected (%s): %s", suffix or "unknown", exc)
        status_code = 415 if "Unsupported file type" in str(exc) or "OCR is not available" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    logger.info("Report text extracted locally (type=%s, characters=%d)", extracted.source_type, len(extracted.text))
    return ReportUploadResponse(
        report_id=str(uuid.uuid4()),
        filename=filename,
        source_type=extracted.source_type,
        file_size_bytes=len(content),
        extracted_text=extracted.text,
        page_count=extracted.page_count,
    )
