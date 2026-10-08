import { MedicalIcon } from "@/components/MedicalIcon";

export function ResearchPipeline() {
  return (
    <div className="hero-visual-shell" role="img" aria-label="Medical report flows through patient-oriented retrieval, AI simplification, and verification before branching into patient and clinician explanations">
      <div className="hero-visual-topbar">
        <span><i /> HOW THE SYSTEM WORKS</span>
        <span>01—05 · INFORMATION FLOW</span>
      </div>
      <div className="pipeline-art">
        <svg className="pipeline-wires" viewBox="0 0 760 500" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="wireA" x1="0" x2="1">
              <stop offset="0" stopColor="#56aec7" stopOpacity=".2" />
              <stop offset=".48" stopColor="#39b6b5" stopOpacity=".8" />
              <stop offset="1" stopColor="#7298de" stopOpacity=".35" />
            </linearGradient>
            <linearGradient id="wireB" x1="0" x2="1">
              <stop offset="0" stopColor="#54c5be" stopOpacity=".08" />
              <stop offset=".5" stopColor="#55c6bc" stopOpacity=".8" />
              <stop offset="1" stopColor="#a18be2" stopOpacity=".6" />
            </linearGradient>
            <filter id="softGlow" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          <path className="wire wire-base" d="M125 152 C180 152 176 100 242 100 S330 122 357 199 S436 260 480 208 S536 155 571 158" />
          <path className="wire wire-flow" d="M125 152 C180 152 176 100 242 100 S330 122 357 199 S436 260 480 208 S536 155 571 158" />
          <path className="wire wire-base" d="M514 178 C562 186 540 289 592 294" />
          <path className="wire wire-flow wire-branch" d="M514 178 C562 186 540 289 592 294" />
          <path className="wire wire-base" d="M514 178 C574 180 544 386 592 391" />
          <path className="wire wire-flow wire-branch wire-clinician" d="M514 178 C574 180 544 386 592 391" />
          <circle className="flow-particle particle-small" r="3" filter="url(#softGlow)"><animateMotion dur="8s" repeatCount="indefinite" path="M125 152 C180 152 176 100 242 100 S330 122 357 199 S436 260 480 208 S536 155 571 158" /></circle>
          <circle className="flow-particle particle-large" r="4.2" filter="url(#softGlow)"><animateMotion dur="8s" begin="-3.9s" repeatCount="indefinite" path="M125 152 C180 152 176 100 242 100 S330 122 357 199 S436 260 480 208 S536 155 571 158" /></circle>
          <circle className="flow-particle particle-branch" r="2.8" filter="url(#softGlow)"><animateMotion dur="5s" repeatCount="indefinite" path="M514 178 C562 186 540 289 592 294" /></circle>
          <circle className="wire-node" cx="242" cy="100" r="4" />
          <circle className="wire-node" cx="357" cy="199" r="5" />
          <circle className="wire-node" cx="480" cy="208" r="4" />
        </svg>

        <div className="anatomy-watermark" aria-hidden="true">
          <div className="anatomy-grid" />
          <svg viewBox="0 0 190 230" fill="none">
            <path d="M94 26v79M94 64c-21-27-39-35-52-26-14 10-16 34-26 64-10 30-5 66 21 74 27 8 55-18 57-61M96 64c21-27 39-35 52-26 14 10 16 34 26 64 10 30 5 66-21 74-27 8-55-18-57-61" />
            <path d="M94 27c-7-7-7-14 0-20 7 6 7 13 0 20ZM94 80l-21 20m21-20 21 20" />
          </svg>
          <span>CHEST RADIOGRAPH · VISUAL MOTIF</span>
        </div>

        <div className="flow-node report-node">
          <div className="report-node-paper">
            <div className="report-mini-head"><MedicalIcon name="report" size={15} /><span>ILLUSTRATIVE REPORT</span></div>
            <div className="xray-motif"><MedicalIcon name="lungs" size={40} /></div>
            <div className="report-finding-mini">Mild cardiomegaly</div>
            <div className="report-finding-mini finding-highlight">Bilateral pleural effusion</div>
            <div className="report-finding-mini finding-negative-mini">No pneumothorax</div>
          </div>
          <span className="node-caption">01 · MEDICAL REPORT</span>
        </div>

        <div className="flow-node retrieval-node">
          <div className="retrieval-stack">
            <span /><span /><span />
            <div className="retrieval-core"><MedicalIcon name="database" size={22} /></div>
          </div>
          <div className="retrieval-snippets">
            <small>QUERY CONCEPTS</small>
            <span>Cardiomegaly <i /></span>
            <span>Pleural effusion <i /></span>
          </div>
          <span className="node-caption">02 · MEDLINEPLUS</span>
        </div>

        <div className="flow-node ai-node">
          <div className="ai-halo"><div className="ai-core"><MedicalIcon name="brain" size={27} /></div></div>
          <span className="node-caption">03 · AI SIMPLIFICATION</span>
          <span className="node-subcaption">CLEAR LANGUAGE</span>
        </div>

        <div className="flow-node verify-node">
          <div className="verify-shield"><MedicalIcon name="shield" size={24} /></div>
          <span className="node-caption">04 · VERIFICATION</span>
          <span className="node-subcaption">TWO-TIER CHECK</span>
        </div>

        <span className="output-stage-label">05 · OUTPUT</span>
        <div className="flow-destination patient-destination">
          <span className="destination-icon patient-dest-icon"><MedicalIcon name="patient" size={18} /></span>
          <span><strong>PATIENT</strong><small>Plain-language view</small></span>
        </div>
        <div className="flow-destination clinician-destination">
          <span className="destination-icon clinician-dest-icon"><MedicalIcon name="clinician" size={18} /></span>
          <span><strong>CLINICIAN</strong><small>Evidence view</small></span>
        </div>
        <div className="visual-footnote"><span className="footnote-dot" /> Same source · two audience views</div>
      </div>
    </div>
  );
}
