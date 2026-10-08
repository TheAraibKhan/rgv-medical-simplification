from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional


class ReportSectionType(str, Enum):
    HEADER = "HEADER"
    PATIENT_METADATA = "PATIENT_METADATA"
    TEST_HEADER = "TEST_HEADER"
    TEST_RESULT = "TEST_RESULT"
    PENDING_STATUS = "PENDING_STATUS"
    REFERENCE_INTERVAL = "REFERENCE_INTERVAL"
    FINDING = "FINDING"
    INTERPRETATION = "INTERPRETATION"
    COMMENT = "COMMENT"
    NOTE = "NOTE"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    RISK_GUIDANCE = "RISK_GUIDANCE"
    TREATMENT_GUIDANCE = "TREATMENT_GUIDANCE"
    REFERENCE = "REFERENCE"
    INSTRUCTION = "INSTRUCTION"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    FOOTER = "FOOTER"
    UNKNOWN = "UNKNOWN"


class SourceSpan(BaseModel):
    start: int
    end: int
    page: Optional[int] = None


class ReportSection(BaseModel):
    section: ReportSectionType
    text: str
    source_span: SourceSpan


class StructuredTestResult(BaseModel):
    test_name: str
    canonical_name: Optional[str] = None
    source_name: Optional[str] = None
    short_name: Optional[str] = None
    abbreviation: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_interval: Optional[str] = None
    flag: Optional[str] = None
    status: str = "reported"
    section: ReportSectionType
    source_section: Optional[ReportSectionType] = None
    patient_specific: bool
    retrieval_eligible: bool
    explanation_eligible: bool
    source_text: str
    source_page: Optional[int] = None
    source_span: SourceSpan


class StructuredPendingStatus(BaseModel):
    test_names: list[str] = Field(default_factory=list)
    source_text: str
    section: ReportSectionType = ReportSectionType.PENDING_STATUS
    source_page: Optional[int] = None
    source_span: SourceSpan


class StructuredFinding(BaseModel):
    concept: str
    text: str
    section: ReportSectionType
    patient_specific: bool
    negated: bool
    retrieval_eligible: bool
    explanation_eligible: bool
    source_text: str
    source_page: Optional[int] = None
    source_span: SourceSpan


class ExcludedReportItem(BaseModel):
    source_text: str
    section: ReportSectionType
    reason: str
    patient_specific: bool = False
    retrieval_eligible: bool = False
    shown_to_patient: bool = False
    available_to_clinician: bool = True
    source_page: Optional[int] = None
    source_span: SourceSpan


class ReportReference(BaseModel):
    reference_type: str = "report_reference"
    title: Optional[str] = None
    citation_text: str
    source_section: ReportSectionType
    source_page: Optional[int] = None
    source_span: SourceSpan


class StructuredMedicalReport(BaseModel):
    raw_source: str
    patient_source_text: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    results: list[StructuredTestResult] = Field(default_factory=list)
    pending_statuses: list[StructuredPendingStatus] = Field(default_factory=list)
    findings: list[StructuredFinding] = Field(default_factory=list)
    general_information: list[StructuredFinding] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    retrieval_eligible_items: list[StructuredFinding] = Field(default_factory=list)
    excluded_items: list[ExcludedReportItem] = Field(default_factory=list)
    references: list[ReportReference] = Field(default_factory=list)


class ClaimType(str, Enum):
    PATIENT_SPECIFIC = "PATIENT_SPECIFIC"
    GENERAL_EXPLANATORY = "GENERAL_EXPLANATORY"


class VerificationLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNSUPPORTED_PATIENT_CLAIM = "UNSUPPORTED_PATIENT_CLAIM"


class Evidence(BaseModel):
    source: str
    title: str
    text: str
    url: Optional[str] = None
    score: float = 0.0
    document_id: Optional[str] = None
    snapshot_date: Optional[str] = None


class Claim(BaseModel):
    claim_id: str
    text: str
    claim_type: ClaimType
    polarity: str = "AFFIRMED"
    units: Optional[str] = None


class ClaimVerification(BaseModel):
    claim_id: str
    label: VerificationLabel
    evidence: list[Evidence] = []
    reason: str
    original_claim: str = ""
    final_claim: Optional[str] = None
    changed: bool = False


class Finding(BaseModel):
    text: str
    polarity: str
    section: Optional[ReportSectionType] = None
    patient_specific: bool = True
    retrieval_eligible: bool = False
    source_text: Optional[str] = None
    source_span: Optional[SourceSpan] = None


class ConditionResult(BaseModel):
    condition: str
    output: str
    claims: list[Claim] = []
    verifications: list[ClaimVerification] = []
    evidence: list[Evidence] = []
    latency_ms: float = 0.0
    mode: str = "demo"
    first_pass_output: Optional[str] = None
    correction_applied: bool = False
    correction_note: Optional[str] = None


class CompareRequest(BaseModel):
    report: str = Field(min_length=5)
    top_k: int = Field(default=3, ge=1, le=10)


class CompareResponse(BaseModel):
    report: str
    findings: list[Finding] = []
    structured_report: Optional[StructuredMedicalReport] = None
    mode: str = "demo"
    b1: ConditionResult
    b2: ConditionResult
    b3: ConditionResult


class ReportUploadResponse(BaseModel):
    report_id: str
    filename: str
    source_type: str
    file_size_bytes: int
    extracted_text: str
    page_count: Optional[int] = None
    status: str = "extracted"
