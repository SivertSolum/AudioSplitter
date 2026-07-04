const STEM_LABELS = {
  vocals: "Vocals",
  drums: "Drums",
  bass: "Bass",
  other: "Other",
  no_vocals: "Instrumental",
};

const pickFileButton = document.getElementById("pick-file");
const openFolderButton = document.getElementById("open-folder");
const downloadAllButton = document.getElementById("download-all");
const selectedFileLabel = document.getElementById("selected-file");
const originalPreview = document.getElementById("original-preview");
const statusDot = document.getElementById("status-dot");
const statusTitle = document.getElementById("status-title");
const statusMessage = document.getElementById("status-message");
const elapsedLabel = document.getElementById("elapsed");
const errorMessage = document.getElementById("error-message");
const stemSection = document.getElementById("stem-section");
const stemGrid = document.getElementById("stem-grid");
const customStemsPanel = document.getElementById("custom-stems");
const modeInputs = document.querySelectorAll('input[name="split-mode"]');
const customStemInputs = document.querySelectorAll('input[name="custom-stem"]');

let pollTimer = null;
let elapsedTimer = null;
let elapsedSeconds = 0;
let currentInputPath = null;

function api() {
  return window.pywebview.api;
}

function getSelectedMode() {
  const selected = document.querySelector('input[name="split-mode"]:checked');
  return selected ? selected.value : "full";
}

function getSelectedCustomStems() {
  return Array.from(customStemInputs)
    .filter((input) => input.checked)
    .map((input) => input.value);
}

function updateModeUi() {
  const mode = getSelectedMode();
  customStemsPanel.hidden = mode !== "custom";
  updatePickFileState();
}

function updatePickFileState() {
  const mode = getSelectedMode();
  const customInvalid = mode === "custom" && getSelectedCustomStems().length === 0;
  const isBusy = statusDot.classList.contains("active");
  pickFileButton.disabled = customInvalid || isBusy;
}

function setStatus(status, message, error) {
  statusDot.className = "status-dot";
  if (status === "queued" || status === "running" || status === "uploading") {
    statusDot.classList.add("active");
    statusTitle.textContent =
      status === "queued" ? "Queued for separation" : "Separating stems with Demucs…";
    elapsedLabel.hidden = false;
  } else if (status === "done") {
    statusDot.classList.add("done");
    statusTitle.textContent = "Separation complete";
    elapsedLabel.hidden = true;
  } else if (status === "error") {
    statusDot.classList.add("error");
    statusTitle.textContent = "Separation failed";
    elapsedLabel.hidden = true;
  } else {
    statusTitle.textContent = "Waiting for a file";
    elapsedLabel.hidden = true;
  }

  statusMessage.textContent = message || "";
  if (error) {
    errorMessage.hidden = false;
    errorMessage.textContent = error;
  } else {
    errorMessage.hidden = true;
    errorMessage.textContent = "";
  }
  updatePickFileState();
}

function startElapsedTimer() {
  elapsedSeconds = 0;
  elapsedLabel.textContent = "Elapsed: 0:00";
  elapsedLabel.hidden = false;
  if (elapsedTimer) {
    window.clearInterval(elapsedTimer);
  }
  elapsedTimer = window.setInterval(() => {
    elapsedSeconds += 1;
    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = String(elapsedSeconds % 60).padStart(2, "0");
    elapsedLabel.textContent = `Elapsed: ${minutes}:${seconds}`;
  }, 1000);
}

function stopElapsedTimer() {
  if (elapsedTimer) {
    window.clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
}

async function pollStatus() {
  const status = await api().get_status();
  setStatus(status.status, status.message, status.error);

  if (status.status === "done") {
    stopElapsedTimer();
    pickFileButton.disabled = false;
    openFolderButton.disabled = false;
    await renderStems(status.stems);
    window.clearInterval(pollTimer);
    pollTimer = null;
    updatePickFileState();
  } else if (status.status === "error") {
    stopElapsedTimer();
    pickFileButton.disabled = false;
    window.clearInterval(pollTimer);
    pollTimer = null;
    updatePickFileState();
  }
}

async function renderStems(stems) {
  stemGrid.innerHTML = "";
  stemSection.hidden = false;

  for (const stem of stems) {
    const uri = await api().get_stem_uri(stem);
    const card = document.createElement("article");
    card.className = "stem-card";

    const title = document.createElement("h3");
    title.textContent = STEM_LABELS[stem] || stem;

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    if (uri) {
      audio.src = uri;
    }

    const downloadButton = document.createElement("button");
    downloadButton.type = "button";
    downloadButton.textContent = `Save ${STEM_LABELS[stem] || stem}`;
    downloadButton.addEventListener("click", async () => {
      const destination = await api().pick_save_file(`${stem}.wav`);
      if (!destination) {
        return;
      }
      const result = await api().save_stem_copy(stem, destination);
      if (!result.ok) {
        setStatus("error", "Could not save stem.", result.error);
      }
    });

    card.appendChild(title);
    card.appendChild(audio);
    card.appendChild(downloadButton);
    stemGrid.appendChild(card);
  }
}

async function handlePickFile() {
  const mode = getSelectedMode();
  const selectedStems = mode === "custom" ? getSelectedCustomStems() : null;

  const inputPath = await api().pick_input_file();
  if (!inputPath) {
    return;
  }

  currentInputPath = inputPath;
  selectedFileLabel.textContent = inputPath;
  originalPreview.hidden = false;
  originalPreview.src = `file:///${inputPath.replace(/\\/g, "/")}`;

  pickFileButton.disabled = true;
  openFolderButton.disabled = true;
  stemSection.hidden = true;
  stemGrid.innerHTML = "";
  setStatus("queued", "Starting separation…", null);
  startElapsedTimer();

  const result = await api().start_separation(inputPath, mode, selectedStems);
  if (!result.ok) {
    stopElapsedTimer();
    pickFileButton.disabled = false;
    setStatus("error", "Could not start separation.", result.error);
    updatePickFileState();
    return;
  }

  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
  pollTimer = window.setInterval(pollStatus, 1500);
  await pollStatus();
}

async function handleDownloadAll() {
  const status = await api().get_status();
  if (status.status !== "done") {
    return;
  }
  const baseName = currentInputPath
    ? currentInputPath.split(/[\\/]/).pop().replace(/\.[^.]+$/, "")
    : "stems";
  const destination = await api().pick_save_file(`${baseName}-stems.zip`);
  if (!destination) {
    return;
  }
  const result = await api().save_all_stems_zip(destination);
  if (!result.ok) {
    setStatus("error", "Could not create zip archive.", result.error);
  }
}

modeInputs.forEach((input) => {
  input.addEventListener("change", updateModeUi);
});

customStemInputs.forEach((input) => {
  input.addEventListener("change", updatePickFileState);
});

pickFileButton.addEventListener("click", handlePickFile);
openFolderButton.addEventListener("click", async () => {
  const result = await api().open_output_folder();
  if (!result.ok) {
    setStatus("error", "Could not open output folder.", result.error);
  }
});
downloadAllButton.addEventListener("click", handleDownloadAll);

window.addEventListener("pywebviewready", () => {
  updateModeUi();
  setStatus("idle", "Choose a split mode, then select a track.", null);
});
