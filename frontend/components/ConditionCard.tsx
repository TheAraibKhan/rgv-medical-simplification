import type { Condition, Verification } from "@/lib/api";

type Variant = "b1" | "b2" | "b3";

const conditionDetails: Record<Variant, { title: string; method: string; description: string }> = {
  b1: { title: "Direct prompting", method: "LLM only", description: "Simplification without external retrieval." },
  b2: { title: "MedlinePlus RAG", method: "+ Retrieval", description: "Patient-oriented retrieval supports the simplification." },
  b3: { title: "RAG + two-tier verification", method: "+ Verification", description: "Retrieved context with two-tier verification." },
};

function badgeClass(label: Verification["label"]) {
  if (label === "SUPPORTED") return "verification-badge verification-supported";
  if (label === "CONTRADICTED" || label === "UNSUPPORTED_PATIENT_CLAIM") return "verification-badge verification-contradicted";
  if (label === "NEEDS_REVIEW") return "verification-badge verification-review";
  return "verification-badge";
}

export function ConditionCard({ item, variant }: { item: Condition; variant: Variant }) {
  const details = conditionDetails[variant];
  const isVerificationCondition = variant === "b3";

  return (
    <article className={`condition-card condition-${variant}`}>
      <header className="condition-header">
        <div className="condition-heading">
          <span className="condition-id">{variant.toUpperCase()}</span>
          <div>
            <h3>{details.title}</h3>
            <p>{details.description}</p>
          </div>
        </div>
        <span className="method-badge">{details.method}</span>
      </header>

      <div className="condition-status">Status · {item.mode === "demo" ? "Demo output" : item.mode}</div>
      {isVerificationCondition && item.first_pass_output !== undefined && item.first_pass_output !== null && (
        <>
          <h4 className="output-label">First-pass explanation</h4>
          <div className="output-text">{item.first_pass_output}</div>
        </>
      )}
      <h4 className="output-label">{isVerificationCondition ? "Final explanation" : "Generated explanation"}</h4>
      <div className="output-text">{item.output}</div>
      {isVerificationCondition && item.correction_note && <p className="correction-note">{item.correction_note}</p>}

      <div className="condition-metrics">
        <div className="metric-chip">
          <span>Clinical faithfulness</span>
          <strong>Not evaluated</strong>
        </div>
        <div className="metric-chip">
          <span>{isVerificationCondition ? "Claim verification" : "Verification"}</span>
          <strong>{isVerificationCondition
            ? `${item.verifications.length} claim${item.verifications.length === 1 ? "" : "s"} checked`
            : "Not applicable"}</strong>
        </div>
      </div>

      {isVerificationCondition && item.claims.length > 0 && (
        <section className="claim-list" aria-label={`${variant.toUpperCase()} claims`}>
          <h4>Claim-level verification</h4>
          {item.claims.map((claim) => {
            const verification = item.verifications.find((entry) => entry.claim_id === claim.claim_id);
            const status = verification?.label === "UNSUPPORTED_PATIENT_CLAIM" || verification?.label === "CONTRADICTED"
              ? "UNSUPPORTED PATIENT CLAIM"
              : verification?.label === "NEEDS_REVIEW"
                ? "NEEDS REVIEW"
                : verification?.label === "SUPPORTED" && claim.claim_type === "PATIENT_SPECIFIC"
                  ? "SUPPORTED BY SOURCE"
                  : verification?.label === "SUPPORTED"
                    ? "SUPPORTED AS GENERAL EXPLANATION"
                    : "NOT CHECKED";
            return (
              <div className="claim-item" key={claim.claim_id}>
                <p>{claim.text}</p>
                <div className="claim-meta">
                  <span>{claim.claim_type === "PATIENT_SPECIFIC" ? "Patient-specific" : "General explanatory"}</span>
                  {verification && (
                    <span className={badgeClass(verification.label)}>{status}</span>
                  )}
                </div>
                {verification && (
                  <>
                    <p className="claim-reason">{verification.reason}</p>
                    <p className="claim-reason">Checked against: {verification.evidence.length
                      ? verification.evidence.map((source) => source.source).filter((source, index, all) => all.indexOf(source) === index).join(", ")
                      : "No supporting source"}</p>
                  </>
                )}
              </div>
            );
          })}
        </section>
      )}

      <section className="evidence-list" aria-label={`${variant.toUpperCase()} source evidence`}>
        <h4>Retrieved evidence</h4>
        {item.evidence.length > 0 ? item.evidence.slice(0, 3).map((evidence, index) => (
          <div className="evidence-item" key={evidence.document_id ?? `${evidence.source}-${index}`}>
            {evidence.url
              ? <a href={evidence.url} target="_blank" rel="noreferrer">{evidence.title || evidence.source}</a>
              : <strong>{evidence.title || evidence.source}</strong>}
            <small>{evidence.source}{evidence.snapshot_date ? ` · snapshot ${evidence.snapshot_date}` : ""}</small>
            <p className="evidence-text">{evidence.text}</p>
          </div>
        )) : (
          <p className="evidence-empty">{variant === "b1" ? "None — direct prompting uses the source report only." : "No relevant retrieved evidence for this report."}</p>
        )}
      </section>
    </article>
  );
}
