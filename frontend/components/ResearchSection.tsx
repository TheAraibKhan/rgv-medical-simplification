const rationales = [
  {
    number: "01",
    title: "Why retrieval?",
    prompt: "General explanatory knowledge",
    effect: "MedlinePlus may support clearer explanations of medical concepts.",
    color: "rationale-blue",
  },
  {
    number: "02",
    title: "Why verification?",
    prompt: "Generated claims",
    effect: "B3 checks whether claims remain supported by the appropriate evidence.",
    color: "rationale-violet",
  },
  {
    number: "03",
    title: "Why three conditions?",
    prompt: "B1 → B2 → B3",
    effect: "Compare direct prompting, retrieval, and retrieval with explicit verification.",
    color: "rationale-teal",
  },
];

export function ResearchSection() {
  return (
    <section className="research-section section-block" id="research">
      <div className="section-intro section-intro-row">
        <div><span className="section-label">RESEARCH DETAILS</span><h2>Test what each step <span>contributes.</span></h2></div>
        <p>Does retrieval-grounded verification improve clinical faithfulness beyond retrieval alone?</p>
      </div>
      <div className="rationale-diagram">
        {rationales.map((item, index) => (
          <article className={`rationale-node ${item.color}`} key={item.number}>
            <span className="rationale-number">{item.number}</span>
            <h3>{item.title}</h3>
            <div className="rationale-flow"><strong>{item.prompt}</strong><span>↓</span><p>{item.effect}</p></div>
            {index < rationales.length - 1 && <div className="rationale-arrow" aria-hidden="true">→</div>}
          </article>
        ))}
      </div>
      <div className="research-footnote">Primary research comparison <strong>B2 vs B3</strong><span>retrieval alone vs. retrieval + two-tier verification</span></div>
    </section>
  );
}
