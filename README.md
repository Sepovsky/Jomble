# Jomble

An AI-powered job-matching and resume-tailoring application. Paste a job posting URL, upload your resume PDF, and get an instant match score with actionable feedback. Optionally upload your LaTeX resume to have it tailored for the role.

---

## Features

- **Job Matching** — Scrapes any job posting URL and semantically matches it against your resume using GPT-4o-mini. Returns a score (0–100), matched skills, missing skills, and a plain-English recruiter assessment.
- **Resume Tailoring** — Upload your LaTeX resume (`.tex` or `.zip`). The LLM suggests targeted text improvements as string-level patches — it never rewrites structure or invents fake experience.
- **Post-Tailoring Validation** — A second LLM pass checks the tailored resume for hallucinations, changed facts, and unsupported skills before delivery.
- **ZIP Download** — Get `tailored_resume.tex`, `tailored_resume.pdf` (when compiled), and `validation_report.json` in one download.
- **Fully Dockerised** — One command to run the full stack.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JS served by Nginx |
| Backend | Python, FastAPI |
| LLM | OpenAI GPT-4o / GPT-4o-mini |
| Scraping | Playwright (Chromium), BeautifulSoup |
| PDF Parsing | PyMuPDF (fitz) |
| LaTeX Compilation | pdflatex (TeX Live) |
| Containerisation | Docker, Docker Compose |

---

## Project Structure

```
Jomble/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── schemas.py               # Pydantic models
│   │   ├── routers/
│   │   │   ├── match.py             # POST /api/match
│   │   │   └── tailor.py            # POST /api/tailor
│   │   └── services/
│   │       ├── job_fetcher.py       # Scrapes job posting HTML
│   │       ├── job_matcher.py       # LLM-based resume↔job matching
│   │       ├── resume_parser.py     # Extracts text from PDF resume
│   │       └── resume_tailor.py     # LLM tailoring + validation
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── Dockerfile
├── docker-compose.yml
├── .env                             # OPENAI_API_KEY (not committed)
└── .gitignore
```

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/)
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Jomble.git
cd Jomble
```

### 2. Set your API key

```bash
echo "OPENAI_API_KEY=sk-..." > .env
```

### 3. Build and run

```bash
docker-compose up --build
```

The app will be available at **http://localhost**.

---

## Usage

### Match
1. Paste a job posting URL into the input field.
2. Upload your resume as a **PDF**.
3. Click **Analyse** — results appear with a score, matched/missing skills, and a summary.

### Tailor (Improve)
1. After matching, click the **Improve** button.
2. Upload your resume as a **`.tex` file** or a **`.zip`** containing the `.tex` and any custom template files (`.cls`, `.sty`).
3. Click **Generate** — a ZIP file downloads containing:
   - `tailored_resume.tex` — your improved LaTeX source
   - `tailored_resume.pdf` — compiled PDF (Docker only)
   - `validation_report.json` — hallucination safety report

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI secret key |

---

## Local Development (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
uvicorn app.main:app --reload --port 8000
```

> **Note:** PDF compilation requires `pdflatex` (TeX Live). Without it, the `.tex` file is still tailored and included in the ZIP — only the `.pdf` is skipped.

---

## License

MIT
