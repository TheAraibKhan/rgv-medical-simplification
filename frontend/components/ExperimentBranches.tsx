import { MedicalIcon } from "@/components/MedicalIcon";

const methods = [
  { id: "B1", title: "Direct prompting", marker: "LLM", className: "branch-b1", detail: "Report → LLM" },
  { id: "B2", title: "MedlinePlus RAG", marker: "RETRIEVAL", className: "branch-b2", detail: "Report → Knowledge → LLM" },
  { id: "B3", title: "RAG + two-tier verification", marker: "VERIFY", className: "branch-b3", detail: "Report → Knowledge → LLM → Checks" },
];

export function ExperimentBranches() {
  return (
    <section className="experiment-section section-block" id="method">
      <div className="section-intro section-intro-row">
        <div><span className="section-label">CONTROLLED EXPERIMENT</span><h2>One report. <span>Three paths.</span></h2></div>
        <p>B1, B2, and B3 isolate the role of retrieval and verification. The source report remains the same across conditions.</p>
      </div>
      <div className="branch-diagram">
        <div className="branch-source"><MedicalIcon name="report" size={18} /><span>SAME REPORT</span></div>
        <div className="branch-trunk" aria-hidden="true" />
        <div className="branch-paths">
          {methods.map((method, index) => (
            <div className={`branch-path ${method.className}`} key={method.id}>
              <div className="branch-connector" aria-hidden="true"><i /></div>
              <div className="branch-method">
                <div className="branch-method-top"><span>{method.id}</span><b>{method.marker}</b></div>
                <strong>{method.title}</strong>
                <small>{method.detail}</small>
                {index === 2 && <div className="branch-verify-chip"><MedicalIcon name="shield" size={13} /> explicit checks</div>}
              </div>
              <div className="branch-output-line" aria-hidden="true" />
            </div>
          ))}
        </div>
        <div className="branch-merge" aria-hidden="true"><span /><span /><span /></div>
        <div className="branch-comparison"><span>COMPARISON</span><strong>B1 <i /> B2 <i /> B3</strong><small>Primary research comparison: B2 vs B3</small></div>
      </div>
      <p className="branch-note"><MedicalIcon name="info" size={14} /> Comparison outputs, evidence, and claim checks appear in the results section after a completed run.</p>
    </section>
  );
}
