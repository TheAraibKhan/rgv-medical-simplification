export type Evidence = {
  source: string;
  title: string;
  text: string;
  url?: string | null;
  score: number;
  document_id?: string | null;
  snapshot_date?: string | null;
};

export type Claim = {
  claim_id: string;
  text: string;
  claim_type: "PATIENT_SPECIFIC" | "GENERAL_EXPLANATORY";
  polarity: string;
  units?: string | null;
};

export type Verification = {
  claim_id: string;
  label: "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED" | "NEEDS_REVIEW" | "UNSUPPORTED_PATIENT_CLAIM";
  evidence: Evidence[];
  reason: string;
  original_claim?: string;
  final_claim?: string | null;
  changed?: boolean;
};

export type Finding = {
  text: string;
  polarity: "AFFIRMED" | "NEGATED" | string;
  section?: string | null;
  patient_specific?: boolean;
  retrieval_eligible?: boolean;
  source_text?: string | null;
  source_span?: SourceSpan | null;
};

export type SourceSpan = {
  start: number;
  end: number;
  page?: number | null;
};

export type StructuredTestResult = {
  test_name: string;
  canonical_name?: string | null;
  source_name?: string | null;
  short_name?: string | null;
  abbreviation?: string | null;
  value?: string | null;
  unit?: string | null;
  reference_interval?: string | null;
  flag?: string | null;
  status: string;
  section: string;
  patient_specific: boolean;
  retrieval_eligible: boolean;
  explanation_eligible: boolean;
  source_text: string;
  source_page?: number | null;
  source_span: SourceSpan;
};

export type StructuredFinding = {
  concept: string;
  text: string;
  section: string;
  patient_specific: boolean;
  negated: boolean;
  retrieval_eligible: boolean;
  explanation_eligible: boolean;
  source_text: string;
  source_page?: number | null;
  source_span: SourceSpan;
};

export type ExcludedReportItem = {
  source_text: string;
  section: string;
  reason: string;
  patient_specific: boolean;
  retrieval_eligible: boolean;
  shown_to_patient: boolean;
  available_to_clinician: boolean;
  source_page?: number | null;
  source_span: SourceSpan;
};

export type ReportReference = {
  reference_type: string;
  title?: string | null;
  citation_text: string;
  source_section: string;
  source_page?: number | null;
  source_span: SourceSpan;
};

export type StructuredMedicalReport = {
  raw_source: string;
  patient_source_text: string;
  sections?: ReportSection[];
  results: StructuredTestResult[];
  findings: StructuredFinding[];
  general_information: StructuredFinding[];
  retrieval_queries: string[];
  retrieval_eligible_items: StructuredFinding[];
  excluded_items: ExcludedReportItem[];
  references: ReportReference[];
};

export type ReportSection = {
  section: string;
  text: string;
  source_span: SourceSpan;
};

export type Condition = {
  condition: string;
  output: string;
  claims: Claim[];
  verifications: Verification[];
  evidence: Evidence[];
  latency_ms: number;
  mode: string;
  first_pass_output?: string | null;
  correction_applied: boolean;
  correction_note?: string | null;
};

export type CompareResponse = {
  report: string;
  findings: Finding[];
  structured_report?: StructuredMedicalReport | null;
  mode: "demo" | "research" | string;
  b1: Condition;
  b2: Condition;
  b3: Condition;
};

export type NormalizedAnalysisResponse = {
  raw: CompareResponse;
  report: string;
  structuredResults: StructuredTestResult[];
  availableResults: StructuredTestResult[];
  pendingResults: StructuredTestResult[];
  generalInformation: StructuredFinding[];
  retrievedEvidence: Evidence[];
  claims: Claim[];
  verifications: Verification[];
  warnings: string[];
};

export type UploadedReport = {
  report_id: string;
  filename: string;
  source_type: string;
  file_size_bytes: number;
  extracted_text: string;
  page_count?: number | null;
  status: string;
};

export type ComparisonErrorCategory = "connection" | "invalid-request" | "backend" | "response";

export class ComparisonError extends Error {
  constructor(
    message: string,
    readonly category: ComparisonErrorCategory,
  ) {
    super(message);
    this.name = "ComparisonError";
  }
}

export class BackendConnectionError extends ComparisonError {
  constructor() {
    super("The backend is unavailable. Check that FastAPI is running and the Next.js API proxy is configured.", "connection");
    this.name = "BackendConnectionError";
  }
}

export class InvalidRequestError extends ComparisonError {
  constructor(message = "Enter a report with at least 5 characters and try again.") {
    super(message, "invalid-request");
    this.name = "InvalidRequestError";
  }
}

export class UnexpectedResponseError extends ComparisonError {
  constructor() {
    super("The backend returned an unexpected comparison response. Please retry.", "response");
    this.name = "UnexpectedResponseError";
  }
}

const configuredApiBase = process.env.NEXT_PUBLIC_API_URL?.trim() || "/api";
const isDevelopment = process.env.NODE_ENV !== "production";

function devLog(message: string, data?: Record<string, unknown>): void {
  if (isDevelopment) console.info(message, data ?? {});
}

function compareUrl(): string {
  return `${apiBaseUrl()}/compare`;
}

function apiBaseUrl(): string {
  const base = configuredApiBase.replace(/\/+$/, "");
  return base.endsWith("/api") ? base : `${base}/api`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isEvidence(value: unknown): value is Evidence {
  return isRecord(value)
    && typeof value.source === "string"
    && typeof value.title === "string"
    && typeof value.text === "string"
    && typeof value.score === "number"
    && (value.url === undefined || value.url === null || typeof value.url === "string")
    && (value.document_id === undefined || value.document_id === null || typeof value.document_id === "string")
    && (value.snapshot_date === undefined || value.snapshot_date === null || typeof value.snapshot_date === "string");
}

function isClaim(value: unknown): value is Claim {
  return isRecord(value)
    && typeof value.claim_id === "string"
    && typeof value.text === "string"
    && (value.claim_type === "PATIENT_SPECIFIC" || value.claim_type === "GENERAL_EXPLANATORY")
    && typeof value.polarity === "string"
    && (value.units === undefined || value.units === null || typeof value.units === "string");
}

function isVerification(value: unknown): value is Verification {
  return isRecord(value)
    && typeof value.claim_id === "string"
    && (value.label === "SUPPORTED"
      || value.label === "CONTRADICTED"
      || value.label === "UNSUPPORTED"
      || value.label === "NEEDS_REVIEW"
      || value.label === "UNSUPPORTED_PATIENT_CLAIM")
    && Array.isArray(value.evidence)
    && value.evidence.every(isEvidence)
    && typeof value.reason === "string";
}

function isCondition(value: unknown): value is Condition {
  return isRecord(value)
    && typeof value.condition === "string"
    && typeof value.output === "string"
    && Array.isArray(value.claims)
    && value.claims.every(isClaim)
    && Array.isArray(value.verifications)
    && value.verifications.every(isVerification)
    && Array.isArray(value.evidence)
    && value.evidence.every(isEvidence)
    && typeof value.latency_ms === "number"
    && typeof value.mode === "string"
    && (value.first_pass_output === undefined || value.first_pass_output === null || typeof value.first_pass_output === "string")
    && typeof value.correction_applied === "boolean"
    && (value.correction_note === undefined || value.correction_note === null || typeof value.correction_note === "string");
}

function isCompareResponse(value: unknown): value is CompareResponse {
  return isRecord(value)
    && typeof value.report === "string"
    && Array.isArray(value.findings)
    && value.findings.every((finding) => isRecord(finding)
      && typeof finding.text === "string"
      && typeof finding.polarity === "string")
    && typeof value.mode === "string"
    && isCondition(value.b1)
    && value.b1.condition === "B1"
    && isCondition(value.b2)
    && value.b2.condition === "B2"
    && isCondition(value.b3)
    && value.b3.condition === "B3";
}

export function normalizeAnalysisResponse(payload: CompareResponse): NormalizedAnalysisResponse {
  const structured = payload.structured_report;
  const structuredResults = structured?.results ?? [];
  const availableResults = structuredResults.filter((item) =>
    item.status === "reported" && item.value !== undefined && item.value !== null && item.value !== "");
  const pendingResults = structuredResults.filter((item) =>
    ["pending", "not_available", "awaited"].includes(item.status.toLowerCase()));
  const warnings = [payload.b1, payload.b2, payload.b3]
    .map((condition) => condition.correction_note)
    .filter((note): note is string => Boolean(note?.trim()));

  return {
    raw: payload,
    report: payload.report,
    structuredResults,
    availableResults,
    pendingResults,
    generalInformation: structured?.general_information ?? [],
    retrievedEvidence: payload.b3.evidence ?? [],
    claims: payload.b3.claims ?? [],
    verifications: payload.b3.verifications ?? [],
    warnings,
  };
}

async function responseDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (!isRecord(body)) return null;
    if (typeof body.detail === "string") return body.detail;
    return null;
  } catch {
    return null;
  }
}

export async function compare(report: string, top_k = 3): Promise<CompareResponse> {
  const url = compareUrl();
  const requestBody = { report, top_k };
  devLog("analysis request started", {
    url,
    method: "POST",
    body: { reportLength: report.length, top_k },
  });

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    });
  } catch (error) {
    console.warn("COMPARE ERROR", {
      url,
      reason: "The frontend could not reach the API proxy.",
      error,
    });
    throw new BackendConnectionError();
  }

  if (response.status >= 400 && response.status < 500) {
    console.warn("COMPARE ERROR", { url, status: response.status, statusText: response.statusText });
    if (response.status === 400 || response.status === 422) {
      throw new InvalidRequestError((await responseDetail(response)) || "The report or retrieval depth was rejected. Check the input and try again.");
    }
    throw new ComparisonError((await responseDetail(response)) || `The comparison request was rejected (HTTP ${response.status}).`, "backend");
  }

  if (!response.ok) {
    console.warn("COMPARE ERROR", { url, status: response.status, statusText: response.statusText });
    throw new ComparisonError((await responseDetail(response)) || "The comparison service encountered an error. Please retry.", "backend");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    console.warn("COMPARE ERROR", { url, status: response.status, reason: "Response was not valid JSON.", error });
    throw new UnexpectedResponseError();
  }

  if (!isCompareResponse(payload)) {
    console.warn("COMPARE ERROR", {
      url,
      status: response.status,
      reason: "Response JSON did not match the CompareResponse schema.",
      responseKeys: isRecord(payload) ? Object.keys(payload) : [],
    });
    throw new UnexpectedResponseError();
  }

  const normalized = normalizeAnalysisResponse(payload);
  devLog("analysis response received", {
    url,
    status: response.status,
    structuredResults: normalized.structuredResults.length,
    availableResults: normalized.availableResults.length,
    pendingResults: normalized.pendingResults.length,
    retrievalCount: normalized.retrievedEvidence.length,
    verificationCount: normalized.verifications.length,
    conditions: [payload.b1.condition, payload.b2.condition, payload.b3.condition],
    modes: [payload.b1.mode, payload.b2.mode, payload.b3.mode],
  });
  return payload;
}

export async function uploadReport(file: File): Promise<UploadedReport> {
  const url = `${apiBaseUrl()}/report/upload`;
  const formData = new FormData();
  formData.set("file", file);
  devLog("upload started", { url, size: file.size, type: file.type || "unknown" });

  let response: Response;
  try {
    response = await fetch(url, { method: "POST", body: formData });
  } catch (error) {
    console.warn("REPORT UPLOAD ERROR", { url, reason: "The API proxy could not be reached.", error });
    throw new BackendConnectionError();
  }

  if (!response.ok) {
    const detail = await responseDetail(response);
    console.warn("REPORT UPLOAD ERROR", { url, status: response.status, detail });
    throw new ComparisonError(detail || "Unable to process the report. Check the file and try again.", "backend");
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    console.warn("REPORT UPLOAD ERROR", { url, reason: "Response was not valid JSON.", error });
    throw new UnexpectedResponseError();
  }

  if (!isRecord(payload)
    || typeof payload.report_id !== "string"
    || typeof payload.filename !== "string"
    || typeof payload.source_type !== "string"
    || typeof payload.file_size_bytes !== "number"
    || typeof payload.extracted_text !== "string"
    || (payload.page_count !== undefined
      && payload.page_count !== null
      && typeof payload.page_count !== "number")
    || typeof payload.status !== "string") {
    console.warn("REPORT UPLOAD ERROR", { url, reason: "Response did not match upload schema." });
    throw new UnexpectedResponseError();
  }
  const uploaded = {
    report_id: payload.report_id,
    filename: payload.filename,
    source_type: payload.source_type,
    file_size_bytes: payload.file_size_bytes,
    extracted_text: payload.extracted_text,
    page_count: typeof payload.page_count === "number" ? payload.page_count : null,
    status: payload.status,
  };
  devLog("upload completed", {
    filename: uploaded.filename,
    sourceType: uploaded.source_type,
    characters: uploaded.extracted_text.length,
    pageCount: uploaded.page_count,
  });
  return uploaded;
}

export async function getServiceMode(): Promise<"demo" | "research"> {
  const url = `${apiBaseUrl()}/health`;
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`Health check failed with HTTP ${response.status}.`);
  const payload: unknown = await response.json();
  if (!isRecord(payload) || (payload.mode !== "demo" && payload.mode !== "research")) {
    throw new Error("Health response did not include a recognized service mode.");
  }
  return payload.mode;
}
