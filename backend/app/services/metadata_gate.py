"""
LLM checks whether a job posting satisfies the user's stated preferences
before running resume ↔ job matching.
"""

from __future__ import annotations

import json
import logging
import os
import textwrap
from dataclasses import dataclass, asdict
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = textwrap.dedent("""
    You are a job-posting analyst. Compare the job description to the candidate's
    stated preferences (location, remote policy, languages, work authorization,
    salary floor, employment type, seniority).

    Return a single JSON object only — no markdown fences:

    {
      "satisfied": <true if the role is compatible with the user's hard requirements>,
      "blockers": [<short strings: hard mismatches that mean the user should not pursue this role>],
      "warnings": [<short strings: soft mismatches or unclear points to be aware of>],
      "summary": "<2-4 sentences in plain English>"
    }

    Rules:
    - "satisfied" must be false if ANY hard requirement clearly conflicts with the job
      (e.g. user requires fully remote but job is onsite-only in another country;
      user needs visa sponsorship but posting says no sponsorship;
      user's salary floor is stated in the job and is clearly below it if numbers exist).
    - If the posting does not mention something (e.g. salary), do not treat absence as a
      blocker — add a warning instead.
    - Language: if the user lists languages they speak and the job requires a language
      the user did not list at a required level, that can be a blocker. If unclear, warning.
    - Remote policy: map job wording (remote, hybrid, onsite) against meta_remote_policy.
    - Seniority: if the job is clearly entry-level and user targets lead, or vice versa,
      use warnings unless clearly incompatible (then blocker).
    - Employment type: mismatch between user's preference and job type (contract vs FTE)
      can be a blocker if explicit on both sides.
    - Be conservative: when in doubt, prefer warnings over blockers.
""").strip()

_USER_TEMPLATE = textwrap.dedent("""
    ## USER PREFERENCES (metadata)
    {metadata_json}

    ---

    ## JOB DESCRIPTION (excerpt)
    {job_text}
""").strip()

_MAX_CHARS = 12000


@dataclass
class MetadataGateResult:
    satisfied: bool
    blockers: list[str]
    warnings: list[str]
    summary: str
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MetadataGate:
    def __init__(
        self,
        model: str = "gpt-5.4-mini",
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def check(self, job_text: str, metadata: dict[str, Any]) -> MetadataGateResult:
        from openai import OpenAI

        # Skip LLM if user left everything at defaults / empty
        if _is_empty_metadata(metadata):
            return MetadataGateResult(
                satisfied=True,
                blockers=[],
                warnings=[],
                summary="No preferences were set; skipping the preference check.",
                skipped=True,
            )

        client = OpenAI(api_key=self._api_key)
        user_content = _USER_TEMPLATE.format(
            metadata_json=json.dumps(metadata, indent=2),
            job_text=job_text[:_MAX_CHARS],
        )

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("metadata_gate: invalid JSON, defaulting to satisfied")
            return MetadataGateResult(
                satisfied=True,
                blockers=[],
                warnings=["Could not verify preferences automatically."],
                summary="Preference check was inconclusive; review the job posting manually.",
                skipped=False,
            )

        return MetadataGateResult(
            satisfied=bool(data.get("satisfied", True)),
            blockers=list(data.get("blockers", []) or []),
            warnings=list(data.get("warnings", []) or []),
            summary=str(data.get("summary", "")).strip()
            or "Review how this role aligns with your preferences.",
            skipped=False,
        )


def _is_empty_metadata(m: dict[str, Any]) -> bool:
    """True when user did not fill meaningful preference fields."""
    loc = (m.get("location_preference") or "").strip()
    lang_speak = (m.get("languages_speak") or "").strip()
    lang_req = (m.get("languages_required") or "").strip()
    sal = (m.get("salary_min") or "").strip()

    remote = m.get("remote_policy") or "any"
    sponsor = m.get("sponsorship") or "no_preference"
    emp = m.get("employment_type") or "any"
    sen = m.get("seniority") or "any"

    has_text = bool(loc or lang_speak or lang_req or sal)
    has_non_default = (
        remote != "any"
        or sponsor != "no_preference"
        or emp != "any"
        or sen != "any"
    )
    return not has_text and not has_non_default
