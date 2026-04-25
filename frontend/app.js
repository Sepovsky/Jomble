const API_URL        = "/api/match";
const API_TAILOR_URL = "/api/tailor";

let _jobText   = "";
let _missing   = [];

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
  _jobText = data.job_text || "";
  _missing = data.missing  || [];

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

// ── Improve / Tailor ──────────────────────────────────────────────────────

const improveBtn   = document.getElementById("improve-btn");
const improveModal = document.getElementById("improve-modal");
const modalCancel  = document.getElementById("modal-cancel");
const modalSubmit  = document.getElementById("modal-submit");
const modalError   = document.getElementById("modal-error");
const texDropZone  = document.getElementById("tex-drop-zone");
const texFileInput = document.getElementById("tex-file");
const texFileName  = document.getElementById("tex-file-name");
const texBrowse    = document.getElementById("tex-browse");

improveBtn.addEventListener("click", () => { improveModal.hidden = false; });
modalCancel.addEventListener("click", closeModal);
improveModal.addEventListener("click", (e) => { if (e.target === improveModal) closeModal(); });

texBrowse.addEventListener("click", () => texFileInput.click());
texDropZone.addEventListener("click", () => texFileInput.click());

texDropZone.addEventListener("dragover",  (e) => { e.preventDefault(); texDropZone.classList.add("drag-over"); });
texDropZone.addEventListener("dragleave", ()  => texDropZone.classList.remove("drag-over"));
texDropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  texDropZone.classList.remove("drag-over");
  if (e.dataTransfer.files[0]) setTexFile(e.dataTransfer.files[0]);
});
texFileInput.addEventListener("change", () => {
  if (texFileInput.files[0]) setTexFile(texFileInput.files[0]);
});

function setTexFile(file) {
  const dt = new DataTransfer();
  dt.items.add(file);
  texFileInput.files = dt.files;
  texFileName.textContent = file.name;
  texDropZone.classList.add("has-file");
}

modalSubmit.addEventListener("click", async () => {
  const file = texFileInput.files[0];
  if (!file) { showModalError("Please upload a .tex or .zip file."); return; }

  modalError.hidden = true;
  const label   = modalSubmit.querySelector(".btn-label");
  const spinner = modalSubmit.querySelector(".btn-spinner");
  modalSubmit.disabled = true;
  label.hidden   = true;
  spinner.hidden = false;

  try {
    const fd = new FormData();
    fd.append("tex_file", file);
    fd.append("job_text", _jobText);
    fd.append("missing",  JSON.stringify(_missing));

    const res = await fetch(API_TAILOR_URL, { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }

    const blob   = await res.blob();
    const url    = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href     = url;
    anchor.download = "tailored_resume.zip";
    anchor.click();
    URL.revokeObjectURL(url);
    closeModal();
  } catch (err) {
    showModalError(err.message || "Something went wrong. Please try again.");
  } finally {
    modalSubmit.disabled = false;
    label.hidden   = false;
    spinner.hidden = true;
  }
});

function closeModal() {
  improveModal.hidden = true;
  texFileName.textContent = "";
  texDropZone.classList.remove("has-file");
  texFileInput.value = "";
  modalError.hidden  = true;
}

function showModalError(msg) {
  modalError.textContent = msg;
  modalError.hidden = false;
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
