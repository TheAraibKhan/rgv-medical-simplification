# RGV Medical Simplification

Research prototype for **Retrieval-Grounded Verification for Improving Clinical Faithfulness in Patient-Oriented Medical Report Simplification**.

## Research design

- **B1 — Direct prompting:** report → LLM → simplification
- **B2 — Patient-oriented RAG:** report → MedlinePlus → LLM → simplification
- **B3 — RAG + verification:** report → MedlinePlus → LLM → two-tier verification → correction/flagging

Primary research comparison: **B2 vs B3**.

## Stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- LLM serving: local vLLM (OpenAI-compatible endpoint)
- Retrieval: Qdrant + dense embeddings, with BM25-ready interface
- Knowledge source: MedlinePlus
- Verification: NLI/entailment verifier (pluggable; exact model TBD)
- Database: PostgreSQL-ready metadata layer
- Experiment tracking: MLflow-ready
- Evaluation: pandas / SciPy / scikit-learn-ready

## Safety design

Patient-specific claims **must be supported by the source report**. External MedlinePlus evidence is only allowed to support clearly general explanatory content. Retrieved evidence must never authorize a new patient-specific diagnosis, cause, prognosis, severity claim, or recommendation.

## Modes

### Demo mode
Uses synthetic/open example reports. No MIMIC data.

### Research mode
Designed for locally stored, credentialed MIMIC-CXR data. Do not upload MIMIC-derived text to public services or commit it to Git.

## Quick start (demo)

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

The frontend defaults to the demo backend and can run B1/B2/B3 with the mock/demo providers.

In GitHub Codespaces, forward frontend port `3000`. The browser sends API calls
to the same-origin Next.js route at `/api/*`; the rewrite in
`frontend/next.config.mjs` forwards them to FastAPI at
`http://127.0.0.1:8000/api/*`. Copy `frontend/.env.example` to
`frontend/.env.local` (or set `NEXT_PUBLIC_API_URL=/api`) and restart Next.js
after changing the variable. No browser request to `localhost:8000` or separate
backend forwarded URL is needed.

FastAPI also allows localhost/127.0.0.1 development origins and forwarded
`*.app.github.dev` frontend origins by default; `FRONTEND_ORIGIN` can still be
used for an additional explicitly configured frontend origin.

The demo defaults to `APP_MODE=demo`, `LLM_PROVIDER=demo`, and
`VERIFIER_PROVIDER=heuristic`. It uses bundled mock retrieval data and does not
require an LLM, database, Qdrant server, or external API. PDF, TXT, and DOCX
uploads are extracted locally and kept in memory only; uploaded files and text
are not saved by the upload endpoint. Image OCR is optional and is enabled only
when both the local Tesseract executable and `pytesseract` are installed.
Demo retrieval is deterministic and report-matched: it recognizes myocardial
infarction, left ventricular enlargement, cardiomegaly, pleural effusion,
pneumothorax, and atelectasis, while excluding negated findings and never
filling unused Top-K slots with unrelated evidence. B1 uses only the source
report; B2 uses the report plus relevant retrieved definitions; B3 reuses B2's
exact evidence and adds claim-level checks against the report and general
explanations. Demo verification is heuristic, not a clinical evaluation.

Check the backend with `curl http://localhost:8000/api/health`. Submit a
comparison with
`curl -X POST http://localhost:8000/api/compare -H 'Content-Type: application/json' -d '{"report":"Mild cardiomegaly with bilateral pleural effusion. No evidence of pneumothorax.","top_k":3}'`.

## Research mode

Research mode uses local components only. It does not download a model or
MedlinePlus data at startup. If its required local model, verifier, or snapshot
is not configured or the local model endpoint is unavailable, comparisons
explicitly run in labeled demo mode.

1. Start a local OpenAI-compatible vLLM server; do not point the research app at
   a hosted model service.
2. Set `APP_MODE=research`, `LLM_PROVIDER=vllm`, `VLLM_BASE_URL`,
   `VLLM_MODEL`, `VLLM_API_KEY`, and `VERIFIER_PROVIDER=vllm` in the backend
   environment. `VERIFIER_MODEL` may select a separate local verifier model;
   otherwise the configured local model is used.
3. Prepare a local, dated MedlinePlus JSON Lines snapshot and set
   `MEDLINEPLUS_CORPUS_PATH` and `MEDLINEPLUS_SNAPSHOT_DATE`. Each line must be
   a JSON object with `document_id` (or `id`), `title`, `text` (or `snippet`),
   and `url`; `snapshot_date` may be set per document. The backend builds its
   BM25 index from this corpus at startup. Search uses report-derived positive
   text and returns only documents with a nonzero retrieval score.
4. Keep research reports, snapshots, and model serving on the local machine.
   Do not use sensitive or credentialed data in demo mode.

Download an English Health Topic XML snapshot manually from the official
[MedlinePlus XML downloads](https://medlineplus.gov/xml.html) page, then convert
it locally:

```bash
cd backend
python scripts/build_medlineplus_snapshot.py \
  --input /path/to/downloaded-health-topics.xml \
  --output data/medlineplus/snapshot.jsonl \
  --snapshot-date YYYY-MM-DD
```

The converter preserves each document ID, title, summary, synonyms, URL, and
the supplied snapshot date. The local BM25 index is built from that JSONL file
when FastAPI starts; retrieval does not call MedlinePlus at request time.
Snapshots are ignored by Git so downloaded public data is not accidentally
committed. Research runs should preserve source URLs and snapshot dates for
provenance and reproducibility.

vLLM exposes an OpenAI-compatible HTTP API; the backend uses the standard
Python OpenAI client against the configured local endpoint.

## Project structure

```text
backend/       FastAPI research backend
frontend/      Next.js research UI
scripts/       data/retrieval/evaluation helpers
configs/       configuration files
 data/
   demo/       synthetic demo data
   medlineplus/ local knowledge snapshot
   local/      ignored local research data
```

## Important

This repository is a research prototype, not a diagnostic or treatment system. It must not be used for unsupervised patient care.
