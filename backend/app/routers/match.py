import tempfile
import os

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.schemas import MatchResponse
from app.services.html_to_text import HTMLToTextConverter
from app.services.job_fetcher import JobHTMLFetcher
from app.services.job_matcher import JobMatcher
from app.services.resume_parser import ResumeParser

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match(
    job_url: str = Form(...),
    resume: UploadFile = UploadFile(...),
) -> MatchResponse:
    if not resume.filename or not resume.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    try:
        page = JobHTMLFetcher().fetch_html(job_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not fetch job URL: {e}")

    job_text = HTMLToTextConverter().convert(page["html"])

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
    return MatchResponse(**result.to_dict(), job_text=job_text)
