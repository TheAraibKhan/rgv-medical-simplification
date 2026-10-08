from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.schemas.common import Evidence
from app.services.clinical_structure import structure_medical_report

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DemoConcept:
    document_id: str
    title: str
    text: str
    url: str
    aliases: tuple[str, ...]


DEMO_CONCEPTS = (
    DemoConcept(
        document_id="demo-myocardial-infarction",
        title="Heart attack (myocardial infarction)",
        text="A myocardial infarction, commonly called a heart attack, is damage to heart muscle that occurs when blood flow to part of the heart is reduced or blocked. This is general information and does not establish an individual's cause, outlook, or treatment.",
        url="https://medlineplus.gov/heartattack.html",
        aliases=(
            r"\bacute\s+myocardial\s+infarction\b",
            r"\bmyocardial\s+infarction\b",
            r"\bheart\s+attack\b",
            r"\bami\b",
        ),
    ),
    DemoConcept(
        document_id="demo-left-ventricular-enlargement",
        title="Left ventricular enlargement",
        text="The left ventricle is one of the heart's chambers and pumps blood out to the body. Enlargement describes an increase in the size of that chamber; this general definition does not establish its cause or significance for an individual.",
        url="https://medlineplus.gov/search.html?query=left%20ventricular%20enlargement",
        aliases=(
            r"\bleft\s+ventric(?:le|ular)\s+(?:(?:mild|moderate|marked|severe)\s+)?enlarg(?:ement|ed)\b",
            r"\bleft\s+ventricular\s+dilatation\b",
        ),
    ),
    DemoConcept(
        document_id="demo-cardiomegaly",
        title="Cardiomegaly",
        text="Cardiomegaly means that the heart appears larger than usual. This is a general explanation of the term and does not establish why it is present in an individual.",
        url="https://medlineplus.gov/search.html?query=cardiomegaly",
        aliases=(r"\bcardiomegaly\b", r"\benlarged\s+heart\b"),
    ),
    DemoConcept(
        document_id="demo-pleural-effusion",
        title="Pleural effusion",
        text="A pleural effusion is fluid collected in the space between the layers of tissue around the lungs. This is general information and does not establish its cause or significance for an individual.",
        url="https://medlineplus.gov/pleuraldisorders.html",
        aliases=(r"\bpleural\s+effusion\b", r"\bpleural\s+fluid\b"),
    ),
    DemoConcept(
        document_id="demo-pneumothorax",
        title="Pneumothorax",
        text="A pneumothorax is air in the space between a lung and the chest wall, which can cause part or all of a lung to collapse. This is a general explanation and does not establish an individual's severity or treatment.",
        url="https://medlineplus.gov/collapsedlung.html",
        aliases=(r"\bpneumothorax\b", r"\bcollapsed\s+lung\b"),
    ),
    DemoConcept(
        document_id="demo-atelectasis",
        title="Atelectasis",
        text="Atelectasis means that part of a lung is not fully expanded. This is a general explanation of the term and does not establish its cause or significance for an individual.",
        url="https://medlineplus.gov/collapsedlung.html",
        aliases=(r"\batelect(?:asis|atic)\b",),
    ),
)


@dataclass
class LocalDoc:
    document_id: str
    title: str
    text: str
    url: str = ""
    snapshot_date: str = ""


class MedlinePlusRetriever:
    """Simple retriever abstraction.

    The online API method is intentionally separate from the local-index path so that
    experiments can later freeze a dated MedlinePlus snapshot for reproducibility.
    """

    def __init__(self) -> None:
        self.docs: list[LocalDoc] = []
        self.bm25: BM25Okapi | None = None
        self.corpus_error: str | None = None
        self.load_snapshot(settings.medlineplus_corpus_path)

    def add_documents(self, docs: list[LocalDoc]) -> None:
        self.docs.extend(docs)
        tokenized = [self._tokenize(f"{d.title} {d.text}") for d in self.docs]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    def load_snapshot(self, path: Path) -> None:
        if not path.is_file():
            return
        try:
            docs: list[LocalDoc] = []
            with path.open("r", encoding="utf-8") as snapshot:
                for line_number, line in enumerate(snapshot, start=1):
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise ValueError(f"MedlinePlus record on line {line_number} must be a JSON object.")
                    document_id = row.get("document_id") or row.get("id")
                    title = row.get("title")
                    text = row.get("text") or row.get("snippet")
                    if not all(isinstance(value, str) and value.strip() for value in (document_id, title, text)):
                        raise ValueError(f"Invalid MedlinePlus record on line {line_number}.")
                    url = row.get("url", "")
                    snapshot_date = row.get("snapshot_date", settings.medlineplus_snapshot_date)
                    if not isinstance(url, str) or not isinstance(snapshot_date, str):
                        raise ValueError(f"Invalid MedlinePlus metadata on line {line_number}.")
                    docs.append(
                        LocalDoc(
                            document_id=document_id,
                            title=title,
                            text=text,
                            url=url,
                            snapshot_date=snapshot_date,
                        )
                    )
            self.docs = []
            self.bm25 = None
            self.add_documents(docs)
            logger.info("Loaded local MedlinePlus snapshot with %d documents", len(docs))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.corpus_error = str(exc)
            logger.error("Unable to load local MedlinePlus snapshot: %s", exc)

    def local_search(self, report: str, top_k: int = 3) -> list[Evidence]:
        if not self.docs or self.bm25 is None:
            return []
        structured = structure_medical_report(report)
        query_terms = self._tokenize(" ".join(structured.retrieval_queries))
        if not query_terms:
            return []
        scores = self.bm25.get_scores(query_terms)
        ranked = [
            i
            for i in sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
            if scores[i] > 0
        ][:top_k]
        return [
            Evidence(
                source="MedlinePlus",
                title=self.docs[i].title,
                text=self.docs[i].text,
                url=self.docs[i].url,
                score=float(scores[i]),
                document_id=self.docs[i].document_id,
                snapshot_date=self.docs[i].snapshot_date or settings.medlineplus_snapshot_date or None,
            )
            for i in ranked
        ]

    def demo_search(self, report: str, top_k: int = 3) -> list[Evidence]:
        """Retrieve only demo definitions whose concepts occur positively in the report."""
        if top_k < 1:
            return []

        structured = structure_medical_report(report)
        eligible_source = " ".join(structured.retrieval_queries)
        if not eligible_source:
            return []

        matches: list[tuple[int, DemoConcept]] = []
        for concept in DEMO_CONCEPTS:
            positions = [
                match.start()
                for alias in concept.aliases
                for match in re.finditer(alias, eligible_source, flags=re.IGNORECASE)
                if not self._is_negated(eligible_source, match.start())
            ]
            if positions:
                matches.append((min(positions), concept))

        matches.sort(key=lambda item: (item[0], DEMO_CONCEPTS.index(item[1])))
        return [
            Evidence(
                source="MedlinePlus (demo fixture)",
                title=concept.title,
                text=concept.text,
                url=concept.url,
                score=0.0,
                document_id=concept.document_id,
                snapshot_date="demo",
            )
            for _, concept in matches[:top_k]
        ]

    @staticmethod
    def _is_negated(report: str, match_start: int) -> bool:
        clause_start = max(
            report.rfind(mark, 0, match_start)
            for mark in (".", "!", "?", ";", "\n")
        ) + 1
        prefix = report[clause_start:match_start]
        prefix = re.split(
            r",|\b(?:but|however|although|whereas|with)\b",
            prefix,
            flags=re.IGNORECASE,
        )[-1]
        return bool(
            re.search(
                r"\b(?:no|not|without|absent|negative\s+for|free\s+of|rule\s+out)\b",
                prefix,
                flags=re.IGNORECASE,
            )
        )

    async def web_search(self, term: str, top_k: int = 3) -> list[Evidence]:
        """Optional pilot-only adapter for the official MedlinePlus web service.

        Do not use this live endpoint as the final evaluation corpus without storing
        the returned content and retrieval date/snapshot metadata.
        """
        url = "https://wsearch.nlm.nih.gov/ws/query"
        params = {"db": "healthTopics", "term": term, "retmax": str(top_k)}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            xml = response.text
        return self._parse_nlm_xml(xml, top_k)

    @staticmethod
    def _parse_nlm_xml(xml: str, top_k: int) -> list[Evidence]:
        # Lightweight parser for pilot tooling; local snapshot ingestion is preferred.
        docs: list[Evidence] = []
        blocks = re.findall(r"<document>(.*?)</document>", xml, flags=re.S | re.I)
        for block in blocks[:top_k]:
            title = re.search(r"<content name=\"title\">(.*?)</content>", block, flags=re.S | re.I)
            snippet = re.search(r"<content name=\"snippet\">(.*?)</content>", block, flags=re.S | re.I)
            url = re.search(r"<url>(.*?)</url>", block, flags=re.S | re.I)
            docs.append(
                Evidence(
                    source="MedlinePlus",
                    title=re.sub(r"<.*?>", "", title.group(1)).strip() if title else "",
                    text=re.sub(r"<.*?>", "", snippet.group(1)).strip() if snippet else "",
                    url=url.group(1).strip() if url else None,
                    score=0.0,
                )
            )
        return docs

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        ignored = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
            "in", "is", "it", "mild", "moderate", "of", "on", "or", "report",
            "the", "this", "to", "was", "were", "with", "without", "no", "not",
            "evidence", "there", "within", "normal", "limits", "show", "shows",
        }
        return [token for token in tokens if token not in ignored]

    @staticmethod
    def _positive_report_text(report: str) -> str:
        positive_clauses: list[str] = []
        for sentence in re.split(r"(?<=[.!?;])\s+|\n+", report):
            for clause in re.split(r",|\b(?:but|however|although|whereas|with)\b", sentence, flags=re.IGNORECASE):
                clause = clause.strip()
                if not clause:
                    continue
                if re.match(
                    r"^(?:no|not|without|absent|negative\s+for|free\s+of|rule\s+out)\b",
                    clause,
                    flags=re.IGNORECASE,
                ):
                    continue
                positive_clauses.append(clause)
        return " ".join(positive_clauses)

    @staticmethod
    def report_findings(report: str) -> list[dict[str, str]]:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", report) if part.strip()]
        excerpts = [
            part.strip()
            for sentence in sentences
            for part in re.split(r"\s+with\s+", sentence, flags=re.IGNORECASE)
            if part.strip()
        ]
        findings: list[dict[str, str]] = []
        for excerpt in excerpts:
            text = excerpt.strip()
            findings.append(
                {
                    "text": text,
                    "polarity": "NEGATED" if re.search(
                        r"\b(?:no|not|without|absent|negative\s+for|free\s+of)\b",
                        text,
                        flags=re.IGNORECASE,
                    ) else "AFFIRMED",
                }
            )
        return findings


retriever = MedlinePlusRetriever()
