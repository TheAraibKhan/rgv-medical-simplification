from app.retrieval.medlineplus import MedlinePlusRetriever
from app.schemas.common import CompareRequest, ReportSectionType
from app.services.clinical_structure import structure_medical_report
from app.services.pipeline import ResearchPipeline


LAB_REPORT = """PATIENT RESULTS
ApoB = 46.00 mg/dL (46-174 mg/dL)
hsCRP = 1.00 mg/L (<1.00 mg/L)
High-sensitivity Troponin-I = 4 ng/L (<19 ng/L)
HbA1c | Result/s to follow
Fasting glucose | | mg/dL |

COMMENT
hsCRP is associated with future myocardial infarction, stroke, and cardiovascular risk.
Risk of future myocardial infarction does not mean the patient has had a heart attack.

INSTRUCTIONS
Contact customer care for assistance.

REFERENCES
[1] Example laboratory method citation.
"""


def test_sections_results_and_provenance_are_structured_from_report_spans() -> None:
    structured = structure_medical_report(LAB_REPORT)

    results = {item.short_name: item for item in structured.results}
    assert results["ApoB"].value == "46.00"
    assert results["ApoB"].unit == "mg/dL"
    assert results["ApoB"].reference_interval == "46-174 mg/dL"
    assert results["ApoB"].abbreviation == "ApoB"
    assert results["ApoB"].retrieval_eligible is True
    assert results["hsCRP"].value == "1.00"
    assert results["hsCRP"].reference_interval == "<1.00 mg/L"
    assert results["hs-Troponin I"].value == "4"
    assert results["HbA1c"].status == "pending"
    assert results["Fasting glucose"].status == "not_available"

    for result in structured.results:
        assert result.source_text == LAB_REPORT[result.source_span.start:result.source_span.end]
        assert result.patient_specific is True
        assert result.source_span.page is None

    assert any(item.section == ReportSectionType.COMMENT for item in structured.sections)
    assert any(item.section == ReportSectionType.REFERENCE for item in structured.sections)
    assert any(item.section == ReportSectionType.INSTRUCTION for item in structured.sections)
    assert structured.references[0].citation_text == "[1] Example laboratory method citation."
    assert any(item.reason == "ADMINISTRATIVE" for item in structured.excluded_items)
    assert all(item.section != ReportSectionType.COMMENT for item in structured.retrieval_eligible_items)


def test_commentary_concepts_are_context_only_and_not_retrieval_queries() -> None:
    structured = structure_medical_report(LAB_REPORT)

    assert structured.general_information
    assert all(item.concept == "myocardial infarction" for item in structured.general_information)
    assert all(not item.patient_specific for item in structured.general_information)
    assert all(not item.retrieval_eligible for item in structured.general_information)
    assert all("myocardial infarction" not in query.lower() for query in structured.retrieval_queries)
    assert not any("myocardial infarction" in item.concept for item in structured.findings)


def test_retrievers_are_safe_when_called_with_raw_report_text() -> None:
    retriever = MedlinePlusRetriever()
    comment_only = "COMMENT\nhsCRP is associated with future myocardial infarction."

    assert retriever.demo_search(comment_only, top_k=5) == []


def test_retrieval_only_uses_eligible_results_and_does_not_force_sources() -> None:
    result = ResearchPipeline().compare(CompareRequest(report=LAB_REPORT, top_k=5))

    assert result.structured_report is not None
    assert result.b2.evidence == []
    assert result.b3.evidence == result.b2.evidence
    assert result.b1.evidence == []
    assert not any("myocardial infarction" in finding.text.lower() for finding in result.findings)
    assert result.structured_report.raw_source == LAB_REPORT
    assert "future myocardial infarction" not in result.b1.output.lower()
    assert "future myocardial infarction" not in result.b2.output.lower()
    assert "future myocardial infarction" not in result.b3.output.lower()


def test_explicit_negation_is_a_patient_finding_but_not_retrieval_eligible() -> None:
    structured = structure_medical_report("FINDINGS\nNo pleural effusion.")

    assert len(structured.findings) == 1
    assert structured.findings[0].concept == "pleural effusion"
    assert structured.findings[0].patient_specific is True
    assert structured.findings[0].negated is True
    assert structured.findings[0].retrieval_eligible is False


def test_risk_context_does_not_become_patient_finding() -> None:
    structured = structure_medical_report("Risk of future myocardial infarction.")

    assert structured.findings == []
    assert structured.general_information
    assert structured.general_information[0].patient_specific is False
    assert structured.retrieval_queries == []
    assert structured.general_information[0].source_text == "Risk of future myocardial infarction."


def test_educational_interpretation_is_context_not_a_patient_finding() -> None:
    structured = structure_medical_report(
        "INTERPRETATION\nMyocardial infarction is a condition caused by reduced blood flow to the heart."
    )

    assert structured.findings == []
    assert structured.retrieval_queries == []
    assert structured.general_information[0].patient_specific is False
    assert structured.general_information[0].section == ReportSectionType.INTERPRETATION


def test_current_positive_radiology_result_still_retrieves_relevant_knowledge() -> None:
    report = "Mild cardiomegaly with bilateral pleural effusion. No evidence of pneumothorax."
    result = ResearchPipeline().compare(CompareRequest(report=report, top_k=5))

    assert {item.document_id for item in result.b2.evidence} == {
        "demo-cardiomegaly",
        "demo-pleural-effusion",
    }
    assert result.b3.evidence == result.b2.evidence
    assert not any(item.document_id == "demo-pneumothorax" for item in result.b2.evidence)


def test_patient_negative_after_comma_does_not_suppress_later_positive_finding() -> None:
    structured = structure_medical_report("FINDINGS\nNo pleural effusion, mild cardiomegaly.")

    assert [(item.concept, item.negated) for item in structured.findings] == [
        ("pleural effusion", True),
        ("cardiomegaly", False),
    ]
    assert structured.retrieval_queries == ["cardiomegaly"]


def test_multiline_test_header_pairs_with_following_value_and_unit() -> None:
    report = "TEST RESULTS\nApoB\n46.00 mg/dL\n"
    structured = structure_medical_report(report)

    assert len(structured.results) == 1
    result = structured.results[0]
    assert result.test_name == "Apolipoprotein B"
    assert result.short_name == "ApoB"
    assert result.value == "46.00"
    assert result.unit == "mg/dL"
    assert result.status == "reported"
    assert result.source_text == "ApoB\n46.00 mg/dL"
    assert report[result.source_span.start:result.source_span.end] == result.source_text


def test_history_is_patient_specific_but_future_risk_is_not() -> None:
    history = structure_medical_report("HISTORY\nHistory of myocardial infarction.")
    risk = structure_medical_report("COMMENT\nRisk of future myocardial infarction.")

    assert history.findings
    assert history.findings[0].patient_specific is True
    assert history.findings[0].retrieval_eligible is True
    assert risk.findings == []
    assert risk.general_information
    assert risk.retrieval_queries == []


def test_repeated_test_rows_are_deduplicated_but_retained_in_exclusion_ledger() -> None:
    report = "TEST RESULTS\nApoB = 46.00 mg/dL (46-174 mg/dL)\nApoB = 46.00 mg/dL (46-174 mg/dL)\n"

    structured = structure_medical_report(report)

    assert len(structured.results) == 1
    assert any(item.reason == "DUPLICATE" for item in structured.excluded_items)
    assert structured.raw_source == report


def test_z615_style_result_tables_merge_aliases_and_ignore_ocr_artifacts() -> None:
    report = """PATIENT RESULTS
APOLIPOPROTEIN B (Apo B)    46.00    mg/dL    46-174 mg/dL
Apolipoprotein B = 46.00 mg/dL (46-174 mg/dL)
CARDIO C-REACTIVE PROTEIN (hsCRP), SERUM    1.00    mg/L    <1.00 mg/L
hsCRP = 1.00 mg/L (<1.00 mg/L)
High-sensitivity Troponin-I    4    ng/L    <19 ng/L
1 1 1
Any condition that shortens erythrocyte survival can affect HbA1c interpretation.

COMMENT
Future myocardial infarction is educational commentary.

REFERENCE INTERVAL
Lipid Profile    <200 mg/dL

RESULT/S TO FOLLOW:
Troponin-I, Lipid Profile, HbA1c, Glucose, Lp(a), hsCRP
"""

    structured = structure_medical_report(report)
    results_by_name = {item.test_name: item for item in structured.results}

    assert len(structured.results) == 7
    assert results_by_name["Apolipoprotein B"].value == "46.00"
    assert results_by_name["Apolipoprotein B"].short_name == "ApoB"
    assert results_by_name["Apolipoprotein B"].source_name == "APOLIPOPROTEIN B (Apo B)"
    assert results_by_name["Apolipoprotein B"].source_page is None
    assert results_by_name["High-sensitivity C-reactive protein"].value == "1.00"
    assert results_by_name["High-sensitivity Troponin-I"].value == "4"
    assert results_by_name["High-sensitivity Troponin-I"].unit == "ng/L"
    assert results_by_name["Lipid profile"].value is None
    assert results_by_name["Lipid profile"].reference_interval == "<200 mg/dL"
    assert results_by_name["Lipid profile"].status == "pending"
    assert results_by_name["Hemoglobin A1c"].status == "pending"
    assert results_by_name["Glucose"].status == "pending"
    assert results_by_name["Lipoprotein(a)"].status == "pending"
    assert results_by_name["High-sensitivity C-reactive protein"].status == "reported"
    assert all(item.test_name != "1 1 1" for item in structured.results)
    assert all(item.test_name != "Result/s to follow" for item in structured.results)
    assert any(
        item.reason == "TABLE_EXTRACTION_ARTIFACT"
        and "Any condition that shortens erythrocyte" in item.source_text
        for item in structured.excluded_items
    )
    assert all(item.section != ReportSectionType.COMMENT for item in structured.findings)
    assert any(item.section == ReportSectionType.COMMENT for item in structured.general_information)
    assert any(item.reason == "TABLE_EXTRACTION_ARTIFACT" for item in structured.excluded_items)
    pending_names = {name for status in structured.pending_statuses for name in status.test_names}
    assert pending_names == {"Lipid profile", "Hemoglobin A1c", "Glucose", "Lipoprotein(a)"}


def test_pdf_page_markers_are_preserved_in_result_provenance() -> None:
    report = "PATIENT RESULTS\nApoB = 46.00 mg/dL\n\fPATIENT RESULTS\nTroponin-I = 4 ng/L"

    structured = structure_medical_report(report)
    results = {item.test_name: item for item in structured.results}

    assert results["Apolipoprotein B"].source_page == 1
    assert results["Apolipoprotein B"].source_span.page == 1
    assert results["High-sensitivity Troponin-I"].source_page == 2
    assert results["High-sensitivity Troponin-I"].source_span.page == 2


def test_conflicting_measured_duplicates_require_review() -> None:
    structured = structure_medical_report(
        "PATIENT RESULTS\nApoB = 46.00 mg/dL\n\fPATIENT RESULTS\nApolipoprotein B = 50.00 mg/dL"
    )

    assert len(structured.results) == 1
    assert structured.results[0].status == "needs_review"
    assert structured.results[0].value is None
    assert any(item.reason == "CONFLICTING_DUPLICATE" for item in structured.excluded_items)
