import { MedicalIcon } from "@/components/MedicalIcon";

export function BeforeAfterComparison() {
  return (
    <section className="before-after section-block" id="explanation">
      <div className="section-intro">
        <span className="section-label">ILLUSTRATIVE EXAMPLE · NOT CURRENT REPORT</span>
        <h2>Same finding. <span>Clearer language.</span></h2>
        <p>The source report stays in view as the wording becomes easier to understand.</p>
      </div>
      <div className="translation-panel">
        <div className="translation-side clinical-side">
          <div className="translation-label"><span className="translation-icon"><MedicalIcon name="report" size={17} /></span><span>CLINICAL LANGUAGE</span><span className="source-tag">SOURCE</span></div>
          <p>“Mild cardiomegaly with bilateral pleural effusion.”</p>
          <small>Illustrative wording only · not tied to the current report</small>
        </div>
        <div className="translation-bridge" aria-hidden="true"><span><MedicalIcon name="arrow" size={18} /></span><i /><small>TRANSLATE</small></div>
        <div className="translation-side patient-side">
          <div className="translation-label"><span className="translation-icon"><MedicalIcon name="patient" size={17} /></span><span>PATIENT-FRIENDLY EXPLANATION</span><span className="grounded-tag"><MedicalIcon name="check" size={12} /> SOURCE-GROUNDED</span></div>
          <p>“Your heart appears slightly larger than usual, and there is some fluid around the lungs.”</p>
          <small>Plain language, with no cause or diagnosis inferred</small>
        </div>
      </div>
    </section>
  );
}
