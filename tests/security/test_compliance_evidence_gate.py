from mycosoft_mas.security.compliance_evidence_gate import evaluate_control_response, is_control_met


def test_plain_met_string_is_not_accepted() -> None:
    assert not is_control_met("met")


def test_missing_evidence_is_not_accepted() -> None:
    result = evaluate_control_response({"status": "met", "sao_validated": True})
    assert not result.allowed_met
    assert result.reason == "missing_evidence_uri"


def test_missing_sao_validation_is_not_accepted() -> None:
    result = evaluate_control_response({"status": "implemented", "evidence_uri": "preveil://evidence/ac/3.1.1"})
    assert not result.allowed_met
    assert result.reason == "missing_sao_validation"


def test_met_requires_evidence_and_sao_validation() -> None:
    assert is_control_met(
        {
            "status": "met",
            "evidence_uri": "preveil://evidence/ac/3.1.1",
            "sao_validated": True,
        }
    )
