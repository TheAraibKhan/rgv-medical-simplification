from __future__ import annotations

import re
import time
import logging

from app.core.config import settings
from app.retrieval.medlineplus import retriever
from app.schemas.common import ClaimType, CompareRequest, CompareResponse, ConditionResult, Evidence, Finding, VerificationLabel
from app.services.claims import decompose
from app.services.clinical_structure import structure_medical_report
from app.services.llm import llm_service
from app.verification.verifier import verifier

logger = logging.getLogger(__name__)


class ResearchPipeline:
    @property
    def active_mode(self) -> str:
        research_ready = (
            settings.app_mode.lower() == "research"
            and llm_service.active_provider == "vllm"
            and settings.verifier_provider.lower() == "vllm"
            and bool(settings.vllm_model.strip())
            and bool(settings.verifier_model.strip() or settings.vllm_model.strip())
            and bool(retriever.docs)
            and llm_service.local_model_available()
        )
        return "research" if research_ready else "demo"

    def compare(self, request: CompareRequest) -> CompareResponse:
        started = time.perf_counter()
        mode = self.active_mode

        structured_started = time.perf_counter()
        structured = structure_medical_report(request.report)

        # Demo generation should use only the structured patient-specific
        # information rather than echoing tens of thousands of raw characters.
        # The complete raw report is still preserved in structured.raw_source.
        patient_source = self._generation_source(structured, mode)

        logger.info(
            "COMPARE start mode=%s report_chars=%d generation_chars=%d top_k=%d",
            mode,
            len(request.report),
            len(patient_source),
            request.top_k,
        )
        logger.info(
            "COMPARE structure_ms=%.1f results=%d findings=%d",
            (time.perf_counter() - structured_started) * 1000,
            len(structured.results),
            len(structured.findings),
        )
        findings = [
            Finding(
                text=item.text,
                polarity="NEGATED" if item.negated else "AFFIRMED",
                section=item.section,
                patient_specific=item.patient_specific,
                retrieval_eligible=item.retrieval_eligible,
                source_text=item.source_text,
                source_span=item.source_span,
            )
            for item in structured.findings
        ]
        findings.extend(
            Finding(
                text=(
                    f"{item.short_name or item.test_name}: "
                    f"{item.value} {item.unit or ''}".strip()
                    if item.value is not None
                    else f"{item.short_name or item.test_name}: Result not available in the supplied report."
                ),
                polarity="AFFIRMED",
                section=item.section,
                patient_specific=item.patient_specific,
                retrieval_eligible=item.retrieval_eligible,
                source_text=item.source_text,
                source_span=item.source_span,
            )
            for item in structured.results
        )
        retrieval_started = time.perf_counter()
        query_text = "\n".join(structured.retrieval_queries)
        evidence = self._retrieve(query_text, request.top_k, mode)

        logger.info(
            "COMPARE retrieval_ms=%.1f evidence=%d",
            (time.perf_counter() - retrieval_started) * 1000,
            len(evidence),
        )

        try:
            b1_started = time.perf_counter()
            b1 = self._run_b1(patient_source, mode)
            logger.info(
                "COMPARE b1_ms=%.1f",
                (time.perf_counter() - b1_started) * 1000,
            )

            b2_started = time.perf_counter()
            b2 = self._run_b2(patient_source, evidence, mode)
            logger.info(
                "COMPARE b2_ms=%.1f",
                (time.perf_counter() - b2_started) * 1000,
            )

            b3_started = time.perf_counter()
            b3 = self._run_b3(patient_source, evidence, mode)
            logger.info(
                "COMPARE b3_ms=%.1f",
                (time.perf_counter() - b3_started) * 1000,
            )
        except Exception as exc:
            logger.exception("Explanation stage failed; returning structured extraction only.")
            fallback = self._structured_only_result(patient_source, mode, str(exc))
            b1 = fallback
            b2 = fallback.model_copy(update={"condition": "B2", "evidence": evidence})
            b3 = fallback.model_copy(update={"condition": "B3", "evidence": evidence})
        response = CompareResponse(
            report=request.report,
            findings=findings,
            structured_report=structured,
            mode=mode,
            b1=b1,
            b2=b2,
            b3=b3,
        )

        logger.info(
            "COMPARE complete_ms=%.1f mode=%s",
            (time.perf_counter() - started) * 1000,
            mode,
        )

        return response

    @staticmethod
    def _structured_only_result(report: str, mode: str, error: str) -> ConditionResult:
        output = (
            report
            if report and not report.startswith("No patient-specific result")
            else "The report was structured, but the explanation stage was unavailable. Review the extracted result table."
        )
        return ConditionResult(
            condition="B1",
            output=output,
            claims=[],
            verifications=[],
            evidence=[],
            latency_ms=0.0,
            mode=mode,
            correction_note=f"Explanation stage unavailable: {error}",
        )

    @staticmethod
    def _generation_source(structured, mode: str) -> str:
        if mode != "demo":
            return structured.patient_source_text

        parts: list[str] = []

        for result in structured.results:
            if result.status == "reported" and result.value is not None:
                text = " ".join(
                    part
                    for part in (
                        result.short_name or result.test_name,
                        result.value,
                        result.unit,
                    )
                    if part
                )

                if result.reference_interval:
                    text += f" (reference: {result.reference_interval})"

                parts.append(text)

            elif result.status == "pending":
                parts.append(
                    f"{result.short_name or result.test_name}: result pending"
                )

        for finding in structured.findings:
            if finding.explanation_eligible:
                prefix = "No " if finding.negated else ""
                parts.append(f"{prefix}{finding.text.strip()}")

        compact = "\n".join(
            dict.fromkeys(
                part.strip()
                for part in parts
                if part and part.strip()
            )
        ).strip()

        # Prevent very large demo responses/claim sets.
        return (compact or structured.patient_source_text)[:6000]

    def _retrieve(self, report: str, top_k: int, mode: str | None = None) -> list[Evidence]:
        if (mode or self.active_mode) == "demo":
            return retriever.demo_search(report, top_k)
        return retriever.local_search(report, top_k)

    def _run_b1(self, report: str, mode: str | None = None) -> ConditionResult:
        start = time.perf_counter()
        run_mode = mode or self.active_mode
        output = llm_service.generate(report, condition="B1", mode=run_mode)
        return ConditionResult(
            condition="B1",
            output=output,
            claims=decompose(output),
            latency_ms=(time.perf_counter() - start) * 1000,
            mode=run_mode,
        )

    def _run_b2(self, report: str, evidence: list[Evidence], mode: str | None = None) -> ConditionResult:
        start = time.perf_counter()
        run_mode = mode or self.active_mode
        output = llm_service.generate(
            report,
            [e.model_dump() for e in evidence],
            condition="B2",
            mode=run_mode,
        )
        return ConditionResult(
            condition="B2",
            output=output,
            claims=decompose(output),
            evidence=evidence,
            latency_ms=(time.perf_counter() - start) * 1000,
            mode=run_mode,
        )

    def _run_b3(self, report: str, evidence: list[Evidence], mode: str | None = None) -> ConditionResult:
        start = time.perf_counter()
        run_mode = mode or self.active_mode
        first_pass_output = llm_service.generate(
            report,
            [e.model_dump() for e in evidence],
            condition="B3",
            mode=run_mode,
        )
        claims = decompose(first_pass_output)
        verifications = [
            verifier.verify(
                claim,
                report,
                evidence if claim.claim_type == ClaimType.GENERAL_EXPLANATORY else [],
                mode=run_mode,
            )
            for claim in claims
        ]

        unsupported_ids = {
            item.claim_id
            for item in verifications
            if item.label in {
                VerificationLabel.CONTRADICTED,
                VerificationLabel.UNSUPPORTED_PATIENT_CLAIM,
            }
        }
        output = self._remove_unsupported_claims(first_pass_output, claims, unsupported_ids)
        correction_applied = output != first_pass_output
        safe_claims = {claim.text for claim in decompose(output)}
        claim_text_by_id = {claim.claim_id: claim.text for claim in claims}
        verifications = [
            item.model_copy(update={
                "original_claim": claim_text_by_id[item.claim_id],
                "final_claim": (
                    claim_text_by_id[item.claim_id]
                    if claim_text_by_id[item.claim_id] in safe_claims
                    else None
                ),
                "changed": claim_text_by_id[item.claim_id] not in safe_claims,
            })
            for item in verifications
        ]
        correction_note = (
            "Unsupported or contradicted patient-specific wording was withheld; see claim-level checks."
            if correction_applied
            else None
        )

        return ConditionResult(
            condition="B3",
            output=output,
            claims=claims,
            verifications=verifications,
            evidence=evidence,
            latency_ms=(time.perf_counter() - start) * 1000,
            mode=run_mode,
            first_pass_output=first_pass_output,
            correction_applied=correction_applied,
            correction_note=correction_note,
        )

    @staticmethod
    def _remove_unsupported_claims(output: str, claims, unsupported_ids: set[str]) -> str:
        unsupported = [claim.text for claim in claims if claim.claim_id in unsupported_ids]
        if not unsupported:
            return output

        safe_sentences: list[str] = []
        sentences = re.split(r"(?<=[.!?])\s+|\n+", output)
        for sentence in sentences:
            if not sentence.strip():
                continue
            sentence_claims = decompose(sentence)
            if any(claim.text in unsupported for claim in sentence_claims):
                continue
            safe_sentences.append(sentence)

        return "\n".join(safe_sentences) or (
            "Some first-pass wording was withheld because it was not adequately supported by the source report."
        )


pipeline = ResearchPipeline()
