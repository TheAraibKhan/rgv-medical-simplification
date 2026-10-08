import { MedicalIcon } from "@/components/MedicalIcon";

export function VerificationPanel() {
  return (
    <section className="verification-section section-block" id="verification">
      <div className="verification-copy">
        <span className="section-label">THE VERIFICATION BOUNDARY</span>
        <h2>Explain the concept.<br /><span>Don’t invent the cause.</span></h2>
        <p>General knowledge can clarify medical language. It cannot authorize a new patient-specific diagnosis, cause, prognosis, severity claim, or recommendation.</p>
      </div>
      <div className="claim-visual">
        <div className="claim-visual-header"><span>ILLUSTRATIVE CLAIM CHECK</span><span className="claim-visual-code">EXAMPLE STATES · NOT MODEL OUTPUT</span></div>
        <div className="claim-source-row"><span className="claim-source-icon"><MedicalIcon name="report" size={16} /></span><div><small>IN THE SOURCE REPORT</small><strong>Enlarged heart · fluid around lungs</strong></div><span className="source-status"><MedicalIcon name="check" size={13} /> SOURCE</span></div>
        <div className="claim-check-list">
          <div className="claim-check claim-check-supported"><span className="claim-check-mark"><MedicalIcon name="check" size={14} /></span><span><strong>Heart appears enlarged</strong><small>Supported by a source finding</small></span><b>SUPPORTED BY SOURCE</b></div>
          <div className="claim-check claim-check-supported"><span className="claim-check-mark"><MedicalIcon name="check" size={14} /></span><span><strong>Fluid around the lungs</strong><small>Supported plain-language explanation</small></span><b>SUPPORTED</b></div>
          <div className="claim-check claim-check-review"><span className="claim-check-mark"><MedicalIcon name="warning" size={14} /></span><span><strong>Claim needs stronger evidence</strong><small>Ambiguous wording should be reviewed</small></span><b>NEEDS REVIEW</b></div>
          <div className="claim-check claim-check-boundary"><span className="claim-check-mark"><MedicalIcon name="x" size={14} /></span><span><strong>Cause is hypertension</strong><small>Unsupported patient-specific claim; cause not stated in source</small></span><b>UNSUPPORTED</b></div>
        </div>
        <div className="boundary-note"><MedicalIcon name="lock" size={14} /><span>External knowledge may explain terms, but does not establish a patient-specific cause.</span></div>
      </div>
    </section>
  );
}
