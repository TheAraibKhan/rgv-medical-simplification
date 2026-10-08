import { MedicalIcon } from "@/components/MedicalIcon";

const steps = [
  { title: "Reading your report", description: "Extracting text and findings" },
  { title: "Identifying clinical concepts", description: "Finding meaningful report findings" },
  { title: "Retrieving medical information", description: "Searching relevant patient-oriented knowledge" },
  { title: "Generating explanation", description: "Preparing patient-friendly language" },
  { title: "Verifying explanation", description: "Checking generated claims" },
  { title: "Preparing results", description: "Organizing both report views" },
];

export function AnalysisProcessing({ activeStep }: { activeStep: number }) {
  return (
    <main className="processing-screen" aria-labelledby="processing-title" aria-live="polite">
      <div className="processing-content">
        <a className="brand processing-brand" href="#home" aria-label="RGV Medical Simplification">
          <span className="brand-symbol"><span>R</span><i /><span>V</span></span>
          <span className="brand-name"><strong>RGV</strong><small>Medical Simplification</small></span>
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
        <p className="processing-privacy">Your report is processed by the RGV research prototype and is not permanently stored by the upload endpoint.</p>
      </div>
    </main>
  );
}
