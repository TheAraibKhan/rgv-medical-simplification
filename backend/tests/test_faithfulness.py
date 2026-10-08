from app.retrieval.medlineplus import MedlinePlusRetriever
from app.schemas.common import Claim, ClaimType, CompareRequest, VerificationLabel
from app.services.claims import decompose
from app.services.llm import LLMService
from app.services.pipeline import ResearchPipeline
from app.verification.verifier import VerificationService
from fastapi.testclient import TestClient
from app.main import app
from types import SimpleNamespace


def test_patient_specific_causal_inference_is_unsupported() -> None:
    verifier = VerificationService()
    claim = Claim(
        claim_id="1",
        text="Your enlarged heart is probably caused by high blood pressure",
        claim_type=ClaimType.PATIENT_SPECIFIC,
    )
    result = verifier.verify(claim, "Mild cardiomegaly.", [])
    assert result.label == VerificationLabel.UNSUPPORTED_PATIENT_CLAIM


def test_source_supported_patient_assertion() -> None:
    verifier = VerificationService()
    claim = Claim(
        claim_id="2",
        text="Your heart appears slightly larger than normal",
        claim_type=ClaimType.PATIENT_SPECIFIC,
    )
    result = verifier.verify(claim, "Mild cardiomegaly.", [])
    assert result.label == VerificationLabel.SUPPORTED
    assert result.evidence[0].source == "Source report"


def test_demo_retrieval_matches_only_positive_source_concepts() -> None:
    retriever = MedlinePlusRetriever()
    cases = [
        (
            "Mild cardiomegaly with bilateral pleural effusion. No evidence of pneumothorax.",
            {"demo-cardiomegaly", "demo-pleural-effusion"},
        ),
        (
            "Acute myocardial infarction involving the inferior wall. Mild left ventricular enlargement. No pleural effusion.",
            {"demo-myocardial-infarction", "demo-left-ventricular-enlargement"},
        ),
        (
            "Small right-sided pneumothorax. No pleural effusion. Cardiomediastinal silhouette is within normal limits.",
            {"demo-pneumothorax"},
        ),
        (
            "Mild bibasilar atelectatic changes. No focal consolidation or pleural effusion.",
            {"demo-atelectasis"},
        ),
    ]

    for report, expected_ids in cases:
        evidence = retriever.demo_search(report, top_k=5)
        assert {item.document_id for item in evidence} == expected_ids


def test_compare_api_preserves_pipeline_boundaries_for_requested_reports() -> None:
    cases = [
        (
            "Mild cardiomegaly with bilateral pleural effusion. No evidence of pneumothorax.",
            {"demo-cardiomegaly", "demo-pleural-effusion"},
        ),
        (
            "Acute myocardial infarction involving the inferior wall. Mild left ventricular enlargement. No pleural effusion.",
            {"demo-myocardial-infarction", "demo-left-ventricular-enlargement"},
        ),
        (
            "Small right-sided pneumothorax. No pleural effusion. Cardiomediastinal silhouette is within normal limits.",
            {"demo-pneumothorax"},
        ),
        (
            "Mild bibasilar atelectatic changes. No focal consolidation or pleural effusion.",
            {"demo-atelectasis"},
        ),
    ]
    client = TestClient(app)

    for report, expected_ids in cases:
        response = client.post("/api/compare", json={"report": report, "top_k": 5})
        assert response.status_code == 200
        result = response.json()
        assert result["report"] == report
        assert result["b1"]["evidence"] == []
        assert {item["document_id"] for item in result["b2"]["evidence"]} == expected_ids
        assert result["b2"]["evidence"] == result["b3"]["evidence"]
        assert result["b3"]["verifications"]
        assert all("original_claim" in check and "changed" in check for check in result["b3"]["verifications"])


def test_demo_top_k_returns_only_relevant_ranked_concepts() -> None:
    retriever = MedlinePlusRetriever()
    report = (
        "Acute myocardial infarction involving the inferior wall. "
        "Mild left ventricular enlargement. No pleural effusion."
    )

    assert [item.document_id for item in retriever.demo_search(report, top_k=1)] == [
        "demo-myocardial-infarction"
    ]
    assert [item.document_id for item in retriever.demo_search(report, top_k=3)] == [
        "demo-myocardial-infarction",
        "demo-left-ventricular-enlargement",
    ]


def test_negation_scope_does_not_hide_a_later_positive_finding() -> None:
    retriever = MedlinePlusRetriever()

    evidence = retriever.demo_search("No pleural effusion, mild cardiomegaly.", top_k=5)

    assert [item.document_id for item in evidence] == ["demo-cardiomegaly"]


def test_multiple_findings_under_negation_are_not_retrieved() -> None:
    retriever = MedlinePlusRetriever()

    evidence = retriever.demo_search("No pleural effusion or pneumothorax.", top_k=5)

    assert evidence == []


def test_b1_b2_b3_share_report_and_b2_b3_share_retrieval() -> None:
    report = "Mild cardiomegaly with bilateral pleural effusion. No evidence of pneumothorax."
    result = ResearchPipeline().compare(CompareRequest(report=report, top_k=3))

    assert result.report == report
    assert result.b1.evidence == []
    assert {item.document_id for item in result.b2.evidence} == {
        "demo-cardiomegaly",
        "demo-pleural-effusion",
    }
    assert result.b2.evidence == result.b3.evidence
    assert result.b1.output == ResearchPipeline()._run_b1(report).output
    assert result.b1.output != result.b2.output
    assert "Cardiomegaly:" in result.b2.output
    assert result.b3.first_pass_output == result.b2.output
    assert result.b3.verifications
    assert "confidence" not in result.b3.verifications[0].model_dump()


def test_demo_patient_cause_claim_is_not_supported_by_retrieval() -> None:
    claim = Claim(
        claim_id="cause",
        text="Your enlarged heart is probably caused by high blood pressure",
        claim_type=ClaimType.PATIENT_SPECIFIC,
    )
    context = MedlinePlusRetriever().demo_search("Mild cardiomegaly.", top_k=1)
    result = VerificationService().verify(claim, "Mild cardiomegaly.", context)

    assert result.label == VerificationLabel.UNSUPPORTED_PATIENT_CLAIM


def test_patient_claim_negation_must_match_source_report() -> None:
    verifier = VerificationService()
    report = "No pleural effusion."
    supported_negation = Claim(
        claim_id="negative",
        text="The report says there is no fluid around the lungs",
        claim_type=ClaimType.PATIENT_SPECIFIC,
        polarity="NEGATED",
    )
    unsupported_positive = Claim(
        claim_id="positive",
        text="There is fluid around both lungs",
        claim_type=ClaimType.PATIENT_SPECIFIC,
    )

    assert verifier.verify(supported_negation, report, []).label == VerificationLabel.SUPPORTED
    assert verifier.verify(unsupported_positive, report, []).label == VerificationLabel.UNSUPPORTED_PATIENT_CLAIM


def test_b3_demo_pipeline_keeps_supported_pneumothorax_claim() -> None:
    report = "Small right-sided pneumothorax. No pleural effusion."
    result = ResearchPipeline().compare(CompareRequest(report=report, top_k=3))

    assert [item.document_id for item in result.b2.evidence] == ["demo-pneumothorax"]
    assert result.b3.evidence == result.b2.evidence
    assert result.b3.correction_applied is False
    assert "small right-sided air around the lung" in result.b3.output.lower()


def test_b3_removes_unsupported_patient_sentence() -> None:
    output = (
        "Your heart appears slightly larger than usual. "
        "Your enlarged heart is caused by hypertension."
    )
    claims = decompose(output)
    unsupported_ids = {
        claim.claim_id for claim in claims if "caused by hypertension" in claim.text
    }

    corrected = ResearchPipeline._remove_unsupported_claims(output, claims, unsupported_ids)

    assert corrected == "Your heart appears slightly larger than usual."


def test_b3_audit_records_withheld_unsupported_claim(monkeypatch) -> None:
    first_pass = (
        "Your heart appears slightly larger than usual. "
        "Your enlarged heart is caused by hypertension."
    )
    monkeypatch.setattr(
        "app.services.pipeline.llm_service.generate",
        lambda *_, **__: first_pass,
    )

    result = ResearchPipeline()._run_b3("Mild cardiomegaly.", [], mode="demo")

    unsupported = next(
        check for check in result.verifications
        if "caused by hypertension" in check.original_claim
    )
    assert result.first_pass_output == first_pass
    assert result.output == "Your heart appears slightly larger than usual."
    assert unsupported.label == VerificationLabel.UNSUPPORTED_PATIENT_CLAIM
    assert unsupported.changed is True
    assert unsupported.final_claim is None


def test_research_generation_uses_direct_and_shared_rag_prompts(monkeypatch) -> None:
    import app.services.llm as llm_module

    calls = []

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Patient explanation."))]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(llm_module, "OpenAI", lambda **_: fake_client)
    monkeypatch.setattr("app.services.llm.settings.app_mode", "research")
    monkeypatch.setattr("app.services.llm.settings.llm_provider", "vllm")
    monkeypatch.setattr("app.services.llm.settings.vllm_model", "local-test-model")
    service = LLMService()
    evidence = [{"title": "Heart attack", "text": "A heart attack is a general term."}]
    report = "Acute myocardial infarction."

    service.generate(report, evidence, condition="B1")
    service.generate(report, evidence, condition="B2")
    service.generate(report, evidence, condition="B3")

    assert "Heart attack" not in calls[0]["messages"][1]["content"]
    assert calls[1]["messages"][1]["content"] == calls[2]["messages"][1]["content"]
    assert calls[1]["messages"][0]["content"] == calls[2]["messages"][0]["content"]
    assert calls[0]["model"] == "local-test-model"


def test_research_mode_without_model_configuration_uses_demo_provider(monkeypatch) -> None:
    monkeypatch.setattr("app.services.llm.settings.app_mode", "research")
    monkeypatch.setattr("app.services.llm.settings.llm_provider", "vllm")
    monkeypatch.setattr("app.services.llm.settings.vllm_model", "")

    service = LLMService()

    assert service.active_provider == "demo"
    assert service.generate("Mild cardiomegaly.", condition="B1") == "Your heart appears slightly larger than usual."


def test_research_mode_falls_back_when_local_server_has_no_models(monkeypatch) -> None:
    import app.services.llm as llm_module

    fake_client = SimpleNamespace(models=SimpleNamespace(list=lambda: SimpleNamespace(data=[])))
    monkeypatch.setattr(llm_module, "OpenAI", lambda **_: fake_client)
    monkeypatch.setattr("app.services.llm.settings.app_mode", "research")
    monkeypatch.setattr("app.services.llm.settings.llm_provider", "vllm")
    monkeypatch.setattr("app.services.llm.settings.vllm_model", "local-test-model")
    monkeypatch.setattr("app.services.llm.settings.verifier_model", "")

    service = LLMService()

    assert service.local_model_available() is False


def test_local_verifier_cannot_use_retrieval_to_support_patient_claim(monkeypatch) -> None:
    import app.verification.verifier as verifier_module

    class FakeCompletions:
        def create(self, **_):
            return SimpleNamespace(
                choices=[SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"label":"SUPPORTED","quote":"hypertension","reason":"Claim supported."}'
                    )
                )]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(verifier_module, "OpenAI", lambda **_: fake_client)
    monkeypatch.setattr("app.verification.verifier.settings.verifier_provider", "vllm")
    monkeypatch.setattr("app.verification.verifier.settings.vllm_model", "local-test-model")
    service = VerificationService()
    claim = Claim(
        claim_id="cause",
        text="Your enlarged heart is caused by hypertension.",
        claim_type=ClaimType.PATIENT_SPECIFIC,
    )

    result = service.verify(claim, "Mild cardiomegaly.", [], mode="research")

    assert result.label == VerificationLabel.UNSUPPORTED_PATIENT_CLAIM
    assert result.evidence == []
