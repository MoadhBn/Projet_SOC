import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.scoring import (
    Level,
    LlmLabel,
    Thresholds,
    compute_score,
    level_for,
    respond,
    respond_before_llm,
)

client = TestClient(app)


def test_maximum_score_is_100():
    detail = compute_score(15, True, 1.0, LlmLabel.MALICIOUS)
    assert detail.total == pytest.approx(100)


def test_base_score_ignores_llm():
    detail = compute_score(10, False, 0.5, LlmLabel.MALICIOUS)
    assert detail.base == pytest.approx(50 * 10 / 15 + 7.5)
    assert detail.total == pytest.approx(detail.base + 10)


def test_benign_label_never_lowers_the_score():
    without = compute_score(12, True, 0.3)
    benign = compute_score(12, True, 0.3, LlmLabel.BENIGN)
    assert benign.total == pytest.approx(without.total)


def test_malicious_label_can_raise_the_level():
    thresholds = Thresholds(medium=25, high=40)
    detail = compute_score(10, False, 0.2)  # base about 36.3: medium
    assert level_for(detail.base, thresholds) is Level.MEDIUM
    raised = compute_score(10, False, 0.2, LlmLabel.MALICIOUS)
    assert level_for(raised.total, thresholds) is Level.HIGH


def test_high_base_score_responds_without_waiting_for_llm():
    detail = compute_score(15, True, 0.0)  # 75 before any label
    assert respond(detail)
    assert respond_before_llm(detail)


def test_llm_label_can_trigger_the_response_after_the_base_score():
    detail = compute_score(7, False, 1.0, LlmLabel.MALICIOUS)  # base 38.3, final 48.3
    assert not respond_before_llm(detail)
    assert respond(detail)


def test_low_score_does_not_respond():
    detail = compute_score(3, False, 0.1)
    assert not respond(detail)
    assert not respond_before_llm(detail)


@pytest.mark.parametrize("rule_level", [-1, 16])
def test_rule_level_out_of_range_is_rejected(rule_level):
    with pytest.raises(ValueError):
        compute_score(rule_level, False, 0.0)


def test_api_returns_score_detail():
    response = client.post(
        "/score",
        json={"rule_level": 15, "misp_match": True, "anomaly_score": 1.0, "llm_label": "malicious"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["final_score"] == 100
    assert body["level"] == "high"
    assert body["respond"] is True
    assert body["respond_before_llm"] is True


def test_api_rejects_invalid_input():
    response = client.post("/score", json={"rule_level": 20, "misp_match": False, "anomaly_score": 0.5})
    assert response.status_code == 422
