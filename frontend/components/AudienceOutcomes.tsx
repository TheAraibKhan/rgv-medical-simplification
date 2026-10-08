import { MedicalIcon } from "@/components/MedicalIcon";

const audiences = [
  {
    id: "patients",
    label: "PATIENT VIEW",
    title: "Understand your report in clear, everyday language.",
    description: "Plain-language explanation, key findings, and what medical terms mean.",
    icon: "patient" as const,
    theme: "patient-outcome",
    items: ["Plain-language explanation", "Key findings", "Medical terms, explained", "Evidence-backed wording"],
  },
  {
    id: "clinicians",
    label: "CLINICIAN VIEW",
    title: "Inspect evidence, retrieval, and verification.",
    description: "An evidence-oriented view for research review and method comparison.",
    icon: "clinician" as const,
    theme: "clinician-outcome",
    items: ["Source evidence", "Retrieved context", "Claim-level checks", "B1 / B2 / B3 comparison"],
  },
];

export function AudienceOutcomes() {
  return (
    <section className="audience-section section-block" id="use-cases">
      <div className="section-intro section-intro-row">
        <div><span className="section-label">TWO VIEWS · ONE SOURCE</span><h2>Different audiences. <span>Shared evidence.</span></h2></div>
        <p>Both views start from the same medical report. The presentation changes; the source grounding does not.</p>
      </div>
      <div className="outcome-grid">
        {audiences.map((audience) => (
          <article className={`outcome-card ${audience.theme}`} key={audience.id}>
            <div className="outcome-card-top"><span className="outcome-icon"><MedicalIcon name={audience.icon} size={21} /></span><span className="outcome-label">{audience.label}</span><span className="same-source">SAME SOURCE <i /></span></div>
            <h3>{audience.title}</h3>
            <p>{audience.description}</p>
            <ul>{audience.items.map((item) => <li key={item}><MedicalIcon name="check" size={13} />{item}</li>)}</ul>
          </article>
        ))}
      </div>
    </section>
  );
}
