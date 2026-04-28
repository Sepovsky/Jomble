import base64
import io
import json
import logging
import os
import subprocess
import tempfile
import zipfile

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services.resume_tailor import ResumeTailor

router = APIRouter()


def _extract_tex(data: bytes, filename: str) -> tuple[str, dict[str, bytes]]:
    """Return (tex_source, supporting_files) from a .tex or .zip upload.

    supporting_files maps bare filename → bytes for every non-.tex file in the
    archive (custom .cls, .sty, images, etc.) so they can be written alongside
    the .tex when compiling.
    """
    if filename.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            tex_names = [n for n in zf.namelist() if n.endswith(".tex")]
            if not tex_names:
                raise HTTPException(
                    status_code=422,
                    detail="No .tex file found inside the ZIP archive.",
                )
            preferred = next(
                (n for n in tex_names if n.split("/")[-1] in ("main.tex", "resume.tex")),
                tex_names[0],
            )
            tex_source = zf.read(preferred).decode("utf-8", errors="replace")

            # Collect all other files (cls, sty, images, bib, …)
            supporting: dict[str, bytes] = {}
            for name in zf.namelist():
                if name == preferred or name.endswith("/"):
                    continue
                bare = os.path.basename(name)
                if bare:
                    supporting[bare] = zf.read(name)

            return tex_source, supporting

    if filename.endswith(".tex"):
        return data.decode("utf-8", errors="replace"), {}

    raise HTTPException(
        status_code=400,
        detail="Please upload a .tex file or a .zip archive containing a .tex file.",
    )


def _compile_pdf(tex_content: str, supporting: dict[str, bytes]) -> bytes | None:
    """Compile LaTeX source to PDF. Returns PDF bytes or None on failure."""
    import shutil
    if not shutil.which("pdflatex"):
        logger.warning("pdflatex not found — skipping PDF compilation")
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write supporting files first (.cls, .sty, images, etc.)
        for name, file_bytes in supporting.items():
            with open(os.path.join(tmpdir, name), "wb") as f:
                f.write(file_bytes)

        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", tmpdir,
            tex_path,
        ]
        # Run twice so references, TOC, etc. resolve correctly
        for run in range(1, 3):
            proc = subprocess.run(cmd, capture_output=True, timeout=60)
            if proc.returncode != 0:
                logger.warning(
                    "pdflatex run %d exited %d:\n%s",
                    run, proc.returncode,
                    proc.stdout.decode("utf-8", errors="replace")[-3000:],
                )

        pdf_path = os.path.join(tmpdir, "resume.pdf")
        if not os.path.exists(pdf_path):
            logger.error("PDF not produced after pdflatex runs")
            return None

        with open(pdf_path, "rb") as f:
            return f.read()


def _build_zip(
    tex_content: str,
    pdf_bytes: bytes | None,
    validation: dict | None = None,
) -> bytes:
    """Bundle .tex, (optionally) .pdf, and validation report into a ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tailored_resume.tex", tex_content.encode("utf-8"))
        if pdf_bytes:
            zf.writestr("tailored_resume.pdf", pdf_bytes)
        if validation is not None:
            zf.writestr(
                "validation_report.json",
                json.dumps(validation, indent=2).encode("utf-8"),
            )
    return buf.getvalue()


@router.post("/tailor")
async def tailor(
    tex_file: UploadFile = UploadFile(...),
    job_text: str = Form(...),
    missing: str = Form("[]"),
    summary: str = Form(""),
) -> JSONResponse:
    raw = await tex_file.read()
    original_tex, supporting = _extract_tex(raw, tex_file.filename or "")

    try:
        missing_list: list[str] = json.loads(missing)
    except Exception:
        missing_list = []

    tailor_svc = ResumeTailor()

    candidate, applied_replacements = tailor_svc.tailor(
        tex_content=original_tex,
        job_text=job_text,
        missing=missing_list,
        summary=summary,
    )

    # Guard against empty LLM response
    tailored_tex = candidate if candidate.strip() else original_tex

    validation = tailor_svc.validate(
        original_tex=original_tex,
        tailored_tex=tailored_tex,
    )

    improvement_summary = tailor_svc.summarize(
        applied_replacements=applied_replacements,
        missing=missing_list,
        recruiter_summary=summary,
    )

    logger.info(
        "Tailor complete — original=%d tailored=%d is_safe=%s short_term=%d long_term=%d",
        len(original_tex), len(tailored_tex),
        validation.get("is_safe"),
        len(improvement_summary.get("short_term", [])),
        len(improvement_summary.get("long_term", [])),
    )

    pdf_bytes = _compile_pdf(tailored_tex, supporting)
    zip_bytes = _build_zip(tailored_tex, pdf_bytes, validation)

    return JSONResponse({
        "zip_b64":    base64.b64encode(zip_bytes).decode(),
        "short_term": improvement_summary.get("short_term", []),
        "long_term":  improvement_summary.get("long_term", []),
    })
