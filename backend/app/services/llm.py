from __future__ import annotations

import json
import re
import time
import logging
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


DIRECT_SYSTEM_PROMPT = """You simplify medical reports for patients.
Use ONLY the source report. Do not use or invent external medical facts.
Preserve findings, negation, uncertainty, severity, laterality, numbers, and units.
Do not infer a diagnosis, cause, prognosis, severity, treatment, or recommendation.
Use clear, calm language and return only the explanation."""

B2_SYSTEM_PROMPT = """You simplify medical reports for patients using the source report and supplied general reference material.
Patient-specific facts, including findings, negation, uncertainty, severity, laterality, numbers, and units, must come only from the source report.
Reference material may explain general medical terms only. It must not establish this patient's diagnosis, cause, prognosis, severity, treatment, or recommendation.
Keep general definitions explicitly general. Use clear, calm language and return only the explanation."""

# B3 uses the same generation instructions as B2 so the verification stage remains
# the only experimental difference between these two conditions.
B3_SYSTEM_PROMPT = B2_SYSTEM_PROMPT


class LLMService:
    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()
        self.active_provider = (
            "vllm"
            if settings.app_mode.lower() == "research"
            and self.provider == "vllm"
            and settings.vllm_model.strip()
            else "demo"
        )
        self.client: OpenAI | None = None
        self._availability_checked_at = 0.0
        self._server_available = False
        if self.active_provider == "vllm":
            self.client = OpenAI(
                base_url=settings.vllm_base_url,
                api_key=settings.vllm_api_key,
                timeout=3.0,
                max_retries=0,
            )

    def local_model_available(self) -> bool:
        if self.active_provider != "vllm" or self.client is None:
            return False
        now = time.monotonic()
        if now - self._availability_checked_at < 5:
            return self._server_available

        self._availability_checked_at = now
        try:
            model_ids = {item.id for item in self.client.models.list().data}
            required_models = {settings.vllm_model, settings.verifier_model or settings.vllm_model}
            self._server_available = required_models.issubset(model_ids)
            if not self._server_available:
                logger.warning("Configured local model is not available; using the demo fallback.")
        except Exception as exc:
            self._server_available = False
            logger.warning(
                "Local OpenAI-compatible model endpoint is unavailable (%s); using the demo fallback.",
                type(exc).__name__,
            )
        return self._server_available

    def generate(
        self,
        report: str,
        evidence: list[dict[str, Any]] | None = None,
        condition: str = "B1",
        mode: str | None = None,
    ) -> str:
        if mode == "demo" or self.active_provider == "demo":
            return self._demo_generate(report, evidence or [])
        if self.active_provider != "vllm" or self.client is None:
            raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")

        uses_retrieval = condition in {"B2", "B3"}
        context = ""
        if uses_retrieval and evidence:
            context = "\n\nPATIENT-ORIENTED REFERENCE MATERIAL (GENERAL EXPLANATIONS ONLY):\n" + "\n\n".join(
                f"- {item.get('title', '')}: {item.get('text', '')}" for item in evidence
            )

        response = self.client.chat.completions.create(
            model=settings.vllm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        B3_SYSTEM_PROMPT if condition == "B3"
                        else B2_SYSTEM_PROMPT if condition == "B2"
                        else DIRECT_SYSTEM_PROMPT
                    ),
                },
                {
                    "role": "user",
                    "content": f"SOURCE MEDICAL REPORT:\n{report}{context}\n\nWrite a patient-oriented simplification.",
                },
            ],
            temperature=0,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _demo_generate(report: str, evidence: list[dict[str, Any]]) -> str:
        """
        Deterministic demo simplification.

        Important:
        - Preserve patient-specific polarity.
        - Never introduce patient-specific facts from retrieval.
        - Keep general retrieved explanations separate.
        """
        text = report.strip()

        replacements = [
            (
                r"\bmild\s+cardiomegaly\b",
                "Your heart appears slightly larger than usual.",
            ),
            (
                r"\bcardiomegaly\b",
                "an enlarged heart",
            ),
            (
                r"\bacute\s+myocardial\s+infarction\s+involving\s+(?:the\s+)?inferior\s+wall\b",
                "a heart attack affecting the lower wall of the heart",
            ),
            (
                r"\bacute\s+myocardial\s+infarction\b",
                "a heart attack",
            ),
            (
                r"\bmyocardial\s+infarction\b",
                "a heart attack",
            ),
            (
                r"\bno\s+evidence\s+of\s+pneumothorax\b",
                "The report does not show a collapsed lung.",
            ),
            (
                r"\bno\s+pneumothorax\b",
                "The report does not show a collapsed lung.",
            ),
            (
                r"\bno\s+pleural\s+effusion\b",
                "The report says there is no fluid around the lungs.",
            ),
            (
                r"\bwithout\s+pleural\s+effusion\b",
                "without fluid around the lungs",
            ),
            (
                r"\bbilateral\s+pleural\s+effusion\b",
                "fluid around both lungs",
            ),
            (
                r"\bpleural\s+effusion\b",
                "fluid around the lungs",
            ),
            (
                r"\bmild\s+left\s+ventricular\s+enlargement\b",
                "mild enlargement of the heart's main pumping chamber",
            ),
            (
                r"\bleft\s+ventricular\s+enlargement\b",
                "enlargement of the heart's main pumping chamber",
            ),
            (
                r"\batelectatic\s+changes\b",
                "areas of the lungs that are not fully expanded",
            ),
            (
                r"\batelectasis\b",
                "an area of the lung that is not fully expanded",
            ),
            (
                r"\bpneumothorax\b",
                "air around the lung",
            ),
        ]

        output = text

        for pattern, replacement in replacements:
            output = re.sub(
                pattern,
                replacement,
                output,
                flags=re.IGNORECASE,
            )

        # Normalize only accidental intra-word whitespace introduced by bad OCR.
        output = re.sub(r"[ \t]+", " ", output)
        output = re.sub(r" +([,.])", r"\1", output)
        output = re.sub(r"\n{3,}", "\n\n", output).strip()

        # For the common report format, keep each clinical statement as its
        # own patient-facing sentence.
        if re.search(r"\bmild\s+cardiomegaly\b", text, re.I):
            lines = ["Your heart appears slightly larger than usual."]

            if re.search(r"\bno\s+pleural\s+effusion\b", text, re.I):
                lines.append("The report says there is no fluid around the lungs.")
            elif re.search(r"\bbilateral\s+pleural\s+effusion\b", text, re.I):
                lines.append("The report describes fluid around both lungs.")

            if re.search(r"\bno\s+(?:evidence\s+of\s+)?pneumothorax\b", text, re.I):
                lines.append("The report does not show a collapsed lung.")

            output = "\n".join(lines)

        if not evidence:
            return output

        explanations: list[str] = []

        for item in evidence:
            title = str(item.get("title") or "").strip()
            explanation = str(item.get("text") or "").strip()

            if not explanation:
                continue

            if title:
                explanations.append(f"{title}: {explanation}")
            else:
                explanations.append(explanation)

        if not explanations:
            return output

        return output + "\n\n" + "\n".join(dict.fromkeys(explanations))


llm_service = LLMService()
