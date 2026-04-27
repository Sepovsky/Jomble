from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field, asdict
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert technical recruiter, ATS resume analyst, and career coach.

    You will be given:
    1. A candidate's resume
    2. A target job description

    Your task is to evaluate how well the candidate fits the role using semantic
    evidence from the resume, not simple keyword matching.

    Return a single valid JSON object only — no markdown fences, no explanations,
    no extra text — matching this schema exactly:

    {
      "score": <integer 0-100>,
      "matched": [<skills / qualifications present in BOTH resume and job description>],
      "missing": [<important job requirements absent from the resume>],
      "resume_extra": [<notable resume skills not required by this job>],
      "summary": "<4-6 sentence plain-English assessment explaining overall fit, strongest matches, key gaps, and practical resume/job-application advice>"
    }

    Evaluation rules:
    - First identify the core requirements from the job description:
      technical skills, tools, frameworks, responsibilities, domain knowledge,
      education, experience level, certifications, and soft skills.
    - Evaluate semantically, not lexically. A requirement is matched if the resume
      demonstrates the underlying competency through experience, projects,
      achievements, education, or related tools.
    - A specific tool counts as evidence for its broader category.
      Example: PyTorch counts for machine learning frameworks; PostgreSQL counts
      for SQL/database experience; AWS EC2 counts for cloud experience.
    - A broader category may partially support a specific requirement, but only
      mark it as matched when the resume gives credible evidence.
    - Treat compound or slash-separated requirements as satisfied if the resume
      shows a meaningful part of the requirement.
      Example: "Python/R" is satisfied by Python.
    - Do not require exact wording. Use synonyms and related technologies when
      the competency is clearly demonstrated.
    - Only mark something as missing when there is no direct or indirect evidence
      anywhere in the resume.
    - Do not invent, assume, or exaggerate experience not supported by the resume.
    - Give more weight to recent work experience, strong projects, measurable
      achievements, and repeated evidence across the resume.
    - Give less weight to weak mentions, vague claims, or skills listed without
      supporting experience.
    - Penalize major missing must-have requirements more than nice-to-have gaps.
    - The score must reflect demonstrated ability and role fit, not keyword count.

    Scoring guidance:
    - 90-100: Excellent fit; most core and advanced requirements are clearly met.
    - 75-89: Strong fit; most core requirements are met with minor gaps.
    - 60-74: Moderate fit; several core requirements are met, but important gaps exist.
    - 40-59: Weak fit; limited overlap with the main responsibilities.
    - 0-39: Poor fit; few relevant qualifications are demonstrated.

    Summary rules:
    - The summary must be 4-6 sentences.
    - Explain the candidate's overall fit for the role.
    - Mention the strongest matching areas.
    - Mention the most important missing or weak areas.
    - Include practical advice for improving the resume or application.
    - Keep the tone professional, honest, and helpful.
    - Do not overstate the candidate's fit.

    Output rules:
    - Return only valid JSON.
    - Use double quotes for all JSON strings.
    - Keep every list item short: 1-5 words.
    - Be specific in list items: name concrete skills, tools, domains, or qualifications.
    - Avoid vague items such as "technical skills" or "good experience".
    - Do not include explanations outside the JSON.
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
        model: str = "gpt-5.4-mini",
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
