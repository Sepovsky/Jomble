const API_URL = "/api/match";

const form       = document.getElementById("match-form");
const submitBtn  = document.getElementById("submit-btn");
const btnLabel   = submitBtn.querySelector(".btn-label");
const btnSpinner = submitBtn.querySelector(".btn-spinner");
const errorMsg   = document.getElementById("error-msg");
const inputCard  = document.getElementById("input-card");
const resultsCard = document.getElementById("results-card");
const resetBtn   = document.getElementById("reset-btn");
const dropZone   = document.getElementById("drop-zone");
const fileInput  = document.getElementById("resume");
const fileNameEl = document.getElementById("file-name");

// ── Drop zone ──────────────────────────────────────────────────────────────

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

function setFile(file) {
  if (!file.name.endsWith(".pdf")) {
    showError("Please upload a PDF file.");
    return;
  }
  const dt = new DataTransfer();
  dt.items.add(file);
  fileInput.files = dt.files;
  fileNameEl.textContent = file.name;
  dropZone.classList.add("has-file");
}

// ── Form submit ────────────────────────────────────────────────────────────

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();

  const jobUrl = document.getElementById("job-url").value.trim();
  const file   = fileInput.files[0];

  if (!jobUrl)  { showError("Please enter a job posting URL.");  return; }
  if (!file)    { showError("Please upload your resume PDF.");    return; }

  setLoading(true);

  const formData = new FormData();
  formData.append("job_url", jobUrl);
  formData.append("resume", file);

  try {
    const res = await fetch(API_URL, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    showError(err.message || "Something went wrong. Please try again.");
  } finally {
    setLoading(false);
  }
});

// ── Results ────────────────────────────────────────────────────────────────

function renderResults(data) {
  inputCard.hidden  = true;
  resultsCard.hidden = false;

  // Score ring animation
  const score     = Math.round(data.score);
  const circumference = 314;
  const offset    = circumference - (score / 100) * circumference;
  const ring      = document.getElementById("ring-fill");

  ring.style.strokeDashoffset = circumference;
  ring.style.stroke = scoreColor(score);
  requestAnimationFrame(() => {
    setTimeout(() => { ring.style.strokeDashoffset = offset; }, 50);
  });

  // Animate number count-up
  const numEl = document.getElementById("score-number");
  let current = 0;
  const step  = Math.ceil(score / 40);
  const timer = setInterval(() => {
    current = Math.min(current + step, score);
    numEl.textContent = current;
    if (current >= score) clearInterval(timer);
  }, 30);

  // Score title
  const title = document.getElementById("score-title");
  if      (score >= 80) title.textContent = "Strong Match 🎯";
  else if (score >= 55) title.textContent = "Moderate Match 👍";
  else if (score >= 30) title.textContent = "Partial Match 🔍";
  else                  title.textContent = "Low Match ⚠️";

  document.getElementById("summary-text").textContent = data.summary;

  renderList("matched-list", "matched-count", data.matched);
  renderList("missing-list",  "missing-count",  data.missing);
  renderList("extra-list",    "extra-count",    data.resume_extra);
}

function renderList(listId, countId, items) {
  const ul    = document.getElementById(listId);
  const badge = document.getElementById(countId);
  ul.innerHTML = "";
  badge.textContent = items.length;
  if (items.length === 0) {
    const li = document.createElement("li");
    li.textContent = "—";
    li.style.opacity = ".4";
    ul.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    ul.appendChild(li);
  });
}

function scoreColor(score) {
  if (score >= 70) return "#10B981";
  if (score >= 45) return "#F59E0B";
  return "#EF4444";
}

// ── Reset ──────────────────────────────────────────────────────────────────

resetBtn.addEventListener("click", () => {
  resultsCard.hidden = true;
  inputCard.hidden   = false;
  form.reset();
  fileNameEl.textContent = "";
  dropZone.classList.remove("has-file");
  document.getElementById("ring-fill").style.strokeDashoffset = 314;
});

// ── Helpers ────────────────────────────────────────────────────────────────

function setLoading(on) {
  submitBtn.disabled    = on;
  btnLabel.hidden       = on;
  btnSpinner.hidden     = !on;
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.hidden      = false;
}

function hideError() {
  errorMsg.hidden = true;
}
