from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.common import (
    ExcludedReportItem,
    ReportReference,
    ReportSection,
    ReportSectionType,
    SourceSpan,
    StructuredFinding,
    StructuredMedicalReport,
    StructuredPendingStatus,
    StructuredTestResult,
)


@dataclass(frozen=True)
class _Line:
    text: str
    start: int
    end: int
    section: ReportSectionType
    test: tuple[str, str | None, str | None] | None = None
    page: int | None = None
    source_name: str | None = None
    source_text: str | None = None

    @property
    def span(self) -> SourceSpan:
        return SourceSpan(start=self.start, end=self.end, page=self.page)


_SECTION_HEADINGS: tuple[tuple[re.Pattern[str], ReportSectionType], ...] = (
    (re.compile(r"^(?:test\s+)?results?(?:\s*/\s*findings?)?$", re.I), ReportSectionType.TEST_RESULT),
    (re.compile(r"^(?:reference\s+)?(?:interval|range)s?$", re.I), ReportSectionType.REFERENCE_INTERVAL),
    (re.compile(r"^(?:biological\s+)?reference\s+(?:interval|range)s?$", re.I), ReportSectionType.REFERENCE_INTERVAL),
    (re.compile(r"^(?:(?:lab|laboratory)\s+)?comments?$", re.I), ReportSectionType.COMMENT),
    (re.compile(r"^(?:clinical\s+)?interpretation$", re.I), ReportSectionType.INTERPRETATION),
    (re.compile(r"^(?:general\s+)?information$", re.I), ReportSectionType.GENERAL_INFORMATION),
    (re.compile(r"^(?:risk|cardiovascular\s+risk)(?:\s+information|\s+guidance)?$", re.I), ReportSectionType.RISK_GUIDANCE),
    (re.compile(r"^(?:treatment|management)\s+(?:guidance|recommendations?)$", re.I), ReportSectionType.TREATMENT_GUIDANCE),
    (re.compile(r"^(?:references|bibliography|citation)s?$", re.I), ReportSectionType.REFERENCE),
    (re.compile(r"^(?:instructions|patient\s+instructions)$", re.I), ReportSectionType.INSTRUCTION),
    (re.compile(r"^(?:notes?|remarks?)$", re.I), ReportSectionType.NOTE),
    (re.compile(r"^(?:patient|test|investigation)\s+(?:details|information|profile)$", re.I), ReportSectionType.PATIENT_METADATA),
    (re.compile(r"^(?:test|investigation)\s+name$", re.I), ReportSectionType.TEST_HEADER),
)

_TEST_ALIASES: tuple[tuple[str, str, str | None, re.Pattern[str]], ...] = (
    ("Apolipoprotein B", "ApoB", "ApoB", re.compile(r"\b(?:apolipoprotein\s*b|apo\s*b|apob)\b", re.I)),
    ("High-sensitivity C-reactive protein", "hsCRP", "hsCRP", re.compile(r"\b(?:cardio\s+c[- ]reactive\s+protein|high[- ]sensitivity\s+c[- ]reactive\s+protein|hs[- ]?crp)\b", re.I)),
    ("Lipoprotein(a)", "Lp(a)", "Lp(a)", re.compile(r"\b(?:lipoprotein\s*\(\s*a\s*\)|lp\s*\(\s*a\s*\))", re.I)),
    ("High-sensitivity Troponin-I", "hs-Troponin I", None, re.compile(r"\b(?:high[- ]sensitivity\s+)?troponin\s*[- ]?\s*i\b", re.I)),
    ("Hemoglobin A1c", "HbA1c", "HbA1c", re.compile(r"\b(?:hemoglobin\s*a1c|hba1c)\b", re.I)),
    ("Estimated average glucose", "eAG", "eAG", re.compile(r"\b(?:estimated\s+average\s+glucose|eag)\b", re.I)),
    ("Fasting glucose", "Fasting glucose", None, re.compile(r"\b(?:fasting\s+glucose|glucose\s*,?\s*fasting|glucose\s*\(\s*fasting\s*\))\b", re.I)),
    ("Lipid profile", "Lipid profile", None, re.compile(r"\b(?:lipid\s+(?:profile|panel))\b", re.I)),
    ("Glucose", "Glucose", None, re.compile(r"\bglucose\b", re.I)),
    ("Total cholesterol", "Total cholesterol", None, re.compile(r"\btotal\s+cholesterol\b", re.I)),
    ("Triglycerides", "Triglycerides", None, re.compile(r"\btriglycerides?\b", re.I)),
    ("HDL cholesterol", "HDL cholesterol", "HDL", re.compile(r"\b(?:hdl(?:\s+cholesterol)?|high[- ]density\s+lipoprotein)\b", re.I)),
    ("LDL cholesterol", "LDL cholesterol", "LDL", re.compile(r"\b(?:ldl(?:\s+cholesterol)?|low[- ]density\s+lipoprotein)\b", re.I)),
    ("Non-HDL cholesterol", "Non-HDL cholesterol", None, re.compile(r"\bnon[- ]hdl(?:\s+cholesterol)?\b", re.I)),
    ("VLDL cholesterol", "VLDL cholesterol", "VLDL", re.compile(r"\b(?:vldl(?:\s+cholesterol)?|very[- ]low[- ]density\s+lipoprotein)\b", re.I)),
)

_CLINICAL_CONCEPTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("myocardial infarction", re.compile(r"\b(?:myocardial infarction|heart attack)\b", re.I)),
    ("cardiomegaly", re.compile(r"\b(?:cardiomegaly|enlarged heart)\b", re.I)),
    ("left ventricular enlargement", re.compile(r"\bleft\s+ventric(?:le|ular)\s+(?:(?:mild|moderate|marked|severe)\s+)?enlarg(?:ement|ed)\b", re.I)),
    ("pleural effusion", re.compile(r"\b(?:pleural effusion|pleural fluid)\b", re.I)),
    ("pneumothorax", re.compile(r"\b(?:pneumothorax|collapsed lung)\b", re.I)),
    ("atelectasis", re.compile(r"\b(?:atelectasis|atelectatic)\b", re.I)),
)

_VALUE_RE = re.compile(
    r"(?P<value>(?:[<>≤≥]\s*)?\d+(?:[.,]\d+)?)"
    r"(?:\s*(?P<unit>%|mg\s*/\s*dL|mg\s*/\s*L|ng\s*/\s*L|ng\s*/\s*mL|"
    r"µg\s*/\s*L|ug\s*/\s*L|g\s*/\s*dL|mmol\s*/\s*L|µmol\s*/\s*L|"
    r"U\s*/\s*L|mIU\s*/\s*L|pg\s*/\s*mL))?",
    re.I,
)
_REFERENCE_RE = re.compile(
    r"(?:reference(?:\s+range|\s+interval)?|normal\s+range|ref\.?)\s*[:=]?\s*(.+)$|"
    r"\(\s*((?:[<>≤≥]\s*)?\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?(?:\s*[a-zµ%/]+)?)\s*\)",
    re.I,
)
_PLAIN_REFERENCE_RE = re.compile(
    r"^\s*((?:[<>≤≥]\s*)?\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?(?:\s*[a-zµ%/]+)?)\s*$",
    re.I,
)
_PENDING_RE = re.compile(r"\b(?:result(?:s|/s)?\s+to\s+follow|pending|awaited|not\s+available)\b", re.I)
_ADMIN_RE = re.compile(r"\b(?:contact|customer\s+care|helpline|call\s+us|website|printed\s+by|page\s+\d+\s+of\s+\d+)\b", re.I)
_PATIENT_METADATA_RE = re.compile(
    r"^\s*(?:patient\s+name|name|age|sex|gender|lab(?:oratory)?\s*(?:id|number|no\.?)|"
    r"accession\s*(?:id|number|no\.?)|referring\s+doctor|collection\s+date|"
    r"collected\s+at|specimen\s*(?:id|type))\s*[:=]",
    re.I,
)
_NON_RESULT_FRAGMENT_RE = re.compile(
    r"\b(?:any condition that shortens erythrocyte|test results released|"
    r"sample collected|specimen received|methodology|important instructions?)\b",
    re.I,
)
_GENERAL_CONTEXT_RE = re.compile(
    r"\b(?:associated\s+with|future\s+risk|risk\s+of|for\s+example|example\s+of|"
    r"discussed\s+as|may\s+increase\s+the\s+risk|can\s+increase\s+the\s+risk)\b",
    re.I,
)
_INTERPRETATION_GENERAL_RE = re.compile(
    r"\b(?:is\s+a|are\s+a|means|refers\s+to|occurs\s+when|can\s+cause|"
    r"may\s+cause|associated\s+with|for\s+example|example\s+of)\b",
    re.I,
)
_REFERENCE_RE_LINE = re.compile(r"^\s*(?:\[\d+\]|\d+\.\s+https?://|https?://|doi\s*:)", re.I)
_FLAG_RE = re.compile(r"\b(H|L|HIGH|LOW|ABNORMAL|CRITICAL)\b\s*$", re.I)
_TEST_RESULT_RE = re.compile(
    r"^\s*(?P<name>.+?)\s*(?:[:=]|\t|\s{2,}|\s+\|\s*)\s*"
    r"(?P<value>(?:[<>≤≥]\s*)?\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>%|mg\s*/\s*dL|mg\s*/\s*L|ng\s*/\s*L|ng\s*/\s*mL|µg\s*/\s*L|ug\s*/\s*L|g\s*/\s*dL|mmol\s*/\s*L|µmol\s*/\s*L|U\s*/\s*L|mIU\s*/\s*L|pg\s*/\s*mL)?"
    r"(?P<tail>.*)$",
    re.I,
)
_PENDING_TEST_ROW_RE = re.compile(
    r"^\s*(?P<name>.+?)\s*(?:[:=]|\t|\s{2,}|\s+\|\s*)\s*"
    r"(?:result(?:s|/s)?\s+to\s+follow|pending|awaited|not\s+available)\b.*$",
    re.I,
)
_REFERENCE_VALUE_RE = re.compile(
    r"(?P<interval>(?:[<>≤≥]\s*)?\d+(?:[.,]\d+)?"
    r"(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?(?:\s*[a-zµ%/]+)?)\s*$",
    re.I,
)
_TABLE_RESULT_RE = re.compile(
    r"^\s*(?P<name>[^|]+?)\s*\|\s*(?P<value>[^|]*)\s*\|\s*"
    r"(?P<unit>[^|]*)\s*(?:\|\s*(?P<tail>.*))?$"
)
_SPACE_TABLE_SPLIT_RE = re.compile(r"\t+|\s{2,}")


def _classify_heading(text: str) -> ReportSectionType | None:
    heading = text.strip().strip(" :.-")
    if _is_table_header(heading):
        return ReportSectionType.TEST_HEADER
    for pattern, section in _SECTION_HEADINGS:
        if pattern.match(heading):
            return section
    return None


def _lookup_text(name: str) -> str:
    text = name.replace("|", " I ")
    text = re.sub(r"\bmg\s*[lI1]\s*L\b", "mg/L", text, flags=re.I)
    text = re.sub(r"\btroponin\s*-\s*i\b", "troponin-i", text, flags=re.I)
    text = re.sub(r"\bc\s+reactive\b", "c-reactive", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _canonical_test(name: str) -> tuple[str, str | None, str | None]:
    lookup = _lookup_text(name)
    for canonical, short_name, abbreviation, pattern in _TEST_ALIASES:
        if pattern.search(lookup):
            return canonical, short_name, abbreviation
    return name.strip(" :|-\t"), None, None


def _is_known_test_name(name: str) -> bool:
    lookup = _lookup_text(name)
    return any(pattern.search(lookup) for _, _, _, pattern in _TEST_ALIASES)


def _table_cells(text: str) -> list[str]:
    table_text = re.sub(r"(troponin\s*-\s*)\|", r"\1 I ", text, flags=re.I)
    if "|" in table_text:
        return [cell.strip() for cell in table_text.strip().strip("|").split("|")]
    return [cell.strip() for cell in _SPACE_TABLE_SPLIT_RE.split(table_text.strip()) if cell.strip()]


def _table_result_parts(text: str) -> tuple[str, str, str | None, str] | None:
    cells = _table_cells(text)
    if len(cells) < 2:
        return None

    source_name = cells[0].strip(" :|-\t")
    if not _is_known_test_name(source_name):
        for index in range(1, min(len(cells), 4)):
            candidate = " ".join(cells[: index + 1]).strip(" :|-\t")
            if _is_known_test_name(candidate):
                source_name = candidate
                cells = [candidate] + cells[index + 1:]
                break
    if not _is_known_test_name(source_name):
        return None

    raw_value = cells[1].strip() if len(cells) > 1 else ""
    unit: str | None = None
    tail_parts: list[str] = []

    if len(cells) >= 3:
        unit = cells[2].strip().replace("mglL", "mg/L").replace("mgIL", "mg/L") or None
        tail_parts = cells[3:]
    else:
        value_match = _VALUE_RE.fullmatch(raw_value)
        if value_match:
            raw_value = value_match.group("value").strip()
            unit = re.sub(r"\s+", "", value_match.group("unit") or "") or None

    if unit and not re.fullmatch(
        r"%|mg\s*/\s*dL|mg\s*/\s*L|ng\s*/\s*L|ng\s*/\s*mL|"
        r"Âµg\s*/\s*L|ug\s*/\s*L|g\s*/\s*dL|mmol\s*/\s*L|Âµmol\s*/\s*L|"
        r"U\s*/\s*L|mIU\s*/\s*L|pg\s*/\s*mL",
        unit,
        re.I,
    ):
        tail_parts.insert(0, unit)
        unit = None

    return source_name, raw_value, unit, " ".join(part for part in tail_parts if part).strip()


def _pending_status_header(text: str) -> bool:
    return bool(re.match(
        r"^\s*(?:result(?:s|/s)?\s+to\s+follow|pending\s+results?)\b",
        text,
        re.I,
    ))


def _is_table_header(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return (
        "test name" in normalized
        and "result" in normalized
        and ("unit" in normalized or "reference" in normalized)
    )


def _is_blocked_test_section(section: ReportSectionType) -> bool:
    return section in {
        ReportSectionType.REFERENCE,
        ReportSectionType.COMMENT,
        ReportSectionType.NOTE,
        ReportSectionType.INTERPRETATION,
        ReportSectionType.GENERAL_INFORMATION,
        ReportSectionType.RISK_GUIDANCE,
        ReportSectionType.TREATMENT_GUIDANCE,
        ReportSectionType.INSTRUCTION,
        ReportSectionType.PENDING_STATUS,
        ReportSectionType.ADMINISTRATIVE,
        ReportSectionType.PATIENT_METADATA,
        ReportSectionType.HEADER,
        ReportSectionType.FOOTER,
    }


def _is_ocr_artifact(text: str) -> bool:
    compact = text.strip()
    return bool(
        re.fullmatch(r"\d+(?:\s+\d+){2,}", compact)
        or re.search(r"\b(\S{1,4})(?:\s+\1){2,}\b", compact, re.I)
        or _NON_RESULT_FRAGMENT_RE.search(compact)
    )


def _known_test_row(text: str) -> bool:
    if _table_result_parts(text) is not None:
        return True
    table_match = _TABLE_RESULT_RE.match(text)
    if table_match and _is_known_test_name(table_match.group("name")):
        return True
    result_match = _TEST_RESULT_RE.match(text)
    if result_match and _is_known_test_name(result_match.group("name")):
        return True
    return False


def _line_records(raw_text: str) -> list[_Line]:
    lines: list[_Line] = []
    section = ReportSectionType.UNKNOWN
    offset = 0
    pending_test: tuple[str, str | None, str | None] | None = None
    pending_test_line: _Line | None = None
    page = 1 if "\f" in raw_text else None

    for raw_line in raw_text.splitlines(keepends=True):
        text = raw_line.rstrip("\r\n")
        start = offset
        end = start + len(text)
        offset += len(raw_line)

        if "\f" in text:
            if page is not None:
                page += text.count("\f")
            section = ReportSectionType.UNKNOWN
            pending_test = None
            pending_test_line = None
            continue
        if not text.strip():
            continue

        if _pending_status_header(text):
            section = ReportSectionType.PENDING_STATUS
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue

        heading = _classify_heading(text)
        if heading is None and _is_table_header(text):
            heading = ReportSectionType.TEST_HEADER
        if heading is not None:
            section = heading
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, heading, page=page))
            continue

        if re.match(r"^\s*page\s+\d+\s+(?:of|/)\s+\d+\s*$", text, re.I):
            section = ReportSectionType.FOOTER
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue
        if _ADMIN_RE.search(text):
            section = ReportSectionType.ADMINISTRATIVE
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue
        if _REFERENCE_RE_LINE.search(text):
            section = ReportSectionType.REFERENCE
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue
        if _PATIENT_METADATA_RE.search(text):
            lines.append(_Line(text, start, end, ReportSectionType.PATIENT_METADATA, page=page))
            continue

        if section == ReportSectionType.REFERENCE_INTERVAL:
            lines.append(_Line(text, start, end, section, page=page))
            continue

        if _is_blocked_test_section(section):
            pending_test = None
            pending_test_line = None
            if _GENERAL_CONTEXT_RE.search(text) and section in {
                ReportSectionType.INTERPRETATION,
                ReportSectionType.GENERAL_INFORMATION,
                ReportSectionType.UNKNOWN,
            }:
                context_section = (
                    ReportSectionType.RISK_GUIDANCE
                    if re.search(r"\b(?:risk|future)\b", text, re.I)
                    else ReportSectionType.GENERAL_INFORMATION
                )
                lines.append(_Line(text, start, end, context_section, page=page))
            else:
                lines.append(_Line(text, start, end, section, page=page))
            continue

        if (
            section in {ReportSectionType.UNKNOWN, ReportSectionType.TEST_HEADER, ReportSectionType.TEST_RESULT}
            and _is_known_test_name(text.strip())
            and not re.search(r"[=:|]", text)
            and not _known_test_row(text)
        ):
            pending_test = _canonical_test(text.strip())
            section = ReportSectionType.TEST_HEADER
            pending_test_line = _Line(
                text,
                start,
                end,
                ReportSectionType.TEST_HEADER,
                pending_test,
                page,
                text.strip(),
            )
            lines.append(pending_test_line)
            continue

        pending_row = _PENDING_TEST_ROW_RE.match(text)
        if pending_row and _is_known_test_name(pending_row.group("name")):
            section = ReportSectionType.TEST_RESULT
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue

        if pending_test is not None and _VALUE_RE.fullmatch(text.strip()):
            section = ReportSectionType.TEST_RESULT
            source_start = pending_test_line.start if pending_test_line else start
            source_name = pending_test_line.source_name if pending_test_line else pending_test[0]
            lines.append(_Line(
                text,
                source_start,
                end,
                section,
                pending_test,
                page,
                source_name,
                raw_text[source_start:end],
            ))
            pending_test = None
            pending_test_line = None
            continue

        if _known_test_row(text):
            section = ReportSectionType.TEST_RESULT
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue

        if _is_ocr_artifact(text):
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, ReportSectionType.UNKNOWN, page=page))
            continue

        if section == ReportSectionType.TEST_RESULT:
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue

        if _GENERAL_CONTEXT_RE.search(text) and section in {
            ReportSectionType.COMMENT,
            ReportSectionType.GENERAL_INFORMATION,
            ReportSectionType.INTERPRETATION,
            ReportSectionType.UNKNOWN,
        }:
            context_section = (
                ReportSectionType.COMMENT
                if section == ReportSectionType.COMMENT
                else ReportSectionType.RISK_GUIDANCE
                if re.search(r"\b(?:risk|future)\b", text, re.I)
                else ReportSectionType.GENERAL_INFORMATION
            )
            section = context_section
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, context_section, page=page))
            continue
        if section == ReportSectionType.UNKNOWN and _has_clinical_concept(text):
            section = ReportSectionType.FINDING
            pending_test = None
            pending_test_line = None
            lines.append(_Line(text, start, end, section, page=page))
            continue
        pending_test = None
        pending_test_line = None
        lines.append(_Line(text, start, end, section, page=page))
    return lines


def _has_clinical_concept(text: str) -> bool:
    return any(pattern.search(text) for _, pattern in _CLINICAL_CONCEPTS)


def _strip_reference_unit(reference: str, unit: str | None) -> str:
    if not unit:
        return reference.strip()
    unit_pattern = re.compile(rf"\s*{re.escape(unit)}\s*$", re.I)
    return unit_pattern.sub("", reference).strip()


def _reference_interval(tail: str, unit: str | None = None) -> str | None:
    match = _REFERENCE_RE.search(tail.strip())
    value = next((part for part in match.groups() if part), None) if match else None
    if value is None:
        plain_match = _PLAIN_REFERENCE_RE.match(tail.strip())
        value = plain_match.group(1) if plain_match else None
    return _strip_reference_unit(value.strip(" ()"), unit) if value else None


def _result_from_line(line: _Line) -> StructuredTestResult | None:
    if line.section != ReportSectionType.TEST_RESULT or _pending_status_header(line.text):
        return None

    if line.test is not None:
        test_name, short_name, abbreviation = line.test
        value_match = _VALUE_RE.fullmatch(line.text.strip())
        value = value_match.group("value").strip() if value_match else None
        unit = re.sub(r"\s+", "", value_match.group("unit") or "") or None if value_match else None
        source_name = line.source_name or test_name
        return StructuredTestResult(
            test_name=test_name,
            canonical_name=test_name,
            source_name=source_name,
            short_name=short_name,
            abbreviation=abbreviation,
            value=value,
            unit=unit,
            status="reported" if value else "not_available",
            section=line.section,
            source_section=line.section,
            patient_specific=True,
            retrieval_eligible=value is not None,
            explanation_eligible=True,
            source_text=line.source_text or line.text,
            source_page=line.page,
            source_span=line.span,
        )

    table_parts = _table_result_parts(line.text)
    if table_parts is not None:
        source_name, raw_value, raw_unit, tail = table_parts
        canonical, short_name, abbreviation = _canonical_test(source_name)
        pending = bool(_PENDING_TEST_ROW_RE.match(line.text))
        value_match = _VALUE_RE.search(raw_value)
        unit = re.sub(r"\s+", "", raw_unit or value_match.group("unit") or "") or None if value_match else raw_unit
        value = value_match.group("value").strip() if value_match and not pending else None
        flag_match = _FLAG_RE.search(tail)
        return StructuredTestResult(
            test_name=canonical,
            canonical_name=canonical,
            source_name=source_name,
            short_name=short_name,
            abbreviation=abbreviation,
            value=value,
            unit=unit,
            reference_interval=_reference_interval(tail, unit),
            flag=flag_match.group(1).upper() if flag_match else None,
            status="pending" if pending else "reported" if value else "not_available",
            section=ReportSectionType.TEST_RESULT,
            source_section=line.section,
            patient_specific=True,
            retrieval_eligible=value is not None and not pending,
            explanation_eligible=True,
            source_text=line.source_text or line.text,
            source_page=line.page,
            source_span=line.span,
        )

    pending_match = _PENDING_TEST_ROW_RE.match(line.text)
    if pending_match:
        source_name = pending_match.group("name").strip(" :|-\t")
        if not _is_known_test_name(source_name):
            return None
        canonical, short_name, abbreviation = _canonical_test(source_name)
        return StructuredTestResult(
            test_name=canonical,
            canonical_name=canonical,
            source_name=source_name,
            short_name=short_name,
            abbreviation=abbreviation,
            status="pending",
            section=ReportSectionType.TEST_RESULT,
            source_section=line.section,
            patient_specific=True,
            retrieval_eligible=False,
            explanation_eligible=True,
            source_text=line.source_text or line.text,
            source_page=line.page,
            source_span=line.span,
        )

    match = _TEST_RESULT_RE.match(line.text)
    if not match:
        return None
    source_name = (line.source_name or match.group("name")).strip(" :|-\t")
    canonical, short_name, abbreviation = _canonical_test(source_name)
    if not _is_known_test_name(source_name):
        return None
    value = match.group("value").strip() if match.group("value") else None
    unit = re.sub(r"\s+", "", match.group("unit") or "") or None
    tail = match.group("tail") or ""
    flag_match = _FLAG_RE.search(tail)
    flag = flag_match.group(1).upper() if flag_match else None
    status = "reported" if value else "not_available"
    return StructuredTestResult(
        test_name=canonical,
        canonical_name=canonical,
        source_name=source_name,
        short_name=short_name,
        abbreviation=abbreviation,
        value=value,
        unit=unit,
        reference_interval=_reference_interval(tail, unit),
        flag=flag,
        status=status,
        section=ReportSectionType.TEST_RESULT,
        source_section=line.section,
        patient_specific=True,
        retrieval_eligible=value is not None,
        explanation_eligible=True,
        source_text=line.source_text or line.text,
        source_page=line.page,
        source_span=line.span,
    )


def _reference_result_from_line(line: _Line) -> StructuredTestResult | None:
    if line.section != ReportSectionType.REFERENCE_INTERVAL:
        return None

    matches = [
        (match.start(), match.end(), canonical, short_name, abbreviation)
        for canonical, short_name, abbreviation, pattern in _TEST_ALIASES
        for match in pattern.finditer(line.text)
    ]
    if not matches:
        return None
    test_start, test_end, canonical, short_name, abbreviation = max(
        matches,
        key=lambda item: (item[1] - item[0], -item[0]),
    )
    interval_match = _REFERENCE_VALUE_RE.search(line.text[test_end:])
    if not interval_match:
        return None
    interval = interval_match.group("interval").strip()
    source_name = line.text[:test_end + interval_match.start()].strip(" |:\t")
    return StructuredTestResult(
        test_name=canonical,
        canonical_name=canonical,
        source_name=source_name or line.text[:test_end].strip(),
        short_name=short_name,
        abbreviation=abbreviation,
        reference_interval=interval,
        status="not_available",
        section=ReportSectionType.REFERENCE_INTERVAL,
        source_section=line.section,
        patient_specific=True,
        retrieval_eligible=False,
        explanation_eligible=True,
        source_text=line.source_text or line.text,
        source_page=line.page,
        source_span=line.span,
    )


def _pending_test_names(text: str) -> list[tuple[str, str | None, str | None, str]]:
    content = re.sub(
        r"^\s*(?:result(?:s|/s)?\s+to\s+follow|pending\s+results?)\s*:?\s*",
        "",
        text,
        flags=re.I,
    )
    matches = sorted(
        (
            match.start(),
            match.end(),
            canonical,
            short_name,
            abbreviation,
            match.group(0),
        )
        for canonical, short_name, abbreviation, pattern in _TEST_ALIASES
        for match in pattern.finditer(content)
    )
    selected: list[tuple[str, str | None, str | None, str]] = []
    occupied_until = -1
    selected_names: set[str] = set()
    for start, end, canonical, short_name, abbreviation, source_name in sorted(
        matches,
        key=lambda item: (item[0], -(item[1] - item[0])),
    ):
        if start < occupied_until or canonical in selected_names:
            continue
        selected.append((canonical, short_name, abbreviation, source_name))
        selected_names.add(canonical)
        occupied_until = end
    return selected


def _result_priority(result: StructuredTestResult) -> int:
    if result.status == "reported" and result.value:
        return 3
    if result.status == "pending":
        return 2
    if result.reference_interval:
        return 1
    return 0


def _register_result(
    result: StructuredTestResult,
    by_name: dict[str, StructuredTestResult],
    excluded_items: list[ExcludedReportItem],
) -> None:
    key = result.canonical_name or result.test_name
    existing = by_name.get(key)
    if existing is None:
        by_name[key] = result
        return
    if existing.status == "needs_review":
        excluded_items.append(ExcludedReportItem(
            source_text=result.source_text,
            section=result.source_section or result.section,
            reason="CONFLICTING_DUPLICATE",
            source_page=result.source_page,
            source_span=result.source_span,
        ))
        return

    existing_priority = _result_priority(existing)
    new_priority = _result_priority(result)
    same_measurement = (
        existing.value == result.value
        and (existing.unit or "").casefold() == (result.unit or "").casefold()
    )
    if existing.value and result.value and not same_measurement:
        by_name[key] = existing.model_copy(update={
            "value": None,
            "unit": None,
            "status": "needs_review",
            "retrieval_eligible": False,
            "explanation_eligible": False,
        })
        excluded_items.append(ExcludedReportItem(
            source_text=result.source_text,
            section=result.source_section or result.section,
            reason="CONFLICTING_DUPLICATE",
            source_page=result.source_page,
            source_span=result.source_span,
        ))
        return

    if new_priority > existing_priority:
        selected = result
        if selected.reference_interval is None:
            selected = selected.model_copy(update={
                "reference_interval": existing.reference_interval,
            })
        by_name[key] = selected
        excluded_items.append(ExcludedReportItem(
            source_text=existing.source_text,
            section=existing.source_section or existing.section,
            reason="SUPERSEDED_BY_HIGHER_PRIORITY_RESULT",
            source_page=existing.source_page,
            source_span=existing.source_span,
        ))
    else:
        if existing.reference_interval is None and result.reference_interval:
            by_name[key] = existing.model_copy(update={
                "reference_interval": result.reference_interval,
            })
        excluded_items.append(ExcludedReportItem(
            source_text=result.source_text,
            section=result.source_section or result.section,
            reason="DUPLICATE" if same_measurement else "LOWER_PRIORITY_OCCURRENCE",
            source_page=result.source_page,
            source_span=result.source_span,
        ))


def _findings_from_line(line: _Line) -> list[StructuredFinding]:
    if line.section not in {ReportSectionType.FINDING, ReportSectionType.INTERPRETATION}:
        return []
    if line.section == ReportSectionType.INTERPRETATION and _INTERPRETATION_GENERAL_RE.search(line.text):
        return []
    if _TEST_RESULT_RE.match(line.text) or _PENDING_RE.search(line.text):
        return []

    findings: list[StructuredFinding] = []
    sentence_matches = list(re.finditer(r"[^.!?]+[.!?]?|$", line.text))
    for sentence_match in sentence_matches:
        sentence = sentence_match.group(0)
        if not sentence.strip():
            continue
        segments = list(re.finditer(r"[^,;]+", sentence))
        for segment_match in segments:
            excerpt = segment_match.group(0)
            concepts = [name for name, pattern in _CLINICAL_CONCEPTS if pattern.search(excerpt)]
            if not concepts:
                continue
            negated = bool(re.search(
                r"\b(?:no|not|without|absent|negative\s+for|free\s+of)\b",
                excerpt,
                re.I,
            ))
            start = line.start + sentence_match.start() + segment_match.start()
            end = start + len(excerpt)
            findings.append(StructuredFinding(
                concept=", ".join(concepts),
                text=excerpt.strip(),
                section=line.section,
                patient_specific=True,
                negated=negated,
                retrieval_eligible=not negated,
                explanation_eligible=True,
                source_text=excerpt,
                source_page=line.page,
                source_span=SourceSpan(start=start, end=end, page=line.page),
            ))
    return findings


def structure_medical_report(raw_text: str) -> StructuredMedicalReport:
    """Create a provenance-preserving report representation before retrieval."""
    lines = _line_records(raw_text)
    sections = [
        ReportSection(section=line.section, text=line.text, source_span=line.span)
        for line in lines
    ]

    results_by_name: dict[str, StructuredTestResult] = {}
    findings: list[StructuredFinding] = []
    general_information: list[StructuredFinding] = []
    excluded_items: list[ExcludedReportItem] = []
    references: list[ReportReference] = []
    pending_status_lines: list[tuple[_Line, list[tuple[str, str | None, str | None, str]]]] = []

    for line_index, line in enumerate(lines):
        source_text = line.source_text or line.text
        if _classify_heading(line.text) is not None:
            continue
        if (
            line.section == ReportSectionType.TEST_HEADER
            and line_index + 1 < len(lines)
            and lines[line_index + 1].test is not None
        ):
            continue

        if line.section == ReportSectionType.PENDING_STATUS:
            pending_status_lines.append((line, _pending_test_names(line.text)))
            continue

        if _is_ocr_artifact(line.text):
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason="TABLE_EXTRACTION_ARTIFACT",
                source_page=line.page,
                source_span=line.span,
            ))
            continue

        reference_result = _reference_result_from_line(line)
        if reference_result is not None:
            _register_result(reference_result, results_by_name, excluded_items)
            continue
        if line.section == ReportSectionType.REFERENCE_INTERVAL:
            excluded_items.append(ExcludedReportItem(
                source_text=line.text,
                section=line.section,
                reason="REFERENCE_TABLE",
                source_page=line.page,
                source_span=line.span,
            ))
            continue

        result = _result_from_line(line)
        if result is not None:
            _register_result(result, results_by_name, excluded_items)
            continue

        if line.section in {
            ReportSectionType.COMMENT,
            ReportSectionType.NOTE,
            ReportSectionType.GENERAL_INFORMATION,
            ReportSectionType.RISK_GUIDANCE,
            ReportSectionType.TREATMENT_GUIDANCE,
            ReportSectionType.INTERPRETATION,
        }:
            concepts = [name for name, pattern in _CLINICAL_CONCEPTS if pattern.search(line.text)]
            general_information.append(StructuredFinding(
                concept=", ".join(concepts) if concepts else "General report context",
                text=line.text.strip(),
                section=line.section,
                patient_specific=False,
                negated=False,
                retrieval_eligible=False,
                explanation_eligible=False,
                source_text=source_text,
                source_page=line.page,
                source_span=line.span,
            ))
            continue

        line_findings = _findings_from_line(line)
        if line_findings:
            findings.extend(line_findings)
            continue

        if line.section == ReportSectionType.REFERENCE and not re.fullmatch(
            r"\s*(?:references|bibliography|citations?)\s*:?\s*",
            line.text,
            re.I,
        ):
            references.append(ReportReference(
                citation_text=line.text.strip(),
                source_section=line.section,
                source_page=line.page,
                source_span=line.span,
            ))
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason="REFERENCE_TEXT",
                source_page=line.page,
                source_span=line.span,
            ))
        elif line.section == ReportSectionType.ADMINISTRATIVE:
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason="ADMINISTRATIVE",
                source_page=line.page,
                source_span=line.span,
            ))
        elif line.section == ReportSectionType.PATIENT_METADATA:
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason="PATIENT_METADATA",
                source_page=line.page,
                source_span=line.span,
            ))
        elif line.section in {ReportSectionType.HEADER, ReportSectionType.FOOTER}:
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason="REPEATED_PAGE_TEXT",
                source_page=line.page,
                source_span=line.span,
            ))
        elif line.section in {ReportSectionType.TEST_RESULT, ReportSectionType.TEST_HEADER}:
            if _classify_heading(line.text) is not None:
                continue
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason="TABLE_EXTRACTION_ARTIFACT",
                source_page=line.page,
                source_span=line.span,
            ))
        elif line.section in {
            ReportSectionType.INSTRUCTION,
        }:
            excluded_items.append(ExcludedReportItem(
                source_text=source_text,
                section=line.section,
                reason=line.section.value,
                source_page=line.page,
                source_span=line.span,
            ))
        elif line.section == ReportSectionType.UNKNOWN and line.text.strip():
            excluded_items.append(ExcludedReportItem(
                source_text=line.text,
                section=line.section,
                reason="UNCLASSIFIED_TEXT",
                source_page=line.page,
                source_span=line.span,
            ))

    pending_statuses: list[StructuredPendingStatus] = []
    for line, pending_names in pending_status_lines:
        unresolved_names: list[str] = []
        for canonical, short_name, abbreviation, source_name in pending_names:
            existing = results_by_name.get(canonical)
            if existing is not None and _result_priority(existing) >= 2:
                if existing.status == "pending":
                    unresolved_names.append(canonical)
                continue
            pending_result = StructuredTestResult(
                test_name=canonical,
                canonical_name=canonical,
                source_name=source_name,
                short_name=short_name,
                abbreviation=abbreviation,
                reference_interval=existing.reference_interval if existing else None,
                status="pending",
                section=ReportSectionType.PENDING_STATUS,
                source_section=ReportSectionType.PENDING_STATUS,
                patient_specific=True,
                retrieval_eligible=False,
                explanation_eligible=True,
                source_text=line.text,
                source_page=line.page,
                source_span=line.span,
            )
            _register_result(pending_result, results_by_name, excluded_items)
            selected = results_by_name.get(canonical)
            if selected is not None and selected.status == "pending":
                unresolved_names.append(canonical)
        pending_statuses.append(StructuredPendingStatus(
            test_names=list(dict.fromkeys(unresolved_names)),
            source_text=line.text,
            source_page=line.page,
            source_span=line.span,
        ))

    results = sorted(results_by_name.values(), key=lambda result: result.source_span.start)

    eligible_findings = [finding for finding in findings if finding.retrieval_eligible]
    eligible_results = [
        result for result in results
        if result.retrieval_eligible and result.status == "reported" and result.value is not None
    ]
    retrieval_queries = [
        " ".join(part for part in (result.test_name, result.value, result.unit) if part)
        for result in eligible_results
    ] + [finding.concept for finding in eligible_findings]
    retrieval_items = [
        StructuredFinding(
            concept=result.short_name or result.test_name,
            text=" ".join(part for part in (result.test_name, result.value, result.unit) if part),
            section=result.section,
            patient_specific=result.patient_specific,
            negated=False,
            retrieval_eligible=True,
            explanation_eligible=result.explanation_eligible,
            source_text=result.source_text,
            source_page=result.source_page,
            source_span=result.source_span,
        )
        for result in eligible_results
    ] + eligible_findings
    patient_source = "\n".join(
        dict.fromkeys(
            [result.source_text for result in eligible_results if result.explanation_eligible]
            + [finding.source_text for finding in findings if finding.explanation_eligible]
        )
    ).strip()
    if not patient_source:
        patient_source = "No patient-specific result or finding could be reliably extracted from the supplied report."

    return StructuredMedicalReport(
        raw_source=raw_text,
        patient_source_text=patient_source,
        sections=sections,
        results=results,
        pending_statuses=pending_statuses,
        findings=findings,
        general_information=general_information,
        retrieval_queries=retrieval_queries,
        retrieval_eligible_items=retrieval_items,
        excluded_items=excluded_items,
        references=references,
    )
