import { MedicalIcon } from "@/components/MedicalIcon";

const steps = [
  { title: "Reading your report", description: "Extracting text and findings" },
  { title: "Identifying clinical concepts", description: "Finding meaningful report findings" },
  { title: "Matching reference material", description: "Finding relevant patient-oriented knowledge" },
  { title: "Preparing explanation", description: "Writing patient-friendly language" },
  { title: "Checking the wording", description: "Comparing statements with the source report" },
  { title: "Preparing results", description: "Organizing both report views" },
];

export function AnalysisProcessing({ activeStep }: { activeStep: number }) {
  return (
    <main className="processing-screen" aria-labelledby="processing-title" aria-live="polite">
      <div className="processing-content">
        <a className="brand processing-brand" href="#home" aria-label="MedLens">
          <span className="brand-symbol medlens-mark"><span /><i /></span>
          <span className="brand-name"><strong>MedLens</strong><small>Clinical Report Clarity</small></span>
        </a>
        <div className="processing-document" aria-hidden="true">
          <span><MedicalIcon name="report" size={27} /></span>
        </div>
        <h1 id="processing-title">Understanding your report</h1>
        <p className="processing-intro">We’re carefully preparing a clear explanation from your report.</p>
        <ol className="processing-steps">
          {steps.map((step, index) => {
            const state = index < activeStep ? "complete" : index === activeStep ? "active" : "pending";
            return (
              <li className={`processing-step is-${state}`} key={step.title} aria-current={state === "active" ? "step" : undefined}>
                <span className="processing-state" aria-hidden="true">
                  {state === "complete" ? "✓" : state === "active" ? <i /> : ""}
                </span>
                <span className="processing-step-copy">
                  <strong>{step.title}</strong>
                  <small>{step.description}</small>
                </span>
                {state === "active" && <span className="processing-live-dot" aria-hidden="true" />}
              </li>
            );
          })}
        </ol>
        <p className="processing-privacy">Your report is processed for review and is not permanently stored by the upload endpoint.</p>
      </div>
    </main>
  );
}
