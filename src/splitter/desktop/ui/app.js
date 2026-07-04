const STEM_LABELS = {
  vocals: "Vocals",
  drums: "Drums",
  bass: "Bass",
  other: "Other",
  no_vocals: "Instrumental",
};

const sourceInput = document.getElementById("source-input");
const sourceActionButton = document.getElementById("source-action");
const splitButton = document.getElementById("split-track");
const openFolderButton = document.getElementById("open-folder");
const downloadAllButton = document.getElementById("download-all");
const originalPreview = document.getElementById("original-preview");
const previewEmpty = document.getElementById("preview-empty");
const statusDot = document.getElementById("status-dot");
const statusTitle = document.getElementById("status-title");
const statusMessage = document.getElementById("status-message");
const elapsedLabel = document.getElementById("elapsed");
const errorMessage = document.getElementById("error-message");
const stemSection = document.getElementById("stem-section");
const stemGrid = document.getElementById("stem-grid");
const customStemsPanel = document.getElementById("custom-stems");
const modeInputs = document.querySelectorAll('input[name="split-mode"]');
const modeSegmentItems = document.querySelectorAll(".segmented--mode .segmented__item");
const customStemInputs = document.querySelectorAll('input[name="custom-stem"]');
const sourceTabLocal = document.getElementById("source-tab-local");
const sourceTabYoutube = document.getElementById("source-tab-youtube");

let pollTimer = null;
let elapsedTimer = null;
let elapsedSeconds = 0;
let currentInputPath = null;
let currentDisplayName = null;
let currentLocalPath = "";
let currentYoutubeUrl = "";
let activeSourceTab = "local";

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

function isBusy() {
  return ["downloading", "queued", "running"].includes(statusDot.dataset.status || "");
}

function updateModeSegmentUi() {
  modeSegmentItems.forEach((item) => {
    const radio = item.querySelector('input[type="radio"]');
    item.classList.toggle("is-active", Boolean(radio?.checked));
  });
}

function updateModeUi() {
  const mode = getSelectedMode();
  updateModeSegmentUi();
  customStemsPanel.hidden = mode !== "custom";
  updateActionState();
}

function updateActionState() {
  const mode = getSelectedMode();
  const customInvalid = mode === "custom" && getSelectedCustomStems().length === 0;
  const busy = isBusy();
  const ready = statusDot.dataset.status === "ready" && currentInputPath;

  sourceActionButton.disabled = busy;
  sourceInput.disabled = busy;
  sourceTabLocal.disabled = busy;
  sourceTabYoutube.disabled = busy;
  splitButton.disabled = busy || customInvalid || !ready;
  openFolderButton.disabled = statusDot.dataset.status !== "done";
}

function updateSourceInput() {
  const isLocal = activeSourceTab === "local";
  sourceInput.readOnly = isLocal;
  sourceInput.type = isLocal ? "text" : "url";
  sourceInput.placeholder = isLocal
    ? "No file selected"
    : "https://www.youtube.com/watch?v=...";
  sourceInput.value = isLocal ? currentLocalPath : currentYoutubeUrl;
  sourceActionButton.textContent = isLocal ? "Select audio file" : "Load from YouTube";
}

function setSourceTab(tab) {
  if (isBusy()) {
    return;
  }
  if (activeSourceTab === "youtube") {
    currentYoutubeUrl = sourceInput.value.trim();
  }
  activeSourceTab = tab;
  const isLocal = tab === "local";
  sourceTabLocal.classList.toggle("is-active", isLocal);
  sourceTabYoutube.classList.toggle("is-active", !isLocal);
  sourceTabLocal.setAttribute("aria-selected", String(isLocal));
  sourceTabYoutube.setAttribute("aria-selected", String(!isLocal));
  updateSourceInput();
}

function setStatus(status, message, error) {
  statusDot.dataset.status = status;
  statusDot.className = "status-dot";
  if (status === "downloading") {
    statusDot.classList.add("active");
    statusTitle.textContent = "Downloading from YouTube";
    elapsedLabel.hidden = true;
  } else if (status === "ready") {
    statusTitle.textContent = "Ready to split";
    elapsedLabel.hidden = true;
  } else if (status === "queued" || status === "running") {
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
    statusTitle.textContent = "Something went wrong";
    elapsedLabel.hidden = true;
  } else {
    statusTitle.textContent = "Waiting for a source";
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
  updateActionState();
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

function resetStemSection() {
  stemSection.hidden = true;
  stemGrid.innerHTML = "";
  openFolderButton.disabled = true;
}

function showLoadedSource(path, displayName, uri) {
  currentInputPath = path;
  currentDisplayName = displayName;
  currentLocalPath = displayName;
  if (activeSourceTab === "local") {
    sourceInput.value = currentLocalPath;
  }
  originalPreview.hidden = false;
  originalPreview.src = uri;
  previewEmpty.hidden = true;
  resetStemSection();
}

function clearPreview() {
  originalPreview.hidden = true;
  originalPreview.removeAttribute("src");
  previewEmpty.hidden = false;
}

async function pollStatus() {
  const status = await api().get_status();
  setStatus(status.status, status.message, status.error);

  if (status.status === "ready" && status.inputPath) {
    const uri = await api().get_input_uri();
    if (uri) {
      showLoadedSource(status.inputPath, status.displayName || status.inputPath, uri);
    }
    stopElapsedTimer();
    window.clearInterval(pollTimer);
    pollTimer = null;
    updateActionState();
    return;
  }

  if (status.status === "done") {
    stopElapsedTimer();
    await renderStems(status.stems);
    window.clearInterval(pollTimer);
    pollTimer = null;
    updateActionState();
  } else if (status.status === "error") {
    stopElapsedTimer();
    window.clearInterval(pollTimer);
    pollTimer = null;
    updateActionState();
  }
}

function beginPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
  }
  pollTimer = window.setInterval(pollStatus, 1500);
  pollStatus();
}

async function renderStems(stems) {
  stemGrid.innerHTML = "";
  stemSection.hidden = false;

  for (const stem of stems) {
    const uri = await api().get_stem_uri(stem);
    const card = document.createElement("article");
    card.className = "stem-card";
    card.dataset.stem = stem;

    const body = document.createElement("div");

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
    downloadButton.className = "btn btn--secondary";
    downloadButton.textContent = `Save ${STEM_LABELS[stem] || stem}`;
    downloadButton.addEventListener("click", async () => {
      const destination = await api().pick_save_file(`${stem}.wav`, "stem");
      if (!destination) {
        return;
      }
      const result = await api().save_stem_copy(stem, destination);
      if (!result.ok) {
        setStatus("error", "Could not save stem.", result.error);
      }
    });

    body.appendChild(title);
    body.appendChild(audio);
    body.appendChild(downloadButton);
    card.appendChild(body);
    stemGrid.appendChild(card);
  }
}

async function handlePickFile() {
  const result = await api().pick_input_file();
  if (!result.ok) {
    if (result.error) {
      setStatus("error", "Could not load file.", result.error);
    }
    return;
  }

  showLoadedSource(result.path, result.displayName, result.uri);
  setStatus("ready", "Preview the track, then click Split when ready.", null);
}

async function handleLoadYoutube() {
  const url = sourceInput.value.trim();
  if (!url) {
    setStatus("error", "Enter a YouTube URL.", "YouTube URL cannot be empty.");
    return;
  }

  currentYoutubeUrl = url;
  resetStemSection();
  currentInputPath = null;
  currentDisplayName = null;
  clearPreview();
  setStatus("downloading", "Downloading audio from YouTube…", null);

  const result = await api().download_youtube(url);
  if (!result.ok) {
    setStatus("error", "Could not start download.", result.error);
    return;
  }

  beginPolling();
}

async function handleSourceAction() {
  if (activeSourceTab === "local") {
    await handlePickFile();
  } else {
    await handleLoadYoutube();
  }
}

async function handleSplit() {
  if (!currentInputPath) {
    return;
  }

  const mode = getSelectedMode();
  const selectedStems = mode === "custom" ? getSelectedCustomStems() : null;

  splitButton.disabled = true;
  openFolderButton.disabled = true;
  resetStemSection();
  setStatus("queued", "Starting separation…", null);
  startElapsedTimer();

  const result = await api().start_separation(currentInputPath, mode, selectedStems);
  if (!result.ok) {
    stopElapsedTimer();
    setStatus("error", "Could not start separation.", result.error);
    updateActionState();
    return;
  }

  beginPolling();
}

async function handleDownloadAll() {
  const status = await api().get_status();
  if (status.status !== "done") {
    return;
  }
  const baseName = currentDisplayName
    ? currentDisplayName.replace(/[<>:"/\\|?*]/g, "").trim() || "stems"
    : currentInputPath
      ? currentInputPath.split(/[\\/]/).pop().replace(/\.[^.]+$/, "")
      : "stems";
  const destination = await api().pick_save_file(`${baseName}-stems.zip`, "zip");
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
  input.addEventListener("change", updateActionState);
});

sourceTabLocal.addEventListener("click", () => setSourceTab("local"));
sourceTabYoutube.addEventListener("click", () => setSourceTab("youtube"));

sourceActionButton.addEventListener("click", handleSourceAction);
splitButton.addEventListener("click", handleSplit);
openFolderButton.addEventListener("click", async () => {
  const result = await api().open_output_folder();
  if (!result.ok) {
    setStatus("error", "Could not open output folder.", result.error);
  }
});
downloadAllButton.addEventListener("click", handleDownloadAll);

sourceInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !sourceActionButton.disabled && activeSourceTab === "youtube") {
    handleLoadYoutube();
  }
});

window.addEventListener("pywebviewready", () => {
  updateSourceInput();
  updateModeUi();
  setStatus("idle", "Load a file or YouTube URL, preview, then split.", null);
});
