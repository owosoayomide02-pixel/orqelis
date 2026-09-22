from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from orqelis_security.redaction import redact_mapping

def _parse_model_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"explanation": text}
    return parsed if isinstance(parsed, dict) else {"explanation": str(parsed)}


ROLES = {
    "sentinel": "You are Orqelis Sentinel. Triage alerts. Identify what needs investigation. Do not invent telemetry.",
    "hunter": "You are Orqelis Hunter. Search the provided telemetry for suspicious patterns. Cite only provided evidence.",
    "analyst": "You are Orqelis Analyst. Investigate the incident. Produce a timeline, likely root cause, and next investigative steps.",
    "auditor": "You are Orqelis Auditor. Review device security posture and configuration. Flag missing controls.",
    "fixer": "You are Orqelis Fixer. Recommend defensive remediation only. Never suggest offensive exploitation. Prefer reversible, least-privilege changes.",
}


@dataclass
class AnalysisResult:
    provider: str
    model: str
    output: dict[str, Any]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_cents: int = 0


class AIGateway:
    def __init__(
        self,
        *,
        provider: str = "heuristic",
        api_key: str = "",
        base_url: str = "",
        model: str = "",
    ) -> None:
        self.provider = provider or "heuristic"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model or "gpt-4o-mini"

    def analyze(self, *, role: str, subject_type: str, payload: dict[str, Any]) -> AnalysisResult:
        redacted = redact_mapping(payload)
        role_key = (role or "analyst").lower()
        if role_key not in ROLES:
            role_key = "analyst"
        if not self.api_key:
            return self._heuristic(role_key, subject_type, redacted)
        try:
            return self._openai_compatible(role_key, subject_type, redacted)
        except Exception as exc:
            fallback = self._heuristic(role_key, subject_type, redacted)
            fallback.output["provider_error"] = str(exc)[:300]
            fallback.output["fallback"] = True
            return fallback

    def _heuristic(self, role: str, subject_type: str, payload: dict[str, Any]) -> AnalysisResult:
        title = str(payload.get("title") or subject_type)
        severity = str(payload.get("severity") or "medium")
        evidence = payload.get("evidence") or payload.get("evidence_json") or {}
        output = {
            "role": role,
            "explanation": (
                f"{role.title()} review of {subject_type} '{title}'. "
                f"Reported severity is {severity}. This analysis used the local heuristic engine because no AI provider key is configured."
            ),
            "timeline": [
                {"step": "Telemetry received", "detail": "Authorized customer security data was provided to Orqelis."},
                {"step": "Detection", "detail": "A rule or correlation engine produced this finding."},
                {"step": "Review", "detail": "A human should confirm impact before any high-risk action."},
            ],
            "priority": severity,
            "recommended_remediation": [
                "Validate the evidence against the affected device.",
                "Confirm the activity was not expected administration.",
                "If confirmed, follow the recommended next step on the alert.",
            ],
            "confidence": 0.4,
            "questions_answered": "Analysis is limited to the supplied tenant data.",
            "evidence_used": evidence if isinstance(evidence, dict) else {"note": "see source record"},
            "heuristic": True,
        }
        return AnalysisResult(provider="heuristic", model="local-heuristic", output=output)

    def _openai_compatible(self, role: str, subject_type: str, payload: dict[str, Any]) -> AnalysisResult:
        url = self.base_url or "https://api.openai.com/v1"
        body = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": ROLES[role] + " Return JSON with keys: explanation, timeline, priority, recommended_remediation, confidence."},
                {
                    "role": "user",
                    "content": (
                        f"Subject type: {subject_type}\n"
                        "Use only this redacted authorized security data. Do not perform or suggest unauthorized access.\n"
                        + json.dumps(payload)[:12000]
                    ),
                },
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=45.0) as client:
            response = client.post(f"{url}/chat/completions", headers=headers, json=body)
            if response.status_code >= 400:
                body.pop("response_format", None)
                response = client.post(f"{url}/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _parse_model_json(content)
        usage = data.get("usage") or {}
        return AnalysisResult(
            provider=self.provider,
            model=self.model,
            output=parsed if isinstance(parsed, dict) else {"explanation": str(parsed)},
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
