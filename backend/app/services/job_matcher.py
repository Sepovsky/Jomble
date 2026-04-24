from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field, asdict
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert technical recruiter and career coach.
    You will be given a candidate's resume and a job description.
    Analyse how well the candidate fits the role and respond with a
    single JSON object — no markdown fences, no extra text — matching
    this schema exactly:

    {
      "score": <integer 0-100>,
      "matched":      [<skills / qualifications present in BOTH>],
      "missing":      [<skills / qualifications required by job but absent from resume>],
      "resume_extra": [<notable skills in resume not required by this job>],
      "summary":      "<2-3 sentence plain-English assessment with actionable advice>"
    }

    Rules:
    - Evaluate semantically, not lexically. A requirement is matched when the
      resume demonstrates the underlying competency — through projects, job
      descriptions, achievements, or any specific tool or technology that belongs
      to the same category — regardless of whether the exact wording appears.
    - Treat compound or slash-separated requirements as satisfied if the resume
      provides evidence of any meaningful part.
    - A specific instance is always evidence of its general category, and vice
      versa. Use your broad knowledge of the technology landscape to make these
      connections without needing them to be spelled out.
    - Only mark something as "missing" when there is genuinely no evidence —
      direct or indirect — anywhere in the resume.
    - "score" must reflect true demonstrated ability, not keyword presence.
    - Be specific in lists: name the concrete skill, tool, or qualification.
    - Keep every list item short (1-5 words).
    - Return ONLY the JSON object.
""").strip()

_USER_TEMPLATE = textwrap.dedent("""
    ## JOB DESCRIPTION
    {job_text}

    ---

    ## RESUME
    {resume_text}
""").strip()

_MAX_CHARS = 12000


@dataclass
class MatchResult:
    score: float
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    resume_extra: list[str] = field(default_factory=list)
    job_skill_count: int = 0
    resume_skill_count: int = 0
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class JobMatcher:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def match(self, resume_text: str, job_text: str) -> MatchResult:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(
                        job_text=job_text[:_MAX_CHARS],
                        resume_text=resume_text[:_MAX_CHARS],
                    ),
                },
            ],
            temperature=0.2,
        )

        data = json.loads(response.choices[0].message.content or "{}")
        matched = sorted(data.get("matched", []))
        missing = sorted(data.get("missing", []))
        extra = sorted(data.get("resume_extra", []))

        return MatchResult(
            score=float(data.get("score", 0)),
            matched=matched,
            missing=missing,
            resume_extra=extra,
            job_skill_count=len(matched) + len(missing),
            resume_skill_count=len(matched) + len(extra),
            summary=data.get("summary", ""),
        )
