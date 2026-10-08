"use client";

import { useMemo, useState } from "react";
import { ConditionCard } from "@/components/ConditionCard";
import type {
  Claim,
  CompareResponse,
  Evidence,
  ExcludedReportItem,
  ReportReference,
  StructuredFinding,
  StructuredTestResult,
} from "@/lib/api";

type AudienceView = "clinician" | "patient";
type ResultStatus = "Available" | "Pending" | "Needs review";

type NormalizedResult = {
  item: StructuredTestResult;
  status: ResultStatus;
  displayValue: string;
};

function displaySection(section: string): string {
  return section.toLowerCase().replaceAll("_", " ");
}

function normalizedResults(results: StructuredTestResult[]): NormalizedResult[] {
  const seen = new Set<string>();
  const rows = results
    .slice()
    .sort((left, right) => left.source_span.start - right.source_span.start)
    .flatMap((item) => {
      const name = item.test_name.replace(/\s+/g, " ").trim();
      const value = item.value?.replace(/\s+/g, " ").trim() || "";
      const unit = item.unit?.replace(/\s+/g, " ").trim() || "";
      const reference = item.reference_interval?.replace(/\s+/g, " ").trim() || "";
      const signature = [name.toLowerCase(), value.toLowerCase(), unit.toLowerCase(), reference.toLowerCase(), item.status.toLowerCase()].join("|");
      if (seen.has(signature)) return [];
      seen.add(signature);
      return [{ item: { ...item, test_name: name, value, unit, reference_interval: reference } }];
    });

  const counts = new Map<string, number>();
  for (const row of rows) {
    const key = row.item.test_name.toLowerCase();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return rows.map(({ item }) => {
    const pending = ["pending", "not_available", "awaited"].includes(item.status.toLowerCase());
    const numericValue = item.value && /^[<>≤≥]?\s*\d+(?:[.,]\d+)?$/.test(item.value);
    const repeatedOcrDigits = /\b(\d+)(?:\s+\1){2,}\b/.test(item.source_text);
    const conflictingRows = (counts.get(item.test_name.toLowerCase()) ?? 0) > 1;
    const status: ResultStatus = pending
      ? "Pending"
      : numericValue && !repeatedOcrDigits && !conflictingRows
        ? "Available"
        : "Needs review";

    return { item, status, displayValue: status === "Available" ? item.value ?? "—" : "—" };
  });
}

function referenceText(item: StructuredTestResult): string {
  let reference = item.reference_interval?.replace(/\s+/g, " ").trim();
  if (!reference) return "—";
  if (item.unit) {
    const unitPattern = new RegExp(`\\s*${item.unit.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*$`, "i");
    reference = reference.replace(unitPattern, "");
  }
  return reference.replace(/\s*-\s*/g, "–");
}

function SourcePanel({ item }: { item: StructuredTestResult }) {
  const page = item.source_page ?? item.source_span.page;
  return (
    <details className="result-source-details">
      <summary>View source</summary>
      <div className="result-source-panel">
        <dl>
          <div><dt>Page</dt><dd>{page ? page : "Not mapped during extraction"}</dd></div>
          <div><dt>Section</dt><dd>{displaySection(item.section)}</dd></div>
          <div><dt>Source span</dt><dd>Characters {item.source_span.start}–{item.source_span.end}</dd></div>
        </dl>
        <strong>Original source wording</strong>
        <blockquote>{item.source_text || "No source wording was retained for this item."}</blockquote>
      </div>
    </details>
  );
}

function ResultsTable({ rows }: { rows: NormalizedResult[] }) {
  if (rows.length === 0) {
    return <p className="clinical-empty-note">No structured test results were identified in this report.</p>;
  }

  return (
    <div className="results-table-scroll">
      <table className="clinical-results-table">
        <thead>
          <tr>
            <th scope="col">Test</th>
            <th scope="col">Short name</th>
            <th scope="col">Result</th>
            <th scope="col">Unit</th>
            <th scope="col">Reference interval</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ item, status, displayValue }, index) => {
            const shortName = item.abbreviation
              || (item.short_name && item.short_name.toLowerCase() !== item.test_name.toLowerCase()
                ? item.short_name
                : null);
            return (
              <tr key={`${item.source_span.start}-${index}`}>
                <th scope="row">
                  <span className="result-test-name">{item.test_name}</span>
                  <SourcePanel item={item} />
                </th>
                <td>{shortName || "—"}</td>
                <td className="result-value">{displayValue}</td>
                <td>{item.unit || "—"}</td>
                <td>{referenceText(item)}</td>
                <td><span className={`result-status status-${status.toLowerCase().replaceAll(" ", "-")}`}>{status}</span></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function sourceFindings(result: CompareResponse): string[] {
  return result.findings.map((finding) => finding.text);
}

function evidenceIsFromReport(evidence: Evidence[]): boolean {
  return evidence.some((item) => item.source.toLowerCase() === "source report");
}

function claimStatus(claim: Claim, result: CompareResponse): string {
  const verification = result.b3.verifications.find((item) => item.claim_id === claim.claim_id);
  if (!verification) return "Not checked";
  if (claim.claim_type === "PATIENT_SPECIFIC") {
    if (verification.label === "SUPPORTED" && evidenceIsFromReport(verification.evidence)) return "Supported by source";
    if (verification.label === "NEEDS_REVIEW") return "Needs review";
    return "Unsupported patient-specific claim";
  }
  return verification.label === "SUPPORTED" && verification.evidence.length > 0
    ? "Supported general explanation"
    : "Needs review";
}

function VerificationLedger({ result }: { result: CompareResponse }) {
  if (result.b3.claims.length === 0) {
    return <p className="clinical-empty-note">No claims were returned for verification in B3.</p>;
  }

  return (
    <div className="verification-ledger">
      {result.b3.claims.map((claim) => {
        const verification = result.b3.verifications.find((item) => item.claim_id === claim.claim_id);
        return (
          <article className="ledger-row" key={claim.claim_id}>
            <span className="ledger-status">{claimStatus(claim, result)}</span>
            <div className="ledger-claim">
              <strong>Original claim</strong>
              <p>{verification?.original_claim || claim.text}</p>
              <small>{claim.claim_type === "PATIENT_SPECIFIC" ? "Patient-specific claim" : "General explanatory claim"}</small>
              {verification?.changed && <>
                <strong>Final claim</strong>
                <p>{verification.final_claim || "Withheld from the final explanation."}</p>
              </>}
            </div>
            <div className="ledger-evidence">
              {verification ? <>
                <strong>{verification.label.replaceAll("_", " ")}</strong>
                <p>{verification.reason}</p>
                {verification.evidence.map((item, index) => (
                  <blockquote key={`${item.document_id ?? item.source}-${index}`}>
                    <strong>{item.source}{item.title ? ` · ${item.title}` : ""}</strong>
                    <span>{item.text}</span>
                  </blockquote>
                ))}
              </> : <strong>Not checked in this condition</strong>}
            </div>
          </article>
        );
      })}
    </div>
  );
}

function RetrievedEvidence({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) {
    return <p className="clinical-empty-note">No retrieved evidence was returned for this report.</p>;
  }
  return (
    <div className="retrieved-evidence-list">
      {evidence.map((item, index) => (
        <article className="retrieved-evidence-item" key={item.document_id ?? `${item.source}-${index}`}>
          <div className="retrieved-evidence-topline"><span>{item.source}</span><span>General medical information</span></div>
          <h4>{item.url
            ? <a href={item.url} target="_blank" rel="noreferrer">{item.title || item.source}</a>
            : item.title || item.source}</h4>
          <details>
            <summary>Read the retrieved explanation</summary>
            <p>{item.text}</p>
            {item.url && <a className="evidence-source-link" href={item.url} target="_blank" rel="noreferrer">Open source ↗</a>}
          </details>
        </article>
      ))}
    </div>
  );
}

function itemSearchTerms(item: StructuredTestResult): string[] {
  return [item.test_name, item.short_name, item.abbreviation]
    .filter((term): term is string => Boolean(term?.trim()))
    .map((term) => term.toLowerCase());
}

function matchesTest(text: string, terms: string[]): boolean {
  const normalized = text.toLowerCase();
  return terms.some((term) => normalized.includes(term));
}

function matchesContext(text: string, concept: string): boolean {
  return text.toLowerCase().includes(concept.toLowerCase());
}

function hasRepeatedOcrToken(text: string): boolean {
  return /\b([\p{L}\p{N}]+)(?:\s+\1){2,}\b/iu.test(text);
}

function TestExplanations({
  rows,
  claims,
  evidence,
}: {
  rows: NormalizedResult[];
  claims: Claim[];
  evidence: Evidence[];
}) {
  if (rows.length === 0) return <p className="clinical-empty-note">No test-specific explanations can be linked without structured test results.</p>;

  return (
    <div className="test-explanation-list">
      {rows.map(({ item }, index) => {
        const terms = itemSearchTerms(item);
        const explanations = claims.filter((claim) =>
          claim.claim_type === "GENERAL_EXPLANATORY" && matchesTest(claim.text, terms));
        const relatedEvidence = evidence.filter((source) =>
          matchesTest(`${source.title} ${source.text}`, terms));
        return (
          <article className="test-explanation" key={`${item.source_span.start}-${index}`}>
            <div><strong>{item.abbreviation || item.short_name || item.test_name}</strong><span>{item.test_name}</span></div>
            {explanations.length > 0
              ? explanations.map((claim) => <p key={claim.claim_id}>{claim.text}</p>)
              : relatedEvidence.length > 0
                ? relatedEvidence.map((source, evidenceIndex) => (
                  <p key={`${source.document_id ?? source.title}-${evidenceIndex}`}>{source.text}</p>
                ))
                : <p>No test-specific explanation was retrieved for this result.</p>}
            {relatedEvidence.map((source, evidenceIndex) => source.url && (
              <a key={`${source.document_id ?? source.title}-link-${evidenceIndex}`} href={source.url} target="_blank" rel="noreferrer">
                General information source ↗
              </a>
            ))}
          </article>
        );
      })}
    </div>
  );
}

type RouteEntry = {
  status: "USED" | "CONTEXT ONLY" | "EXCLUDED";
  title: string;
  reason: string;
  source: string;
  section: string;
  span: string;
};

function routingEntries(result: CompareResponse): RouteEntry[] {
  const structured = result.structured_report;
  if (!structured) return [];
  const entries: RouteEntry[] = [
    ...structured.results.map((item) => ({
      status: "USED" as const,
      title: item.short_name || item.test_name,
      reason: "Patient-specific test result",
      source: item.source_text,
      section: displaySection(item.section),
      span: `Characters ${item.source_span.start}–${item.source_span.end}`,
    })),
    ...structured.findings.map((item) => ({
      status: "USED" as const,
      title: item.concept,
      reason: "Patient-specific finding",
      source: item.source_text,
      section: displaySection(item.section),
      span: `Characters ${item.source_span.start}–${item.source_span.end}`,
    })),
    ...structured.general_information.map((item) => ({
      status: "CONTEXT ONLY" as const,
      title: item.concept,
      reason: "Laboratory commentary or general interpretation",
      source: item.source_text,
      section: displaySection(item.section),
      span: `Characters ${item.source_span.start}–${item.source_span.end}`,
    })),
    ...structured.excluded_items.map((item: ExcludedReportItem) => ({
      status: "EXCLUDED" as const,
      title: item.section === "ADMINISTRATIVE" ? "Administrative information" : displaySection(item.section),
      reason: displaySection(item.reason),
      source: item.source_text,
      section: displaySection(item.section),
      span: `Characters ${item.source_span.start}–${item.source_span.end}`,
    })),
    ...structured.references.map((item: ReportReference) => ({
      status: "EXCLUDED" as const,
      title: item.title || "Report reference",
      reason: "Reference / administrative information",
      source: item.citation_text,
      section: displaySection(item.source_section),
      span: `Characters ${item.source_span.start}–${item.source_span.end}`,
    })),
  ];

  const seen = new Set<string>();
  return entries.filter((entry) => {
    const key = `${entry.status}|${entry.section}|${entry.span}|${entry.source}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function DocumentUnderstanding({
  rows,
  contextualSectionCount,
  pageCount,
}: {
  rows: NormalizedResult[];
  contextualSectionCount: number;
  pageCount: number | null;
}) {
  const availableCount = rows.filter((row) => row.status === "Available").length;
  const pendingCount = rows.filter((row) => row.status === "Pending").length;
  const reviewCount = rows.filter((row) => row.status === "Needs review").length;
  const qualityItems = [
    { label: pageCount === null ? "Page count unavailable from source" : `${pageCount} ${pageCount === 1 ? "page" : "pages"} processed`, done: pageCount !== null },
    { label: `${rows.length} test ${rows.length === 1 ? "field" : "fields"} detected`, done: rows.length > 0 },
    { label: `${availableCount} numeric ${availableCount === 1 ? "result" : "results"} extracted`, done: availableCount > 0 },
    { label: `${pendingCount} pending ${pendingCount === 1 ? "result" : "results"} identified`, done: pendingCount > 0 },
    { label: `${contextualSectionCount} contextual ${contextualSectionCount === 1 ? "section" : "sections"} detected`, done: contextualSectionCount > 0 },
  ];
  return (
    <section className="document-understanding" aria-label="Document understanding">
      <h3>Document understanding</h3>
      <ul>{qualityItems.map((item) => (
        <li key={item.label} className={item.done ? "quality-done" : "quality-unavailable"}>
          <span aria-hidden="true">{item.done ? "✓" : "—"}</span>{item.label}
        </li>
      ))}</ul>
      {reviewCount > 0 && <p className="quality-warning">⚠ {reviewCount} field{reviewCount === 1 ? "" : "s"} need review. No value was inferred.</p>}
      <small>Extraction status only — not a medical confidence measure.</small>
    </section>
  );
}

function PatientView({
  result,
  rows,
}: {
  result: CompareResponse;
  rows: NormalizedResult[];
}) {
  const structured = result.structured_report;
  const contextual = structured?.general_information ?? [];
  const resultClaims = result.b3.claims.filter((claim) => claim.claim_type === "GENERAL_EXPLANATORY");

  return (
    <div className="patient-workspace">
      <section className="patient-results-card" aria-labelledby="patient-results-heading">
        <span className="patient-view-kicker">YOUR RESULTS</span>
        <h3 id="patient-results-heading">Results listed in your report</h3>
        <ResultsTable rows={rows} />
      </section>

      <section className="patient-context-card" aria-labelledby="patient-meaning-heading">
        <span className="patient-view-kicker">WHAT THESE TESTS MEAN</span>
        <h3 id="patient-meaning-heading">Plain-language explanations</h3>
        <TestExplanations rows={rows} claims={resultClaims} evidence={result.b3.evidence} />
      </section>

      <section className="patient-context-card" aria-labelledby="patient-general-heading">
        <span className="patient-view-kicker">GENERAL MEDICAL INFORMATION</span>
        <h3 id="patient-general-heading">Context from the report</h3>
        {contextual.length > 0 ? (
          <div className="general-information-list">
            {contextual.map((item, index) => (
              <article key={`${item.source_span.start}-${index}`}>
                <strong>{item.concept}</strong>
                <p>{hasRepeatedOcrToken(item.source_text)
                  ? "Needs review — repeated text was detected in this extracted section."
                  : item.source_text.replace(/\s+/g, " ").trim()}</p>
                <small>This wording is general context from the report, not a patient-specific result or diagnosis.</small>
                {result.b3.evidence
                  .filter((source) => matchesContext(`${source.title} ${source.text}`, item.concept))
                  .map((source, sourceIndex) => (
                    <div className="context-retrieved-explanation" key={`${source.document_id ?? source.title}-${sourceIndex}`}>
                      <span>Related general explanation · {source.title || source.source}</span>
                      <p>{source.text}</p>
                      {source.url && <a href={source.url} target="_blank" rel="noreferrer">View information source ↗</a>}
                    </div>
                  ))}
              </article>
            ))}
          </div>
        ) : <p className="clinical-empty-note">No separate contextual medical information was identified in this report.</p>}
      </section>

      <p className="patient-important"><strong>IMPORTANT</strong><span>Research prototype — not a diagnostic system.</span></p>
    </div>
  );
}

function ClinicianWorkflow({
  result,
  filename,
  pageCount,
  documentType,
  rows,
  topK,
  onTopKChange,
  onRerun,
  onShowOutput,
}: {
  result: CompareResponse;
  filename: string | null;
  pageCount: number | null;
  documentType: string;
  rows: NormalizedResult[];
  topK: number;
  onTopKChange: (value: number) => void;
  onRerun: () => Promise<void>;
  onShowOutput: () => void;
}) {
  const structured = result.structured_report;
  const contextSections = useMemo(() => {
    const contextTypes = new Set(["COMMENT", "INTERPRETATION", "GENERAL_INFORMATION", "RISK_GUIDANCE", "TREATMENT_GUIDANCE"]);
    return new Set((structured?.sections ?? [])
      .filter((section) => contextTypes.has(section.section))
      .map((section) => section.section)).size;
  }, [structured]);
  const routes = routingEntries(result);
  const usedCount = routes.filter((item) => item.status === "USED").length;
  const contextualCount = routes.filter((item) => item.status === "CONTEXT ONLY").length;
  const excludedCount = routes.filter((item) => item.status === "EXCLUDED").length;

  return (
    <div className="clinician-workspace">
      <DocumentUnderstanding rows={rows} contextualSectionCount={contextSections} pageCount={pageCount} />

      <ol className="clinical-workflow" aria-label="Clinical information workflow">
        {[
          "SOURCE REPORT",
          "STRUCTURED RESULTS",
          "CONTEXT CLASSIFICATION",
          "RETRIEVAL-ELIGIBLE CONCEPTS",
          "RETRIEVED EVIDENCE",
          "PLAIN-LANGUAGE EXPLANATION",
          "VERIFICATION",
          "OUTPUT",
        ].map((step, index) => <li key={step}><span>{String(index + 1).padStart(2, "0")}</span>{step}</li>)}
      </ol>

      <details className="workflow-stage" open>
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">01</span><span><small>SOURCE REPORT</small><strong>{filename || "Pasted report"}</strong></span><b>{documentType}{pageCount !== null ? ` · ${pageCount} PAGES` : ""}</b></summary>
        <div className="workflow-stage-content">
          <p className="workflow-report-meta">Original extracted wording is preserved for audit. Page-level row mapping is unavailable when it was not returned by extraction.</p>
          <blockquote className="source-report-text">{result.report}</blockquote>
        </div>
      </details>

      <details className="workflow-stage" open>
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">02</span><span><small>STRUCTURED RESULTS</small><strong>Extracted test fields</strong></span><b>{rows.length} FIELDS</b></summary>
        <div className="workflow-stage-content"><ResultsTable rows={rows} /></div>
      </details>

      <details className="workflow-stage">
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">03</span><span><small>CONTENT ROUTING</small><strong>Context classification ledger</strong></span><b>{usedCount} USED · {contextualCount} CONTEXT · {excludedCount} EXCLUDED</b></summary>
        <div className="workflow-stage-content">
          {routes.length > 0 ? (
            <div className="content-routing-ledger">
              {routes.map((entry, index) => (
                <article className={`routing-entry routing-${entry.status.toLowerCase().replaceAll(" ", "-")}`} key={`${entry.status}-${entry.span}-${index}`}>
                  <span className="routing-label">{entry.status}</span>
                  <div><strong>{entry.title}</strong><small>{entry.reason} · {entry.section} · {entry.span}</small><p>{entry.source}</p></div>
                </article>
              ))}
            </div>
          ) : <p className="clinical-empty-note">No classified content was returned by structured extraction.</p>}
          <small className="audit-note">Excluded source content remains in the original report and this audit ledger.</small>
        </div>
      </details>

      <details className="workflow-stage">
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">04</span><span><small>RETRIEVAL-ELIGIBLE CONCEPTS</small><strong>Concepts selected for retrieval</strong></span><b>{structured?.retrieval_queries.length ?? 0} CONCEPTS</b></summary>
        <div className="workflow-stage-content">
          {structured?.retrieval_queries.length
            ? <ul className="retrieval-concepts">{structured.retrieval_queries.map((query, index) => <li key={`${query}-${index}`}>{query}</li>)}
              </ul>
            : <p className="clinical-empty-note">No concepts were selected for retrieval from this report.</p>}
        </div>
      </details>

      <details className="workflow-stage">
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">05</span><span><small>RETRIEVED EVIDENCE</small><strong>General medical information sources</strong></span><b>{result.b3.evidence.length} SOURCES</b></summary>
        <div className="workflow-stage-content">
          <p className="workflow-boundary-note">Retrieved material can support general explanations; it does not establish patient-specific facts.</p>
          <RetrievedEvidence evidence={result.b3.evidence} />
        </div>
      </details>

      <details className="workflow-stage">
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">06</span><span><small>PLAIN-LANGUAGE EXPLANATION</small><strong>Patient-oriented explanation</strong></span><b>{result.b3.mode.toUpperCase()}</b></summary>
        <div className="workflow-stage-content"><p className="clinician-explanation">{result.b3.output}</p></div>
      </details>

      <details className="workflow-stage">
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">07</span><span><small>VERIFICATION</small><strong>Claim-level review</strong></span><b>{result.b3.verifications.length} CHECKS</b></summary>
        <div className="workflow-stage-content">
          <p className="verification-boundary">Patient-specific claims are checked against the source report. Retrieved material can support general explanations only.</p>
          <VerificationLedger result={result} />
        </div>
      </details>

      <details className="workflow-stage" open>
        <summary className="workflow-stage-heading"><span className="workflow-stage-index">08</span><span><small>OUTPUT</small><strong>Patient view</strong></span><b>STRUCTURED VIEW</b></summary>
        <div className="workflow-stage-content output-destination">
          <p>Structured results, term-linked explanations, and general report context are kept separate in the patient view.</p>
          <button type="button" onClick={onShowOutput}>View patient output</button>
        </div>
      </details>

      <details className="research-mode">
        <summary><span>RESEARCH MODE</span><strong>B1 / B2 / B3 method comparison</strong></summary>
        <div className="research-mode-content">
          <p>Same source report. Review source, retrieval, generation, and verification outputs for each research condition; no aggregate scores are shown.</p>
          <div className="research-method-labels">
            <span><b>B1</b> Direct prompting</span>
            <span><b>B2</b> Patient-oriented RAG</span>
            <span><b>B3</b> RAG + explicit verification</span>
          </div>
          <div className="clinician-research-controls">
            <div><strong>Retrieval depth</strong><small>Choose the number of sources and rerun this report.</small></div>
            <div className="depth-control" role="group" aria-label="Retrieved source count">
              {[1, 3, 5].map((value) => (
                <button className={topK === value ? "selected" : ""} type="button" key={value} aria-pressed={topK === value} onClick={() => onTopKChange(value)}>Top-{value}</button>
              ))}
            </div>
            <button className="clinician-rerun" type="button" onClick={() => void onRerun()}>Run comparison</button>
          </div>
          <div className="results-condition-grid">
            <ConditionCard item={result.b1} variant="b1" />
            <ConditionCard item={result.b2} variant="b2" />
            <ConditionCard item={result.b3} variant="b3" />
          </div>
        </div>
      </details>
    </div>
  );
}

export function ComparisonResults({
  result,
  filename = null,
  pageCount = null,
  documentType = "Pasted text",
  onStartOver,
  topK,
  onTopKChange,
  onRerun,
}: {
  result: CompareResponse | null;
  filename?: string | null;
  pageCount?: number | null;
  documentType?: string;
  onStartOver: () => void;
  topK: number;
  onTopKChange: (value: number) => void;
  onRerun: () => Promise<void>;
}) {
  const [view, setView] = useState<AudienceView>("patient");
  const rows = useMemo(
    () => normalizedResults(result?.structured_report?.results ?? []),
    [result?.structured_report?.results],
  );
  const contextualSections = useMemo(() => {
    const contextTypes = new Set(["COMMENT", "INTERPRETATION", "GENERAL_INFORMATION", "RISK_GUIDANCE", "TREATMENT_GUIDANCE"]);
    return new Set((result?.structured_report?.sections ?? [])
      .filter((section) => contextTypes.has(section.section))
      .map((section) => section.section)).size;
  }, [result?.structured_report?.sections]);
  if (!result) return null;

  const resultName = filename || "Pasted report";
  const availableCount = rows.filter((row) => row.status === "Available").length;
  const pendingCount = rows.filter((row) => row.status === "Pending").length;

  return (
    <section className="comparison-results section-block" id="results" aria-labelledby="results-heading">
      <div className="report-analysis-header">
        <div className="report-analysis-heading">
          <span className="analysis-ready"><i aria-hidden="true">✓</i> REPORT ANALYZED</span>
          <h2 id="results-heading">{resultName}</h2>
          <p>{documentType}{pageCount === null ? "" : ` · ${pageCount} ${pageCount === 1 ? "page" : "pages"}`}</p>
        </div>
        <button className="results-reset" type="button" onClick={onStartOver}>Analyze another report</button>
        <div className="extraction-summary" aria-label="Extraction statistics">
          <span><strong>{availableCount}</strong> results available</span>
          <span><strong>{pendingCount}</strong> results pending</span>
          <span><strong>{contextualSections}</strong> contextual {contextualSections === 1 ? "section" : "sections"}</span>
        </div>
      </div>

      <div className="results-view-choices" role="group" aria-label="Analysis view">
        <button type="button" className={view === "patient" ? "selected" : ""} aria-pressed={view === "patient"} onClick={() => setView("patient")}>Patient view</button>
        <button type="button" className={view === "clinician" ? "selected clinician-choice" : "clinician-choice"} aria-pressed={view === "clinician"} onClick={() => setView("clinician")}>Clinician view</button>
      </div>
      <div>
        {view === "clinician"
          ? <ClinicianWorkflow
            result={result}
            filename={filename}
            pageCount={pageCount}
            documentType={documentType}
            rows={rows}
            topK={topK}
            onTopKChange={onTopKChange}
            onRerun={onRerun}
            onShowOutput={() => setView("patient")}
          />
          : <PatientView result={result} rows={rows} />}
      </div>
    </section>
  );
}
