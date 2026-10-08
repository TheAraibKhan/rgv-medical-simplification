"use client";

import { useState, type DragEvent, type KeyboardEvent } from "react";
import type { FormEvent } from "react";
import { MedicalIcon } from "@/components/MedicalIcon";
import { ComparisonError, type UploadedReport } from "@/lib/api";

export function ReportWorkspace({
  report,
  uploadedReport,
  mode,
  loading,
  uploading,
  uploadError,
  error,
  onRetry,
  onRetryUpload,
  onReportChange,
  onRun,
  onRequestUpload,
  onFileUpload,
  onRemoveUpload,
}: {
  report: string;
  uploadedReport: UploadedReport | null;
  mode: string;
  loading: boolean;
  uploading: boolean;
  uploadError: Error | null;
  error: Error | null;
  onRetry: () => Promise<void>;
  onRetryUpload: () => Promise<void>;
  onReportChange: (value: string) => void;
  onRun: () => Promise<void>;
  onRequestUpload: () => void;
  onFileUpload: (file: File) => Promise<void>;
  onRemoveUpload: () => void;
}) {
  const [pasteMode, setPasteMode] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onRun();
  }

  function dropFile(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const [file] = Array.from(event.dataTransfer.files);
    if (file) void onFileUpload(file);
  }

  function activateDropzone(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRequestUpload();
    }
  }

  const errorCategory = error instanceof ComparisonError ? error.category : "backend";
  const errorTitle = {
    connection: "Backend connection unavailable",
    "invalid-request": "Invalid comparison request",
    backend: "Analysis unavailable",
    response: "Unexpected backend response",
  }[errorCategory];
  const uploadSize = uploadedReport ? `${(uploadedReport.file_size_bytes / 1024).toFixed(1)} KB` : "";

  return (
    <section className="workspace-section section-block" id="try-it">
      <form className="document-workspace" onSubmit={submit}>
        {!uploadedReport && !report && (
          <div
            className={`upload-dropzone${uploading ? " upload-dropzone-busy" : ""}`}
            role="button"
            tabIndex={0}
            aria-label="Choose a medical report to upload"
            aria-busy={uploading}
            onClick={onRequestUpload}
            onKeyDown={activateDropzone}
            onDragOver={(event) => event.preventDefault()}
            onDrop={dropFile}
          >
            <span className="upload-icon"><MedicalIcon name="report" size={26} /></span>
            <strong>{uploading ? "Reading your report…" : "Drop your report here"}</strong>
            <p>PDF · TXT · DOCX · Images</p>
            <span className="browse-report">{uploading ? "Preparing report…" : "Choose File"}</span>
            <small>Up to 20 MB · PNG/JPG text extraction requires local OCR</small>
          </div>
        )}

        {uploadedReport && (
          <div className="uploaded-file-preview">
            <span className="uploaded-file-check" aria-hidden="true">✓</span>
            <div><strong>Report ready</strong><small>{uploadedReport.filename} · {uploadedReport.source_type} · {uploadSize}</small></div>
            <button type="button" onClick={onRemoveUpload} disabled={loading || uploading}>Remove</button>
          </div>
        )}

        {uploading && (
          <div className="upload-progress" role="status" aria-live="polite">
            <span className="progress-spinner" />
            <div><strong>Extracting report text locally…</strong><small>Your file is processed in memory.</small></div>
          </div>
        )}

        {uploadError && (
          <div className="workspace-error" role="alert">
            <span className="workspace-error-icon"><MedicalIcon name="warning" size={17} /></span>
            <div><strong>We couldn’t read that report</strong><p>{uploadError.message}</p></div>
            <button type="button" onClick={() => void onRetryUpload()} disabled={uploading}>Try again</button>
          </div>
        )}

        {!uploadedReport && !report && (
          <div className="paste-option">
            <span>or paste report text</span>
            <button type="button" onClick={() => {
              setPasteMode(true);
              window.requestAnimationFrame(() => document.getElementById("medical-report")?.focus());
            }}>Paste Report</button>
          </div>
        )}

        {(uploadedReport || pasteMode || report) && (
          <>
            <div className="document-sheet">
              <div className="document-meta"><span>SOURCE REPORT</span><span>{uploadedReport ? "VERBATIM · EXTRACTED TEXT" : "PASTE REPORT TEXT"}</span></div>
              <label className="sr-only" htmlFor="medical-report">Source medical report text</label>
              <textarea
                id="medical-report"
                value={report}
                onChange={(event) => onReportChange(event.target.value)}
                placeholder="Paste your report text here…"
                spellCheck
                readOnly={Boolean(uploadedReport)}
                aria-label={uploadedReport ? "Verbatim extracted source report" : "Source medical report"}
              />
              <div className="document-sheet-footer"><span><MedicalIcon name="lock" size={13} /> Original report wording is preserved</span><span>{report.length} characters</span></div>
            </div>

            <p className="privacy-notice">
              {mode === "demo" ? "Demo mode — use synthetic/open medical reports only. " : "Research mode — local processing only. "}
              <strong>Do not upload sensitive patient information.</strong>
            </p>
            <button className="compare-button" type="submit" disabled={loading || uploading || report.trim().length < 5}>
              <MedicalIcon name="spark" size={17} />{error ? "Try analysis again" : "Analyze Report"}<MedicalIcon name="arrow" size={16} />
            </button>
          </>
        )}

        {error && (
          <div className={`workspace-error${errorCategory === "connection" ? " backend-unavailable" : ""}`} role="alert">
            <span className="workspace-error-icon"><MedicalIcon name={errorCategory === "connection" ? "info" : "warning"} size={17} /></span>
            <div>
              <strong>{errorTitle}</strong>
              <p>{errorCategory === "connection"
                ? "The local analysis service is unavailable. Please try again shortly."
                : error.message}</p>
            </div>
            <button type="button" onClick={() => void onRetry()} disabled={loading}>Try again</button>
          </div>
        )}
      </form>
    </section>
  );
}
