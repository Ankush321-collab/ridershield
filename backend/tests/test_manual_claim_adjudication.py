import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import manual_claims.adjudication as adjudication_module
from manual_claims.adjudication import adjudicate_manual_claim
from claims_service.service import (
    approve_manual_claim,
    process_manual_claim,
    reject_manual_claim,
)


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class FakeClaimsDb:
    def __init__(self, results):
        self.results = list(results)
        self.added = []

    async def execute(self, _query):
        if not self.results:
            raise AssertionError("Unexpected execute call")
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        return None

    async def commit(self):
        return None


def _manual_claim_payload(spam_score: int) -> dict:
    return {
        "rider_id": uuid4(),
        "policy_id": uuid4(),
        "disruption_type": "heavy_rain",
        "incident_time": datetime.utcnow(),
        "spam_score": spam_score,
    }


def test_adjudicate_manual_claim_approves_low_risk_response():
    async def _run():
        with patch("manual_claims.adjudication.gather_manual_claim_evidence", AsyncMock(return_value={"claim": {}, "validation": {}, "duplicates": {}, "policy": {}, "earnings": {}})), patch(
            "manual_claims.adjudication._call_nebius_completion",
            AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"decision":"approved","confidence":0.91,'
                                    '"reason_summary":"Corroborating evidence supports the claim.",'
                                    '"evidence_used":["policy_context","validation_context"],'
                                    '"threshold_context":{"aligned_with_threshold":true}}'
                                )
                            }
                        }
                    ]
                }
            ),
        ), patch.object(adjudication_module.settings, "NEBIUS_API_KEY", "test-key"):
            result = await adjudicate_manual_claim(_manual_claim_payload(20), db=SimpleNamespace())
            assert result.decision == "approved"
            assert result.threshold_context["band"] == "low_risk"

    asyncio.run(_run())


def test_adjudicate_manual_claim_handles_tool_calls_then_rejects():
    async def _run():
        with patch("manual_claims.adjudication.gather_manual_claim_evidence", AsyncMock(return_value={"claim": {}, "validation": {}, "duplicates": {"manual_claim_count_for_policy": 2}, "policy": {"coverage_remaining": 400}, "earnings": {"income_loss": 300}})), patch(
            "manual_claims.adjudication._call_nebius_completion",
            AsyncMock(
                side_effect=[
                    {
                        "choices": [
                            {
                                "message": {
                                    "tool_calls": [
                                        {
                                            "id": "call_1",
                                            "function": {"name": "get_duplicate_claim_context"},
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": (
                                        '{"decision":"rejected","confidence":0.88,'
                                        '"reason_summary":"Evidence shows duplicate manual-claim activity.",'
                                        '"evidence_used":["get_duplicate_claim_context"],'
                                        '"threshold_context":{"aligned_with_threshold":true}}'
                                    )
                                }
                            }
                        ]
                    },
                ]
            ),
        ), patch.object(adjudication_module.settings, "NEBIUS_API_KEY", "test-key"):
            result = await adjudicate_manual_claim(_manual_claim_payload(82), db=SimpleNamespace())
            assert result.decision == "rejected"
            assert result.threshold_context["band"] == "high_risk"

    asyncio.run(_run())


def test_adjudicate_manual_claim_falls_back_on_invalid_payload():
    async def _run():
        with patch("manual_claims.adjudication.gather_manual_claim_evidence", AsyncMock(return_value={"claim": {}, "validation": {}, "duplicates": {}, "policy": {}, "earnings": {}})), patch(
            "manual_claims.adjudication._call_nebius_completion",
            AsyncMock(return_value={"choices": [{"message": {"content": '{"decision":"maybe"}'}}]}),
        ), patch.object(adjudication_module.settings, "NEBIUS_API_KEY", "test-key"):
            result = await adjudicate_manual_claim(_manual_claim_payload(45), db=SimpleNamespace())
            assert result.decision == "rejected"
            assert result.threshold_context["fallback"] is True

    asyncio.run(_run())


def test_adjudicate_manual_claim_falls_back_on_transport_error():
    async def _run():
        with patch("manual_claims.adjudication.gather_manual_claim_evidence", AsyncMock(return_value={"claim": {}, "validation": {}, "duplicates": {}, "policy": {}, "earnings": {}})), patch(
            "manual_claims.adjudication._call_nebius_completion",
            AsyncMock(side_effect=RuntimeError("boom")),
        ), patch.object(adjudication_module.settings, "NEBIUS_API_KEY", "test-key"):
            result = await adjudicate_manual_claim(_manual_claim_payload(55), db=SimpleNamespace())
            assert result.decision == "rejected"
            assert "Nebius Kimi" in result.reason_summary

    asyncio.run(_run())


def test_process_manual_claim_marks_approved_and_triggers_payout():
    rider_id = uuid4()
    policy_id = uuid4()
    incident_time = datetime.utcnow().replace(microsecond=0)
    policy = SimpleNamespace(id=policy_id, coverage_limit=5000, coverage_used=0)
    rider = SimpleNamespace(id=rider_id, zone_id=uuid4())
    baseline = SimpleNamespace(avg_earnings=700)
    snapshot = SimpleNamespace(earnings_current_slot=100)
    db = FakeClaimsDb([
        _ScalarResult(policy),
        _ScalarResult(rider),
        _ScalarResult(baseline),
        _ScalarResult(snapshot),
    ])

    async def _record_payout(*args, **kwargs):
        return SimpleNamespace(id=uuid4())

    async def _run():
        with patch("claims_service.service.process_upi_payout", side_effect=_record_payout) as payout_mock:
            result = await process_manual_claim(
                {
                    "rider_id": rider_id,
                    "policy_id": policy_id,
                    "disruption_type": "heavy_rain",
                    "incident_time": incident_time,
                    "spam_score": 20,
                    "review_decision": "approved",
                    "review_reason": "Auto-approved by LLM.",
                },
                db=db,
            )
            claim = db.added[0]
            assert result["status"] == "approved"
            assert claim.status == "paid"
            assert payout_mock.await_count == 1

    asyncio.run(_run())


def test_process_manual_claim_marks_rejected_without_payout():
    rider_id = uuid4()
    policy_id = uuid4()
    incident_time = datetime.utcnow().replace(microsecond=0)
    policy = SimpleNamespace(id=policy_id, coverage_limit=5000, coverage_used=0)
    rider = SimpleNamespace(id=rider_id, zone_id=uuid4())
    baseline = SimpleNamespace(avg_earnings=700)
    snapshot = SimpleNamespace(earnings_current_slot=100)
    db = FakeClaimsDb([
        _ScalarResult(policy),
        _ScalarResult(rider),
        _ScalarResult(baseline),
        _ScalarResult(snapshot),
    ])

    async def _run():
        with patch("claims_service.service.process_upi_payout", new_callable=AsyncMock) as payout_mock:
            result = await process_manual_claim(
                {
                    "rider_id": rider_id,
                    "policy_id": policy_id,
                    "disruption_type": "heavy_rain",
                    "incident_time": incident_time,
                    "spam_score": 82,
                    "review_decision": "rejected",
                    "review_reason": "Auto-rejected by LLM.",
                },
                db=db,
            )
            claim = db.added[0]
            assert result["status"] == "rejected"
            assert claim.status == "rejected"
            payout_mock.assert_not_awaited()

    asyncio.run(_run())


def test_approve_manual_claim_allows_override_from_rejected():
    claim = SimpleNamespace(id=uuid4(), rider_id=uuid4(), payout_amount=350, status="rejected", processed_at=None)
    db = FakeClaimsDb([_ScalarResult(claim)])

    async def _run():
        with patch("claims_service.service.process_upi_payout", AsyncMock(return_value=SimpleNamespace(id=uuid4()))):
            result = await approve_manual_claim(claim.id, db=db, allow_override=True)
            assert result["status"] == "approved"
            assert result["overridden"] is True
            assert claim.status == "paid"

    asyncio.run(_run())


def test_reject_manual_claim_marks_paid_override_for_followup():
    claim = SimpleNamespace(id=uuid4(), rider_id=uuid4(), payout_amount=350, status="paid", processed_at=None)
    db = FakeClaimsDb([_ScalarResult(claim)])

    async def _run():
        result = await reject_manual_claim(claim.id, "Manual override", db=db, allow_override=True)
        assert result["status"] == "rejected"
        assert result["payout_reversal_required"] is True
        assert claim.status == "rejected"

    asyncio.run(_run())
