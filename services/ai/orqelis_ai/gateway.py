from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx
from orqelis_security.redaction import redact_mapping
from pydantic import BaseModel, ConfigDict, Field, ValidationError


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


ROLE_PROMPTS = {
    "sentinel": (
        "You are Sentinel, a security triage assistant. Given a batch of findings, identify which "
        "require immediate escalation. Return JSON with keys: explanation, priority, confidence, "
        "escalations (list of finding titles)."
    ),
    "hunter": (
        "You are Hunter, interpreting raw scan output. Given normalized findings from a domain scan, "
        "explain what each means in plain language and assign a real-world exploitability score. "
        "Return JSON with keys: explanation, priority, confidence, recommended_remediation."
    ),
    "hunter_analysis": (
        "You are Hunter, interpreting raw scan output. Given normalized findings from a domain scan, "
        "explain what each means in plain language and assign a real-world exploitability score. "
        "Return JSON with keys: explanation, priority, confidence, recommended_remediation."
    ),
    "analyst": (
        "You are Analyst. Given a single finding, explain it to a technical but non-specialist reader. "
        "Return JSON with keys: explanation, severity_assessment, confidence, timeline, recommended_remediation."
    ),
    "auditor": (
        "You are Auditor. Given a list of findings for a domain, write a client-facing report section. "
        "Tone: professional, direct, not alarmist. Return JSON with keys: explanation, report, priority, confidence."
    ),
    "fixer": (
        "You are Fixer. Given a finding, propose a concrete remediation as a diff or config change. "
        "Do not suggest anything that requires infrastructure you cannot see. Flag if manual investigation "
        "is needed. Return JSON with keys: explanation, fix_type, description, diff, confidence, "
        "recommended_remediation. Never claim the fix was applied."
    ),
}

# Back-compat alias
ROLES = ROLE_PROMPTS


class RoleOutputSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    explanation: str = Field(default="")
    confidence: float = Field(default=0.5, ge=0, le=1)


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
        model_light: str = "",
        model_heavy: str = "",
    ) -> None:
        self.provider = provider or "heuristic"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model or "gpt-4o-mini"
        self.model_light = model_light or os.environ.get("AI_MODEL_LIGHT", "") or self.model
        self.model_heavy = model_heavy or os.environ.get("AI_MODEL_HEAVY", "") or self.model

    def model_for_role(self, role: str) -> str:
        mapping = {
            "sentinel": self.model_light,
            "hunter": self.model_heavy,
            "hunter_analysis": self.model_heavy,
            "analyst": self.model_heavy,
            "auditor": self.model_heavy,
            "fixer": self.model_heavy,
        }
        return mapping.get(role, self.model) or self.model

    def analyze(self, *, role: str, subject_type: str, payload: dict[str, Any]) -> AnalysisResult:
        redacted = redact_mapping(payload)
        role_key = (role or "analyst").lower()
        if role_key not in ROLE_PROMPTS:
            role_key = "analyst"
        if not self.api_key:
            return self._heuristic(role_key, subject_type, redacted)
        try:
            return self._openai_compatible(role_key, subject_type, redacted, retry_fix=False)
        except Exception as exc:
            try:
                return self._openai_compatible(role_key, subject_type, redacted, retry_fix=True)
            except Exception:
                fallback = self._heuristic(role_key, subject_type, redacted)
                fallback.output["provider_error"] = str(exc)[:300]
                fallback.output["fallback"] = True
                fallback.output["analysis_unavailable"] = True
                return fallback

    def _validate(self, parsed: dict[str, Any]) -> dict[str, Any]:
        try:
            return RoleOutputSchema.model_validate(parsed).model_dump()
        except ValidationError:
            # Merge defaults so callers always get explanation/confidence
            out = dict(parsed)
            out.setdefault("explanation", str(parsed)[:2000])
            out.setdefault("confidence", 0.4)
            return out

    def _heuristic(self, role: str, subject_type: str, payload: dict[str, Any]) -> AnalysisResult:
        title = str(payload.get("title") or subject_type)
        severity = str(payload.get("severity") or "medium")
        evidence = payload.get("evidence") or payload.get("evidence_json") or {}
        domain = payload.get("domain")
        findings = payload.get("findings")
        if role == "fixer":
            output = {
                "role": role,
                "explanation": f"Proposed remediation draft for '{title}'. Requires human approval before any change.",
                "fix_type": "config_change",
                "description": f"Review and harden configuration related to {title}.",
                "diff": (
                    f"# Manual review required for {title}\n"
                    f"# severity: {severity}\n"
                    "# Apply only after human approval — Orqelis never auto-applies fixes.\n"
                ),
                "priority": severity,
                "severity_assessment": severity,
                "recommended_remediation": [
                    "Validate the finding against the live asset.",
                    "Apply the least-privilege change in a change window.",
                    "Re-scan to confirm the issue is resolved.",
                ],
                "confidence": 0.45,
                "requires_human_approval": True,
                "heuristic": True,
            }
        elif role == "auditor":
            count = len(findings) if isinstance(findings, list) else 0
            output = {
                "role": role,
                "explanation": (
                    f"Client-facing summary for {domain or subject_type}: reviewed {count} findings. "
                    f"Highest reported severity in scope is {severity}."
                ),
                "report": (
                    f"# Security assessment — {domain or title}\n\n"
                    f"This report summarizes {count} findings identified during authorized scanning. "
                    "Remediation recommendations are advisory and require customer approval.\n"
                ),
                "priority": severity,
                "confidence": 0.5,
                "heuristic": True,
            }
        else:
            output = {
                "role": role,
                "explanation": (
                    f"{role.title()} review of {subject_type} '{title}'. "
                    f"Reported severity is {severity}. This analysis used the local heuristic engine "
                    "because no AI provider key is configured."
                ),
                "timeline": [
                    {"step": "Telemetry received", "detail": "Authorized customer security data was provided to Orqelis."},
                    {"step": "Detection", "detail": "A rule or scan engine produced this finding."},
                    {"step": "Review", "detail": "A human should confirm impact before any high-risk action."},
                ],
                "priority": severity,
                "severity_assessment": severity,
                "recommended_remediation": [
                    "Validate the evidence against the affected asset.",
                    "Confirm the activity was not expected administration.",
                    "If confirmed, follow the recommended next step on the alert.",
                ],
                "confidence": 0.4,
                "questions_answered": "Analysis is limited to the supplied tenant data.",
                "evidence_used": evidence if isinstance(evidence, dict) else {"note": "see source record"},
                "heuristic": True,
            }
            if payload.get("auto_detected"):
                output["auto_detected"] = True
        return AnalysisResult(provider="heuristic", model="local-heuristic", output=output)

    def _openai_compatible(
        self,
        role: str,
        subject_type: str,
        payload: dict[str, Any],
        *,
        retry_fix: bool,
    ) -> AnalysisResult:
        url = self.base_url or "https://api.openai.com/v1"
        model = self.model_for_role(role)
        system = ROLE_PROMPTS[role]
        if retry_fix:
            system += (
                " Your last response was invalid JSON. Return ONLY valid JSON matching the schema "
                "described in the system prompt."
            )
        body = {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Subject type: {subject_type}\n"
                        "Use only this redacted authorized security data. "
                        "Do not perform or suggest unauthorized access.\n"
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
        if not isinstance(parsed, dict) or "explanation" not in parsed:
            if not retry_fix:
                return self._openai_compatible(role, subject_type, payload, retry_fix=True)
            raise ValueError("Model returned invalid JSON schema")
        validated = self._validate(parsed if isinstance(parsed, dict) else {"explanation": str(parsed)})
        usage = data.get("usage") or {}
        return AnalysisResult(
            provider=self.provider,
            model=model,
            output=validated,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
