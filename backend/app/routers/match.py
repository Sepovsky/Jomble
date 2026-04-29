import tempfile
import os

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.schemas import MatchResponse
from app.services.html_to_text import HTMLToTextConverter
from app.services.job_fetcher import JobHTMLFetcher
from app.services.job_matcher import JobMatcher
from app.services.metadata_gate import MetadataGate
from app.services.resume_parser import ResumeParser

router = APIRouter()


def _parse_metadata(
    location_preference: str,
    remote_policy: str,
    languages_speak: str,
    languages_required: str,
    sponsorship: str,
    salary_min: str,
    salary_currency: str,
    employment_type: str,
    seniority: str,
) -> dict:
    return {
        "location_preference": location_preference.strip(),
        "remote_policy": remote_policy.strip() or "any",
        "languages_speak": languages_speak.strip(),
        "languages_required": languages_required.strip(),
        "sponsorship": sponsorship.strip() or "no_preference",
        "salary_min": salary_min.strip(),
        "salary_currency": (salary_currency or "USD").strip(),
        "employment_type": employment_type.strip() or "any",
        "seniority": seniority.strip() or "any",
    }


@router.post("/match", response_model=MatchResponse)
async def match(
    job_url: str = Form(...),
    resume: UploadFile = UploadFile(...),
    location_preference: str = Form(""),
    remote_policy: str = Form("any"),
    languages_speak: str = Form(""),
    languages_required: str = Form(""),
    sponsorship: str = Form("no_preference"),
    salary_min: str = Form(""),
    salary_currency: str = Form("USD"),
    employment_type: str = Form("any"),
    seniority: str = Form("any"),
) -> MatchResponse:
    if not resume.filename or not resume.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    try:
        page = JobHTMLFetcher().fetch_html(job_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch job URL: {e}")

    job_text = HTMLToTextConverter().convert(page["html"])

    metadata = _parse_metadata(
        location_preference,
        remote_policy,
        languages_speak,
        languages_required,
        sponsorship,
        salary_min,
        salary_currency,
        employment_type,
        seniority,
    )

    gate = MetadataGate().check(job_text, metadata)

    if not gate.satisfied:
        await resume.read()
        block_text = "; ".join(gate.blockers) if gate.blockers else "Preferences conflict."
        return MatchResponse(
            score=0.0,
            matched=[],
            missing=[],
            resume_extra=[],
            job_skill_count=0,
            resume_skill_count=0,
            summary=(
                f"This posting does not align with your stated preferences.\n\n"
                f"{gate.summary}\n\nBlockers: {block_text}"
            ),
            job_text=job_text,
            metadata_satisfied=False,
            metadata_blockers=gate.blockers,
            metadata_warnings=gate.warnings,
            metadata_summary=gate.summary,
            metadata_match_skipped=True,
            metadata_skipped=gate.skipped,
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(await resume.read())
        tmp_path = tmp.name

    try:
        resume_text = ResumeParser().parse(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse resume: {e}")
    finally:
        os.unlink(tmp_path)

    result = JobMatcher().match(resume_text, job_text)

    warn_suffix = ""
    if gate.warnings:
        warn_suffix = (
            "\n\nPreference notes: " + " ".join(gate.warnings)
        )

    combined_summary = result.summary + warn_suffix

    return MatchResponse(
        **result.to_dict(),
        summary=combined_summary,
        job_text=job_text,
        metadata_satisfied=True,
        metadata_blockers=[],
        metadata_warnings=gate.warnings,
        metadata_summary=gate.summary,
        metadata_match_skipped=False,
        metadata_skipped=gate.skipped,
    )
