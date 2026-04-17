import json
import logging
from datetime import datetime
from typing import Any, Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from claims_service.models import Claim
from manual_claims.geo_validation import explain_spam_rejection
from policy_service.models import Policy
from rider_service.models import Rider, RiderZoneBaseline
from shared.config import settings
from trigger_service.models import PlatformSnapshot

logger = logging.getLogger("zylo.manual_claims.adjudication")

LOW_RISK_SPAM_THRESHOLD = 30
HIGH_RISK_SPAM_THRESHOLD = 70
_MAX_TOOL_ROUNDS = 4


class ManualClaimAdjudication(BaseModel):
    decision: Literal["approved", "rejected"]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_summary: str
    evidence_used: list[str] = Field(default_factory=list)
    threshold_context: dict[str, Any] = Field(default_factory=dict)


def _extract_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        text = content.get("text") or content.get("content")
        return text if isinstance(text, str) else ""
    return str(content)


def _extract_json_candidate(raw_text: str) -> str:
    text = raw_text.strip()
    if not text:
        return "{}"
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _normalize_decision_payload(parsed: dict[str, Any]) -> dict[str, Any]:
    decision = str(parsed.get("decision", "")).strip().lower()
    if decision == "approve":
        parsed["decision"] = "approved"
    elif decision == "reject":
        parsed["decision"] = "rejected"

    confidence = parsed.get("confidence", 0.0)
    if isinstance(confidence, str):
        stripped = confidence.strip().rstrip("%")
        try:
            confidence = float(stripped)
        except ValueError:
            confidence = 0.0
    if isinstance(confidence, (int, float)) and confidence > 1:
        confidence = float(confidence) / 100.0
    parsed["confidence"] = confidence

    if not parsed.get("reason_summary"):
        parsed["reason_summary"] = (
            parsed.get("reason")
            or parsed.get("summary")
            or parsed.get("explanation")
            or "Automated adjudication completed."
        )

    evidence_used = parsed.get("evidence_used")
    if isinstance(evidence_used, str):
        parsed["evidence_used"] = [item.strip() for item in evidence_used.split(",") if item.strip()]
    elif not isinstance(evidence_used, list):
        parsed["evidence_used"] = []

    threshold_context = parsed.get("threshold_context")
    if not isinstance(threshold_context, dict):
        parsed["threshold_context"] = {}

    return parsed


def _slot_bucket(slot_start: datetime) -> str:
    hour = slot_start.hour
    if 18 <= hour < 21:
        return "18:00-21:00"
    if 21 <= hour < 23:
        return "21:00-23:00"
    return f"{hour:02d}:00-{min(hour + 3, 23):02d}:00"


def _slot_window(value: datetime) -> tuple[str, datetime, datetime]:
    slot_time_str = _slot_bucket(value)
    start_raw, end_raw = slot_time_str.split("-")
    start_hour = int(start_raw.split(":")[0])
    end_hour = int(end_raw.split(":")[0])
    slot_start = value.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    slot_end = value.replace(hour=end_hour, minute=0, second=0, microsecond=0)
    return slot_time_str, slot_start, slot_end


def _threshold_band(spam_score: int) -> str:
    if spam_score >= HIGH_RISK_SPAM_THRESHOLD:
        return "high_risk"
    if spam_score < LOW_RISK_SPAM_THRESHOLD:
        return "low_risk"
    return "review_band"


def _default_expectation_for_band(spam_score: int) -> str:
    band = _threshold_band(spam_score)
    if band == "high_risk":
        return "reject"
    if band == "low_risk":
        return "approve"
    return "inspect"


def _fallback_rejection(spam_score: int, reason: str, evidence_used: list[str] | None = None) -> ManualClaimAdjudication:
    return ManualClaimAdjudication(
        decision="rejected",
        confidence=0.0,
        reason_summary=reason,
        evidence_used=evidence_used or ["system_fallback"],
        threshold_context={
            "spam_score": spam_score,
            "band": _threshold_band(spam_score),
            "default_expectation": _default_expectation_for_band(spam_score),
            "aligned_with_threshold": True,
            "fallback": True,
        },
    )


async def gather_manual_claim_evidence(claim_data: dict, db: AsyncSession) -> dict[str, Any]:
    rider_id = claim_data["rider_id"]
    policy_id = claim_data["policy_id"]
    incident_time = claim_data["incident_time"]

    policy_result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = policy_result.scalar_one_or_none()

    rider_result = await db.execute(select(Rider).where(Rider.id == rider_id))
    rider = rider_result.scalar_one_or_none()

    claim_week = incident_time.strftime("%Y-W%V")
    slot_time_str, slot_start, slot_end = _slot_window(incident_time)

    baseline = None
    if rider:
        baseline_result = await db.execute(
            select(RiderZoneBaseline).where(
                RiderZoneBaseline.rider_id == rider_id,
                RiderZoneBaseline.zone_id == rider.zone_id,
                RiderZoneBaseline.week == claim_week,
                RiderZoneBaseline.slot_time == slot_time_str,
            )
        )
        baseline = baseline_result.scalar_one_or_none()

    snapshot_result = await db.execute(
        select(PlatformSnapshot)
        .where(
            PlatformSnapshot.rider_id == rider_id,
            PlatformSnapshot.time >= slot_start,
            PlatformSnapshot.time <= slot_end,
        )
        .order_by(PlatformSnapshot.time.desc())
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()

    duplicate_claims_result = await db.execute(
        select(func.count())
        .select_from(Claim)
        .where(
            Claim.rider_id == rider_id,
            Claim.policy_id == policy_id,
            Claim.type == "manual",
            Claim.status.in_(["under_review", "approved", "paid", "rejected"]),
        )
    )
    duplicate_claim_count = int(duplicate_claims_result.scalar_one() or 0)

    expected_earnings = baseline.avg_earnings if baseline else claim_data.get("fallback_expected_earnings", 540)
    actual_earnings = snapshot.earnings_current_slot if snapshot else 0
    income_loss = max(expected_earnings - actual_earnings, 0)
    coverage_remaining = max(0, (policy.coverage_limit - policy.coverage_used) if policy else 0)

    return {
        "claim": {
            "disruption_type": claim_data.get("disruption_type"),
            "description": claim_data.get("description", ""),
            "incident_time": incident_time.isoformat(),
            "spam_score": claim_data.get("spam_score", 0),
            "threshold_band": _threshold_band(claim_data.get("spam_score", 0)),
            "default_expectation": _default_expectation_for_band(claim_data.get("spam_score", 0)),
            "gps_distance_m": claim_data.get("gps_distance_m"),
            "geo_valid": claim_data.get("geo_valid"),
            "weather_match": claim_data.get("weather_match"),
            "traffic_match": claim_data.get("traffic_match"),
            "time_delta_min": claim_data.get("time_delta_min", 0),
            "photo_path": claim_data.get("photo_path"),
        },
        "policy": {
            "id": str(policy.id) if policy else None,
            "status": policy.status if policy else None,
            "coverage_limit": policy.coverage_limit if policy else 0,
            "coverage_used": policy.coverage_used if policy else 0,
            "coverage_remaining": coverage_remaining,
        },
        "rider": {
            "id": str(rider.id) if rider else None,
            "name": rider.name if rider else None,
            "zone_id": str(rider.zone_id) if rider and rider.zone_id else None,
            "platform": rider.platform if rider else None,
        },
        "earnings": {
            "claim_week": claim_week,
            "slot_time": slot_time_str,
            "expected_earnings": expected_earnings,
            "actual_earnings": actual_earnings,
            "income_loss": income_loss,
        },
        "validation": {
            "exif_gps_available": claim_data.get("exif_gps_available", False),
            "exif_timestamp_available": claim_data.get("exif_timestamp_available", False),
            "gps_distance_m": claim_data.get("gps_distance_m"),
            "time_delta_min": claim_data.get("time_delta_min", 0),
            "weather_match": claim_data.get("weather_match"),
            "traffic_match": claim_data.get("traffic_match"),
            "rejection_reasons": explain_spam_rejection(
                gps_distance_m=claim_data.get("gps_distance_m", 9999999),
                time_delta_min=claim_data.get("time_delta_min", 0),
                disruption_type=claim_data.get("disruption_type", ""),
                weather_match=bool(claim_data.get("weather_match")),
                traffic_match=bool(claim_data.get("traffic_match")),
            ),
        },
        "duplicates": {
            "manual_claim_count_for_policy": duplicate_claim_count,
        },
    }


def _tool_catalog() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_policy_context",
                "description": "Fetch policy coverage and status facts for this claim.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_earnings_context",
                "description": "Fetch expected earnings, actual earnings, and income-loss facts.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_validation_context",
                "description": "Fetch EXIF, GPS, weather, traffic, and spam-score validation signals.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_duplicate_claim_context",
                "description": "Fetch duplicate and prior-claim indicators for this policy and rider.",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        },
    ]


def _run_tool(name: str, evidence: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "get_policy_context": evidence["policy"],
        "get_earnings_context": evidence["earnings"],
        "get_validation_context": {
            **evidence["claim"],
            **evidence["validation"],
        },
        "get_duplicate_claim_context": evidence["duplicates"],
    }
    if name not in mapping:
        raise ValueError(f"Unsupported tool call: {name}")
    return mapping[name]


def _build_system_prompt() -> str:
    return (
        "You are an automated insurance manual-claim adjudicator. "
        "Decide only approved or rejected. Use the supplied evidence and tool results only. "
        "Threshold guidance: spam_score < 30 is low risk, spam_score >= 70 is high risk. "
        "You may disagree with the threshold expectation only when the evidence strongly supports it. "
        "If evidence is contradictory, missing, or insufficient, reject conservatively. "
        "Return strict JSON with keys decision, confidence, reason_summary, evidence_used, threshold_context. "
        "Do not include markdown. Do not expose chain-of-thought."
    )


def _build_user_prompt(evidence: dict[str, Any]) -> str:
    compact_evidence = {
        "claim": evidence["claim"],
        "validation": evidence["validation"],
        "duplicates": evidence["duplicates"],
    }
    return (
        "Adjudicate this manual claim. "
        "You can call tools for policy, earnings, validation, and duplicate contexts. "
        "Initial evidence:\n"
        f"{json.dumps(compact_evidence, default=str)}"
    )


def _build_final_user_prompt(evidence: dict[str, Any]) -> str:
    return (
        "Adjudicate this manual claim and return only a JSON object. "
        'Schema: {"decision":"approved|rejected","confidence":0.0,"reason_summary":"...","evidence_used":["..."],"threshold_context":{"aligned_with_threshold":true}}. '
        "Reject conservatively if evidence is contradictory or insufficient. "
        "Full evidence:\n"
        f"{json.dumps(evidence, default=str)}"
    )


def _build_nebius_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.NEBIUS_BASE_URL,
        api_key=settings.NEBIUS_API_KEY,
        timeout=settings.NEBIUS_TIMEOUT_SECONDS,
        max_retries=settings.NEBIUS_MAX_RETRIES,
    )


async def _call_nebius_completion(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    client = _build_nebius_client()
    request_kwargs: dict[str, Any] = {
        "model": settings.NEBIUS_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    if tools:
        request_kwargs["tools"] = tools
        request_kwargs["tool_choice"] = "auto"
    response = await client.chat.completions.create(**request_kwargs)
    return response.model_dump()


def _parse_model_decision(payload: dict[str, Any], spam_score: int) -> ManualClaimAdjudication:
    try:
        choice = payload["choices"][0]["message"]
        content = choice.get("content")
        raw_text = _extract_text_content(content)
        json_candidate = _extract_json_candidate(raw_text)
        logger.info("Nebius adjudication raw content: %s", raw_text[:2000])
        parsed = json.loads(json_candidate) if isinstance(json_candidate, str) else json_candidate
        if not isinstance(parsed, dict):
            raise ValueError("Parsed adjudication content is not an object")
        parsed = _normalize_decision_payload(parsed)
        adjudication = ManualClaimAdjudication.model_validate(parsed)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Invalid adjudication payload: {exc}") from exc

    threshold_context = dict(adjudication.threshold_context)
    threshold_context.setdefault("spam_score", spam_score)
    threshold_context.setdefault("band", _threshold_band(spam_score))
    threshold_context.setdefault("default_expectation", _default_expectation_for_band(spam_score))
    threshold_context.setdefault(
        "aligned_with_threshold",
        (threshold_context["default_expectation"] == "approve" and adjudication.decision == "approved")
        or (threshold_context["default_expectation"] == "reject" and adjudication.decision == "rejected")
        or (threshold_context["default_expectation"] == "inspect"),
    )
    adjudication.threshold_context = threshold_context
    return adjudication


async def adjudicate_manual_claim(claim_data: dict, db: AsyncSession) -> ManualClaimAdjudication:
    spam_score = claim_data.get("spam_score", 0)
    evidence = await gather_manual_claim_evidence(claim_data, db)

    if not settings.NEBIUS_API_KEY:
        return _fallback_rejection(
            spam_score,
            "Automated adjudication unavailable because Nebius API key is missing.",
            ["system_fallback", "config_missing"],
        )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": _build_user_prompt(evidence)},
    ]
    tools = _tool_catalog()

    for _ in range(_MAX_TOOL_ROUNDS):
        try:
            payload = await _call_nebius_completion(messages, tools)
            logger.info("Nebius adjudication payload keys: %s", list(payload.keys()))
        except Exception as exc:
            logger.warning("Nebius adjudication request failed: %s", exc)
            return _fallback_rejection(
                spam_score,
                "Automated adjudication failed while calling Nebius Kimi.",
                ["system_fallback", "llm_unavailable"],
            )

        message = payload.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": tool_calls,
                }
            )
            for tool_call in tool_calls:
                name = tool_call.get("function", {}).get("name")
                if not name:
                    continue
                try:
                    tool_result = _run_tool(name, evidence)
                except Exception as exc:
                    tool_result = {"error": str(exc)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", name),
                        "name": name,
                        "content": json.dumps(tool_result, default=str),
                    }
                )
            continue

        try:
            return _parse_model_decision(payload, spam_score)
        except ValueError as exc:
            logger.warning("Nebius adjudication parse failed: %s", exc)
            break

    try:
        final_payload = await _call_nebius_completion(
            [
                {"role": "system", "content": _build_system_prompt()},
                {"role": "user", "content": _build_final_user_prompt(evidence)},
            ],
            tools=None,
        )
        logger.info("Nebius final-pass payload keys: %s", list(final_payload.keys()))
        return _parse_model_decision(final_payload, spam_score)
    except Exception as exc:
        logger.warning("Nebius final-pass adjudication failed: %s", exc)
        return _fallback_rejection(
            spam_score,
            "Automated adjudication returned an invalid decision payload.",
            ["system_fallback", "invalid_llm_response"],
        )

    return _fallback_rejection(
        spam_score,
        "Automated adjudication exceeded the maximum tool-calling rounds.",
        ["system_fallback", "tool_loop_limit"],
    )
