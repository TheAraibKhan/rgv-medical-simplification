"use client";

import { useEffect, useRef, useState } from "react";
import { AnalysisProcessing } from "@/components/AnalysisProcessing";
import { ComparisonResults } from "@/components/ComparisonResults";
import { MedicalIcon } from "@/components/MedicalIcon";
import { ReportWorkspace } from "@/components/ReportWorkspace";
import { compare, getServiceMode, InvalidRequestError, normalizeAnalysisResponse, uploadReport as uploadDocument, type CompareResponse, type UploadedReport } from "@/lib/api";

const landingNavLinks = [
  { label: "How it works", href: "#how-it-works" },
  { label: "About", href: "#about" },
];

const workflowSteps = ["Upload", "Extract", "Structure", "Reference", "Review"];
const reportTypes = ["Radiology reports", "Blood reports", "Lab reports", "Discharge summaries", "Clinical notes"];
type AnalysisState = "IDLE" | "UPLOADING" | "EXTRACTING" | "RETRIEVING" | "GENERATING" | "VERIFYING" | "COMPLETE" | "PARTIAL_SUCCESS" | "ERROR";

export default function Home() {
  const [report, setReport] = useState("");
  const [topK, setTopK] = useState(3);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [uploadedReport, setUploadedReport] = useState<UploadedReport | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(false);
  const [analysisState, setAnalysisState] = useState<AnalysisState>("IDLE");
  const [processingStep, setProcessingStep] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  const [serviceMode, setServiceMode] = useState("demo");
  const uploadInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void getServiceMode()
      .then(setServiceMode)
      .catch((healthError: unknown) => console.warn("API HEALTH CHECK", healthError));
  }, []);

  useEffect(() => {
    if (!result) return;

    window.history.replaceState(window.history.state, "", "#results");
    const frame = window.requestAnimationFrame(() => {
      document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [result]);

  async function runComparison() {
    if (report.trim().length < 5) {
      const validationError = new InvalidRequestError();
      console.warn("COMPARE ERROR", { reason: validationError.message, reportLength: report.length });
      setResult(null);
      setError(validationError);
      return;
    }

    setAnalysisState("EXTRACTING");
    setLoading(true);
    setError(null);
    let stopProgress = false;
    const progressTask = (async () => {
      for (let step = 0; step < 6; step += 1) {
        if (stopProgress) return;
        setProcessingStep(step);
        setAnalysisState(step < 2 ? "EXTRACTING" : step < 3 ? "RETRIEVING" : step < 5 ? "GENERATING" : "VERIFYING");
        await new Promise((resolve) => setTimeout(resolve, 620));
      }
    })();
    try {
      const response = await compare(report, topK);
      await progressTask;
      const normalized = normalizeAnalysisResponse(response);
      setResult(response);
      setServiceMode(response.mode);
      setAnalysisState(normalized.warnings.length > 0 ? "PARTIAL_SUCCESS" : "COMPLETE");
    } catch (e) {
      stopProgress = true;
      const requestError = e instanceof Error ? e : new Error("The comparison could not be completed.");
      console.warn("COMPARE ERROR", requestError.message);
      setError(requestError);
      setAnalysisState(result ? "PARTIAL_SUCCESS" : "ERROR");
    } finally {
      stopProgress = true;
      setLoading(false);
    }
  }

  function updateReport(value: string) {
    setReport(value);
    setResult(null);
    setUploadedReport(null);
    setError(null);
    setAnalysisState("IDLE");
  }

  function updateTopK(value: number) {
    setTopK(value);
  }

  async function processFile(file: File) {
    setPendingFile(file);
    setAnalysisState("UPLOADING");
    setUploading(true);
    setUploadError(null);
    setError(null);
    setResult(null);
    try {
      const uploaded = await uploadDocument(file);
      setUploadedReport(uploaded);
      setReport(uploaded.extracted_text);
      setPendingFile(null);
      setAnalysisState("IDLE");
    } catch (uploadFailure) {
      const requestError = uploadFailure instanceof Error
        ? uploadFailure
        : new Error("Unable to process report. Check the file and retry.");
      console.warn("REPORT UPLOAD ERROR", {
        name: requestError.name,
        message: requestError.message,
      });
      setUploadError(requestError);
      setAnalysisState("ERROR");
    } finally {
      setUploading(false);
      if (uploadInput.current) uploadInput.current.value = "";
    }
  }

  function removeUploadedReport() {
    setUploadedReport(null);
    setPendingFile(null);
    setReport("");
    setResult(null);
    setUploadError(null);
    setError(null);
    setAnalysisState("IDLE");
  }

  if (loading) {
    return <AnalysisProcessing activeStep={processingStep} />;
  }

  const showingResults = result !== null;
  const navLinks = showingResults
    ? [{ label: "Your report", href: "#results" }, { label: "About", href: "#about" }]
    : landingNavLinks;

  return (
    <main className="site-shell">
      <input
        ref={uploadInput}
        className="visually-hidden-input"
        type="file"
        accept=".pdf,.txt,.docx,.png,.jpg,.jpeg"
        aria-label="Upload a medical report"
        onChange={(event) => {
          const [file] = Array.from(event.currentTarget.files ?? []);
          if (file) void processFile(file);
        }}
      />
      <header className="topbar">
        <a className="brand" href="#home" aria-label="RGV Medical Simplification home">
          <span className="brand-symbol medlens-mark"><span /><i /></span>
          <span className="brand-name"><strong>RGV</strong><small>Medical Simplification</small></span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          {navLinks.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}
        </nav>
      </header>

      <div className="page-frame" id="home">
        {showingResults ? (
          <ComparisonResults
            result={result}
            analysisState={analysisState}
            analysisError={error}
            filename={uploadedReport?.filename ?? null}
            pageCount={uploadedReport?.page_count ?? null}
            documentType={uploadedReport?.source_type ?? "Pasted text"}
            onStartOver={removeUploadedReport}
            topK={topK}
            onTopKChange={updateTopK}
            onRerun={runComparison}
          />
        ) : (
          <>
            <section className="hero-layout" aria-labelledby="hero-heading">
              <div className="hero-message">
                <h1 id="hero-heading">Your medical report,<br /><span>made readable.</span></h1>
                <p className="hero-summary">RGV turns lab reports, scans and clinical notes into a structured view with the original wording kept beside every result.</p>
              </div>
              <div className="medlens-hero-visual" aria-hidden="true">
                <div className="floating-report-card report-card-primary">
                  <div className="floating-report-top"><span />LAB REPORT</div>
                  <div className="floating-report-row strong"><b>ApoB</b><i>46.00</i></div>
                  <div className="floating-report-row"><b>hsCRP</b><i>1.00</i></div>
                  <div className="floating-report-row"><b>Troponin-I</b><i>4</i></div>
                </div>
                <div className="floating-report-card report-card-secondary">
                  <MedicalIcon name="shield" size={28} />
                  <strong>Source checked</strong>
                  <span>Page and row provenance</span>
                </div>
                <div className="lens-orbit"><span /><span /><span /></div>
                <div className="glass-lens"><MedicalIcon name="search" size={42} /></div>
                <div className="result-chip chip-one">Result</div>
                <div className="result-chip chip-two">Reference</div>
                <div className="result-chip chip-three">Pending</div>
              </div>
            </section>

            <ReportWorkspace
              report={report}
              uploadedReport={uploadedReport}
              mode={serviceMode}
              loading={loading}
              uploading={uploading}
              uploadError={uploadError}
              error={error}
              onRetry={runComparison}
              onRetryUpload={() => pendingFile ? processFile(pendingFile) : Promise.resolve()}
              onReportChange={updateReport}
              onRun={runComparison}
              onRequestUpload={() => uploadInput.current?.click()}
              onFileUpload={processFile}
              onRemoveUpload={removeUploadedReport}
            />

            <div className="trust-pills" aria-label="Privacy and supported formats">
              <span><MedicalIcon name="lock" size={15} />Private by design</span>
              <span><MedicalIcon name="check" size={15} />{serviceMode === "demo" ? "Sample-safe mode" : "Local review mode"}</span>
              <span>PDF · TXT · DOCX</span>
              <span>PNG/JPG with local OCR</span>
            </div>
            <p className="landing-privacy-note">
              {serviceMode === "demo" ? "Sample-safe mode - use synthetic/open reports only. " : "Local review mode - local processing only. "}
              Do not upload sensitive patient information.
            </p>

            <section className="supported-section" aria-labelledby="supported-heading">
              <span className="section-label">REPORTS RGV CAN HELP READ</span>
              <h2 id="supported-heading">Works with common medical documents</h2>
              <div className="report-type-list">
                {reportTypes.map((type) => <span key={type}>{type}</span>)}
              </div>
              <p>Text-based PDF, TXT and DOCX files can be read. PNG/JPG text extraction requires locally installed OCR.</p>
            </section>

            <section className="process-section" id="how-it-works" aria-labelledby="process-heading">
              <div className="process-heading"><span className="section-label">A SIMPLE, CAREFUL PROCESS</span><h2 id="process-heading">From report to readable results</h2></div>
              <ol className="process-steps">
                {workflowSteps.map((step, index) => (
                  <li key={step}><span>{String(index + 1).padStart(2, "0")}</span><strong>{step}</strong></li>
                ))}
              </ol>
            </section>

            <section className="audience-intro" aria-label="Report explanation and evidence views">
              <div><span className="section-label">ONE REPORT · TWO VIEWS</span><h2>Clear for patients. <span>Transparent for clinicians.</span></h2></div>
              <p>Every explanation keeps the original report in view. Clinicians can inspect the evidence and verification behind it.</p>
            </section>
          </>
        )}

        <footer className="site-footer">
          <div className="footer-main">
            <a className="brand" href="#home"><span className="brand-symbol medlens-mark"><span /><i /></span><span className="brand-name"><strong>RGV</strong><small>Medical Simplification</small></span></a>
            <p id="about">Clear, source-grounded explanations for medical reports. Review tool, not a diagnostic system.</p>
          </div>
          {!showingResults && <div className="footer-nav"><a href="#how-it-works">How it works</a><a href="#try-it">Upload a report</a></div>}
          <div className="footer-legal"><span>Research prototype · {serviceMode.toUpperCase()} mode</span><span>Not a diagnostic system. Do not upload sensitive patient information.</span></div>
        </footer>
      </div>
    </main>
  );
}
