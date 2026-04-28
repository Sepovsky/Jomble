from __future__ import annotations

import json
import logging
import os
import textwrap
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = textwrap.dedent("""
    You are a resume optimization expert.

    You will receive:
      1. A LaTeX resume source
      2. A job description
      3. A recruiter's assessment of the candidate's fit
      4. A list of skills the resume is missing for this role

    Your task is to suggest targeted text improvements as a list of string
    replacements. You must NOT rewrite or return the full resume.

    OUTPUT FORMAT — return ONLY a valid JSON object, no markdown fences:
    {
      "replacements": [
        {"original": "<exact text from resume>", "improved": "<better version>"},
        ...
      ]
    }

    WHAT YOU MAY REPLACE:
    - Bullet point text (the human-readable content inside \\item or \\resumeItem)
    - Skills list text (the text inside a skills section)
    - Summary or objective paragraph text

    WHAT YOU MUST NEVER CHANGE:
    - Employer names, company names
    - Job titles / role names
    - Employment dates or date ranges
    - School names, degree names, education dates
    - Project names
    - Candidate name, email, phone, location, links
    - Award or publication names
    - Any LaTeX commands, environments, or macros
    - Any numbers or metrics not present in the original

    RULES FOR REPLACEMENTS:
    - "original" must be copied VERBATIM from the resume — it must match exactly.
    - "improved" must preserve the same underlying fact, just with stronger
      action verbs, better ATS alignment, or job-relevant emphasis.
    - Only include a replacement when you can genuinely improve it.
    - Do NOT invent tools, technologies, metrics, or achievements.
    - Do NOT add a skill the candidate does not already demonstrate.
    - If a missing skill is genuinely evidenced in the resume content, you may
      clarify the existing text to name it — but do not fabricate it.
    - Keep every "improved" string at a similar length to "original".
    - Return an empty replacements list if no safe improvements exist.
""").strip()

_USER_TEMPLATE = textwrap.dedent("""
    ## JOB DESCRIPTION
    {job_text}

    ---

    ## RECRUITER'S ASSESSMENT
    {summary}

    ---

    ## MISSING SKILLS TO ADDRESS
    {missing}

    ---

    ## LATEX RESUME SOURCE
    {tex_content}

    ---

    Now return the JSON replacements object.
""").strip()

_VALIDATION_PROMPT = textwrap.dedent("""
    You are a strict resume validation assistant.

    Compare the original resume and the tailored resume.

    Return only valid JSON with this schema:

    {
      "is_safe": <true or false>,
      "hallucinations": [<unsupported additions or changed facts>],
      "changed_sensitive_facts": [<changed employers, schools, dates, titles, degrees, awards, links>],
      "unsupported_skills": [<skills added without evidence>],
      "recommendation": "<accept, reject, or regenerate>"
    }

    Rules:
    - Mark is_safe as false if any employer, school, job title, degree, date,
      project, award, metric, or major skill was invented or changed without
      support from the original resume.
    - The job description is not evidence about the candidate.
    - The original resume is the only source of truth.
    - Be strict.
""").strip()

_MAX_CHARS = 12000


class ResumeTailor:
    def __init__(
        self,
        model: str = "gpt-5.5",
        validation_model: str = "gpt-5.4-mini",
        api_key: Optional[str] = None,
    ) -> None:
        self.model = model
        self.validation_model = validation_model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def tailor(
        self,
        tex_content: str,
        job_text: str,
        missing: list[str],
        summary: str = "",
    ) -> tuple[str, list[dict]]:
        """Return (tailored_tex, applied_replacements)."""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        user_content = _USER_TEMPLATE.format(
            job_text=job_text[:_MAX_CHARS],
            summary=summary if summary else "No assessment provided.",
            missing=", ".join(missing) if missing else "none identified",
            tex_content=tex_content[:_MAX_CHARS],
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        # Parse replacements JSON
        try:
            data = json.loads(raw)
            replacements: list[dict] = data.get("replacements", [])
        except json.JSONDecodeError:
            logger.warning("tailor() — LLM returned non-JSON, no replacements applied:\n%s", raw[:500])
            return tex_content, []

        # Apply each replacement to the ORIGINAL source (never modify structure)
        result = tex_content
        applied_list: list[dict] = []
        skipped = 0
        for item in replacements:
            original = item.get("original", "")
            improved = item.get("improved", "")
            if not original or not improved or original == improved:
                continue
            if original not in result:
                logger.warning("tailor() — replacement not found in tex (skipped): %r", original[:80])
                skipped += 1
                continue
            result = result.replace(original, improved, 1)
            applied_list.append(item)

        logger.info(
            "tailor() done — %d replacements applied, %d skipped (not found in source)",
            len(applied_list), skipped,
        )
        return result, applied_list

    def summarize(
        self,
        applied_replacements: list[dict],
        missing: list[str],
        recruiter_summary: str,
    ) -> dict[str, Any]:
        """Generate short-term change descriptions and long-term improvement advice."""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        replacements_text = "\n".join(
            f'- Changed: "{r.get("original", "")[:120]}" → "{r.get("improved", "")[:120]}"'
            for r in applied_replacements
        ) or "No changes were applied."

        user_content = textwrap.dedent(f"""
            ## CHANGES APPLIED TO THE RESUME
            {replacements_text}

            ---

            ## MISSING SKILLS (from job match)
            {", ".join(missing) if missing else "none identified"}

            ---

            ## RECRUITER'S ASSESSMENT
            {recruiter_summary or "No assessment provided."}
        """).strip()

        system = textwrap.dedent("""
            You are a resume improvement advisor.

            You will receive:
              1. A list of text replacements that were applied to a resume
              2. Skills the resume is missing for the target job
              3. A recruiter's assessment of the candidate

            Return ONLY a valid JSON object — no markdown fences — with this schema:
            {
              "short_term": ["<plain-English description of each change made>", ...],
              "long_term":  ["<concrete actionable improvement for next 3-12 months>", ...]
            }

            short_term rules:
            - Describe each replacement in one plain-English sentence (no LaTeX).
            - Max 10 items.
            - If no changes were applied, return a single item:
              "No changes were needed — your resume already aligns well with this role."

            long_term rules:
            - Focus on skills, tools, certifications, or project types to build.
            - Be specific: name actual tools, platforms, or credentials.
            - Max 6 items.
            - Base advice on the missing skills and recruiter assessment.
        """).strip()

        response = client.chat.completions.create(
            model=self.validation_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_content},
            ],
        )

        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("summarize() — failed to parse JSON: %s", raw[:300])
            return {"short_term": [], "long_term": []}

    def validate(
        self,
        original_tex: str,
        tailored_tex: str,
    ) -> dict[str, Any]:
        """Compare original and tailored LaTeX and return a safety report."""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        # Only send the differing lines to keep the prompt focused
        orig_lines = set(original_tex.splitlines())
        tail_lines = set(tailored_tex.splitlines())
        added = "\n".join(tail_lines - orig_lines)
        removed = "\n".join(orig_lines - tail_lines)

        user_content = textwrap.dedent(f"""
            ## LINES REMOVED FROM ORIGINAL
            {removed[:_MAX_CHARS] or "(none)"}

            ---

            ## LINES ADDED IN TAILORED VERSION
            {added[:_MAX_CHARS] or "(none)"}
        """).strip()

        response = client.chat.completions.create(
            model=self.validation_model,
            messages=[
                {"role": "system", "content": _VALIDATION_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.startswith("```")
            ).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "is_safe": False,
                "hallucinations": [],
                "changed_sensitive_facts": [],
                "unsupported_skills": [],
                "recommendation": "reject",
                "parse_error": raw,
            }
