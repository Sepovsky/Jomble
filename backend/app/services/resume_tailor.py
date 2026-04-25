from __future__ import annotations

import os
import textwrap
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

_SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert resume writer specialising in LaTeX resumes.
    You will receive:
      1. A LaTeX resume source (.tex)
      2. A job description
      3. A list of skills/qualifications the resume is currently missing for this role

    Your task is to tailor the LaTeX resume so it better matches the job by:
    - Rewriting bullet points in experience and project sections to highlight
      relevant competencies and mirror the language of the job description.
    - Expanding or reordering the skills section to surface relevant skills the
      candidate already has but may have understated.
    - Rewriting the summary / objective (if present) to target this specific role.
    - Where a "missing" skill is genuinely demonstrated by the candidate's
      experience (even if not named explicitly), add it naturally to the text.
    - Do NOT invent experience or skills the candidate does not have.

    STRICT LaTeX rules — you must follow these exactly:
    - Return ONLY the complete, valid LaTeX source code.
    - Do NOT wrap the output in markdown fences or add any explanation.
    - Preserve every LaTeX command, environment, package import, and document
      structure exactly as in the original.
    - Only change the human-readable text content inside LaTeX commands.
""").strip()

_USER_TEMPLATE = textwrap.dedent("""
    ## JOB DESCRIPTION
    {job_text}

    ---

    ## MISSING SKILLS TO ADDRESS
    {missing}

    ---

    ## LATEX RESUME SOURCE
    {tex_content}
""").strip()

_MAX_CHARS = 12000


class ResumeTailor:
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
    ) -> None:
        # gpt-4o gives much better LaTeX preservation than gpt-4o-mini
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def tailor(
        self,
        tex_content: str,
        job_text: str,
        missing: list[str],
    ) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)

        user_content = _USER_TEMPLATE.format(
            job_text=job_text[:_MAX_CHARS],
            missing=", ".join(missing) if missing else "none identified",
            tex_content=tex_content[:_MAX_CHARS],
        )

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )

        result = (response.choices[0].message.content or "").strip()

        # Strip any accidental markdown fences the model might add
        if result.startswith("```"):
            lines = result.splitlines()
            result = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        return result
