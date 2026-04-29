<div align="center">

<img src="frontend/img/jomble-logo.png" alt="Jomble" width="260" />

<p align="center"><strong>Resume intelligence — match your CV to any role and tailor it with AI.</strong></p>

</div>

---

## Overview

**Jomble** is an AI-powered job-matching and resume-tailoring app. Paste a job posting URL, upload your resume PDF, and get an instant match score with actionable feedback. Optionally upload your LaTeX resume to have it tailored for the role.

---

## Features

- **Job matching** — Scrapes a job posting URL and semantically matches it against your resume using an OpenAI model. Returns a score (0–100), matched skills, missing skills, and a plain-English summary.
- **Preference checks** — Optional filters (location, remote policy, languages, salary, etc.) are validated against the posting before the resume match.
- **Resume tailoring** — Upload your LaTeX resume (`.tex` or `.zip`). The model suggests targeted text improvements as string-level patches — it does not rewrite structure or invent experience.
- **Post-tailoring validation** — A second pass checks the tailored resume for inconsistencies before delivery.
- **ZIP download** — Get tailored sources plus optional PDF and validation metadata in one download.
- **Dockerised stack** — Frontend (Nginx) + backend (FastAPI) via Docker Compose.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | HTML, CSS, vanilla JS (Nginx) |
| Backend | Python, FastAPI |
| LLM | OpenAI API |
| Scraping | Playwright (Chromium), BeautifulSoup |
| PDF parsing | PyMuPDF (fitz) |
| LaTeX | pdflatex (TeX Live), where available |
| Containers | Docker, Docker Compose |

---

## Project structure

```
Jomble/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry
│   │   ├── schemas.py               # Pydantic models
│   │   ├── routers/
│   │   │   ├── match.py             # POST /api/match
│   │   │   └── tailor.py            # POST /api/tailor
│   │   └── services/
│   │       ├── job_fetcher.py       # Job posting HTML
│   │       ├── job_matcher.py       # Resume ↔ job matching
│   │       ├── resume_parser.py     # PDF text extraction
│   │       ├── resume_tailor.py     # Tailoring + validation
│   │       └── metadata_gate.py     # Preference vs posting checks
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── img/                         # Logo & favicon assets
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── .env                             # OPENAI_API_KEY (not committed)
└── .gitignore
```

---

## Getting started

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
docker compose up --build
```

The UI is served at **http://localhost** (port 80). The backend API is used by the frontend container on the internal Docker network.

---

## Usage

### Match

1. Paste a **job posting URL**.
2. Upload your resume as a **PDF**.
3. Optionally expand **Your preferences** to filter by location, remote policy, languages, salary, and more.
4. Click **Analyze Match** — you’ll see a score, preference check summary (if applicable), matched/missing skills, and a short assessment.

### Tailor (improve)

1. After a match, open **Improve my resume for this job**.
2. Upload a **`.tex`** file or a **`.zip`** that includes your `.tex` and any needed `.cls` / `.sty` files.
3. Click **Generate** — download the ZIP with tailored sources and reports (contents depend on backend configuration).

---

## Environment variables

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API secret key |

---

## Local development (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install --with-deps chromium
uvicorn app.main:app --reload --port 8000
```

Serve the frontend separately (e.g. static file server pointed at `frontend/`) and configure the JS client to call `http://localhost:8000` if needed.

> **Note:** PDF compilation needs `pdflatex` (TeX Live). Without it, tailored `.tex` may still be produced while PDF generation is skipped.

---

## License

MIT
