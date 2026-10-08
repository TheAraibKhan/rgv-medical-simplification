from __future__ import annotations

import json
import re
from typing import Iterable

from openai import OpenAI

from app.core.config import settings
from app.schemas.common import Claim, ClaimType, ClaimVerification, Evidence, VerificationLabel


class VerificationService:
    """Pluggable verifier.

    The default is a deliberately conservative heuristic for demo/testing only.
    Replace with a validated clinical/radiology NLI model before empirical claims.
    """

    def __init__(self) -> None:
        self.client = (
            OpenAI(base_url=settings.vllm_base_url, api_key=settings.vllm_api_key)
            if settings.verifier_provider.lower() == "vllm" and settings.vllm_model.strip()
            else None
        )

    def verify(
        self,
        claim: Claim,
        report: str,
        evidence: Iterable[Evidence],
        mode: str = "demo",
    ) -> ClaimVerification:
        evidence_list = list(evidence)
        if mode == "demo":
            return self._heuristic_verify(claim, report, evidence_list)
        if settings.verifier_provider.lower() == "vllm":
            return self._local_model_verify(claim, report, evidence_list)
        if settings.verifier_provider == "heuristic":
            return self._heuristic_verify(claim, report, evidence_list)
        raise RuntimeError(f"Unsupported verifier provider: {settings.verifier_provider}")

    def _local_model_verify(
        self,
        claim: Claim,
        report: str,
        evidence: list[Evidence],
    ) -> ClaimVerification:
        if self.client is None:
            raise RuntimeError("The local verification model is not configured.")
        patient_specific = claim.claim_type == ClaimType.PATIENT_SPECIFIC
        allowed_source = (
            f"SOURCE REPORT:\n{report}"
            if patient_specific
            else "RETRIEVED GENERAL EXPLANATORY EVIDENCE:\n"
            + json.dumps([item.model_dump() for item in evidence], ensure_ascii=False)
        )
        response = self.client.chat.completions.create(
            model=settings.verifier_model or settings.vllm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Verify exactly one claim. Patient-specific claims may be supported only by the source report. "
                        "General explanations may be supported only by retrieved evidence. Never infer support. "
                        "Return JSON with keys label, quote, reason. label must be SUPPORTED, NEEDS_REVIEW, "
                        "CONTRADICTED, or UNSUPPORTED_PATIENT_CLAIM."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{allowed_source}\n\nCLAIM:\n{claim.text}",
                },
            ],
            temperature=0,
            max_tokens=250,
        )
        content = response.choices[0].message.content or ""
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("The local verifier returned invalid JSON.") from exc

        label_text = result.get("label")
        try:
            label = VerificationLabel(label_text)
        except ValueError as exc:
            raise RuntimeError("The local verifier returned an unsupported status.") from exc

        quote = result.get("quote", "")
        allowed_text = report if patient_specific else "\n".join(item.text for item in evidence)
        quote_is_grounded = (
            isinstance(quote, str)
            and bool(quote.strip())
            and quote.casefold() in allowed_text.casefold()
        )
        if label == VerificationLabel.SUPPORTED and not quote_is_grounded:
            label = (
                VerificationLabel.UNSUPPORTED_PATIENT_CLAIM
                if patient_specific
                else VerificationLabel.NEEDS_REVIEW
            )

        supporting_evidence: list[Evidence] = []
        if quote_is_grounded:
            if patient_specific:
                supporting_evidence = [Evidence(source="Source report", title="Source report", text=quote)]
            else:
                supporting_evidence = [
                    item for item in evidence if quote.casefold() in item.text.casefold()
                ]

        return ClaimVerification(
            claim_id=claim.claim_id,
            label=label,
            evidence=supporting_evidence,
            reason=str(result.get("reason") or "Local verifier returned no explanation."),
        )

    def _heuristic_verify(self, claim: Claim, report: str, evidence: list[Evidence]) -> ClaimVerification:
        claim_lower = claim.text.lower()
        report_lower = report.lower()

        if claim.claim_type == ClaimType.PATIENT_SPECIFIC:
            unsupported_inference = re.search(
                r"\b(?:caused by|cause is|due to|because of|probably caused|likely caused|will recover|"
                r"will worsen|should take|should receive|needs treatment|recommend(?:ed|ation)?)\b",
                claim_lower,
            )
            if unsupported_inference:
                return ClaimVerification(
                    claim_id=claim.claim_id,
                    label=VerificationLabel.UNSUPPORTED_PATIENT_CLAIM,
                    evidence=[Evidence(source="Source report", title="Source report", text=report)],
                    reason="Patient-specific cause, prognosis, or recommendation is not authorized by the source report.",
                )

            mappings = {
                "heart appears slightly larger than normal": ("cardiomegaly",),
                "heart appears slightly larger than usual": ("cardiomegaly",),
                "enlarged heart": ("cardiomegaly",),
                "a heart attack": ("myocardial infarction", "acute myocardial infarction"),
                "affecting the lower wall of the heart": ("inferior wall",),
                "there is fluid around the lung": ("pleural effusion",),
                "fluid around both lungs": ("pleural effusion",),
                "fluid around the lungs": ("pleural effusion",),
                "a small area of the lung is not fully expanded": ("atelectasis",),
                "areas of the lungs that are not fully expanded": ("atelectatic",),
                "air around the lung": ("pneumothorax",),
                "does not show a collapsed lung": ("pneumothorax",),
                "report does not show a collapsed lung": ("pneumothorax",),
                "lower wall of the heart": ("inferior wall",),
                "heart's main pumping chamber": ("left ventricular",),
            }
            direct = claim_lower in report_lower
            mapped = any(
                source in claim_lower
                and self._mapping_is_grounded(claim_lower, report_lower, source, targets)
                for source, targets in mappings.items()
            )
            claim_asserts_positive_pneumothorax = (
                "pneumothorax" in claim_lower or "air around the lung" in claim_lower
            ) and not any(marker in claim_lower for marker in ("no ", "not ", "without "))
            source_negates_pneumothorax = bool(
                re.search(r"\b(?:no|without|absent|negative for)\b[^.!?;]{0,50}\bpneumothorax\b", report_lower)
            )
            if claim_asserts_positive_pneumothorax and source_negates_pneumothorax:
                return ClaimVerification(
                    claim_id=claim.claim_id,
                    label=VerificationLabel.CONTRADICTED,
                    evidence=[Evidence(source="Source report", title="Source report", text=report)],
                    reason="The generated patient-specific claim conflicts with a negated finding in the source report.",
                )
            if direct or mapped:
                return ClaimVerification(
                    claim_id=claim.claim_id,
                    label=VerificationLabel.SUPPORTED,
                    evidence=[Evidence(source="Source report", title="Source report", text=report)],
                    reason="Demo verifier found direct or predefined semantic support in the source report.",
                )
            return ClaimVerification(
                claim_id=claim.claim_id,
                label=VerificationLabel.UNSUPPORTED_PATIENT_CLAIM,
                evidence=[Evidence(source="Source report", title="Source report", text=report)],
                reason="No sufficient support for the patient-specific assertion was found in the source report.",
            )

        joined = " ".join(item.text.lower() for item in evidence)
        claim_terms = [
            term for term in re.findall(r"[a-zA-Z]{4,}", claim_lower)
            if term not in {"your", "this", "means", "that", "general", "information", "individual"}
        ]
        supported_terms = sum(1 for term in claim_terms if term in joined)
        if evidence and claim_terms and supported_terms / len(claim_terms) >= 0.4:
            return ClaimVerification(
                claim_id=claim.claim_id,
                label=VerificationLabel.SUPPORTED,
                evidence=evidence,
                reason="Demo verifier found sufficient lexical support in retrieved explanatory evidence.",
            )
        return ClaimVerification(
            claim_id=claim.claim_id,
            label=VerificationLabel.NEEDS_REVIEW,
            evidence=evidence,
            reason="Retrieved evidence did not provide sufficient support for the general explanation.",
        )

    @staticmethod
    def _mapping_is_grounded(
        claim: str,
        report: str,
        source_phrase: str,
        targets: tuple[str, ...],
    ) -> bool:
        claim_start = claim.find(source_phrase)
        claim_negated = VerificationService._is_negated(claim, claim_start) or bool(
            re.match(
                r"(?:report\s+)?(?:does\s+not\s+show|no|not|without|absent|negative\s+for)\b",
                claim[claim_start:],
            )
        )
        for target in targets:
            report_start = report.find(target)
            if report_start >= 0 and VerificationService._is_negated(report, report_start) == claim_negated:
                return True
        return False

    @staticmethod
    def _is_negated(text: str, match_start: int) -> bool:
        clause_start = max(text.rfind(mark, 0, match_start) for mark in (".", "!", "?", ";", "\n")) + 1
        prefix = re.split(r"\b(?:but|however|although|whereas)\b", text[clause_start:match_start])[-1]
        return bool(
            re.search(
                r"\b(?:no|not|without|absent|negative\s+for|free\s+of|rule\s+out)\b",
                prefix,
                flags=re.IGNORECASE,
            )
        )


verifier = VerificationService()
