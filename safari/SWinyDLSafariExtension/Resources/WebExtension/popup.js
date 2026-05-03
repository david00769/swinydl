const state = {
  course: null,
  sourcePageUrl: null,
  courseUrl: null,
  deleteDownloadedMedia: true,
  discoveryTimer: null,
  discoveryCount: 0
};

const statusNode = document.getElementById("status");
const controlsNode = document.getElementById("controls");
const courseNode = document.getElementById("course");
const selectionControlsNode = document.getElementById("selection-controls");
const lessonListNode = document.getElementById("lesson-list");
const jobListNode = document.getElementById("job-list");
const deleteDownloadsNode = document.getElementById("delete-downloads");
const firstRunNode = document.getElementById("first-run");
const handoffNode = document.getElementById("handoff");
const handoffTitleNode = document.getElementById("handoff-title");
const handoffDetailNode = document.getElementById("handoff-detail");
const selectionCountNode = document.getElementById("selection-count");

document.getElementById("refresh").addEventListener("click", loadCourse);
document.getElementById("open-app").addEventListener("click", openNativeApp);
document.getElementById("handoff-open-app").addEventListener("click", openNativeApp);
document.getElementById("check-all").addEventListener("click", () => toggleAll(true));
document.getElementById("uncheck-all").addEventListener("click", () => toggleAll(false));
document.getElementById("export-debug").addEventListener("click", exportDebugLog);
document.getElementById("transcribe").addEventListener("click", () => launchJob("transcribe"));
document.getElementById("download-transcribe").addEventListener("click", () => launchJob("download_and_transcribe"));
document.getElementById("refresh-jobs").addEventListener("click", () => pollJobStatuses());
deleteDownloadsNode.addEventListener("change", persistSettings);

loadSettings().then(loadCourse);
setInterval(pollJobStatuses, 3000);

async function loadCourse() {
  startDiscoveryStatus();
  let response;
  try {
    response = await sendRuntimeMessage({ type: "load-course" }, "Unable to load course");
  } finally {
    stopDiscoveryStatus();
  }
  if (!response?.ok) {
    setStatus(response?.error || "Unable to load a supported course from the current page.");
    controlsNode.classList.add("hidden");
    courseNode.classList.add("hidden");
    selectionControlsNode.classList.add("hidden");
    firstRunNode.classList.remove("hidden");
    hideHandoff();
    lessonListNode.innerHTML = "";
    updateSelectionCount();
    return;
  }

  state.course = response.course;
  state.sourcePageUrl = response.sourcePageUrl;
  state.courseUrl = response.courseUrl;
  renderCourse(response.course);
  setStatus(`Loaded ${response.course.lessons.length} lessons from ${response.course.course_title}.`);
  await pollJobStatuses();
}

function renderCourse(course) {
  controlsNode.classList.remove("hidden");
  courseNode.classList.remove("hidden");
  selectionControlsNode.classList.remove("hidden");
  firstRunNode.classList.add("hidden");
  hideHandoff();
  document.getElementById("course-title").textContent = course.course_title;
  document.getElementById("course-meta").textContent = [
    course.course_context_label || course.platform,
    course.course_description,
    `${course.lessons.length} lessons`
  ].filter(Boolean).join(" • ");
  lessonListNode.innerHTML = "";
  for (const lesson of course.lessons) {
    const wrapper = document.createElement("label");
    wrapper.className = "lesson row";
    wrapper.innerHTML = `
      <span>
        <div class="title">${escapeHtml(lesson.title)}</div>
        <div class="meta">${lesson.date || "undated"} • ${lesson.assets.filter((asset) => asset.kind === "caption").length} captions • ${lesson.assets.filter((asset) => asset.kind === "media").length} media</div>
      </span>
      <input type="checkbox" data-lesson-id="${escapeHtml(lesson.lesson_id)}" checked />
    `;
    lessonListNode.appendChild(wrapper);
  }
  for (const checkbox of document.querySelectorAll("input[data-lesson-id]")) {
    checkbox.addEventListener("change", updateSelectionCount);
  }
  updateSelectionCount();
}

async function launchJob(requestedAction) {
  if (!state.course) {
    setStatus("Load a supported course first.");
    return;
  }
  const selectedLessonIds = Array.from(document.querySelectorAll("input[data-lesson-id]:checked"))
    .map((input) => input.getAttribute("data-lesson-id"));
  if (!selectedLessonIds.length) {
    setStatus("Choose at least one lesson.");
    return;
  }

  setStatus("Launching job in the native SWinyDL app…");
  const response = await sendRuntimeMessage({
    type: "launch-job",
    payload: {
      sourcePageUrl: state.sourcePageUrl,
      courseUrl: state.courseUrl,
      selectedLessonIds,
      requestedAction,
      deleteDownloadedMediaAfterTranscription: state.deleteDownloadedMedia,
      keepAudio: false,
      keepVideo: requestedAction === "download_and_transcribe",
      outputRoot: null,
      course: {
        ...state.course,
        lessons: state.course.lessons.filter((lesson) => selectedLessonIds.includes(lesson.lesson_id))
      }
    }
  }, "Unable to queue the job");

  if (!response?.ok) {
    setStatus(response?.error || "Unable to queue the job in the native wrapper.");
    return;
  }
  const appLaunchFailed = response?.app_launch?.succeeded === false || response.appOpened === false;
  if (appLaunchFailed) {
    showHandoff("Queued, but SWinyDL did not open.", "Click Open App. Progress appears in SWinyDL.");
    setStatus(`Queued ${selectedLessonIds.length} lessons, but SWinyDL did not open. Click Open App.`);
  } else {
    showHandoff("Queued for transcription.", "Progress appears in SWinyDL.");
    setStatus(`Queued ${selectedLessonIds.length} lessons. Progress appears in SWinyDL.`);
  }
  await pollJobStatuses();
}

async function pollJobStatuses() {
  const response = await sendRuntimeMessage({ type: "job-status" }, "Unable to refresh jobs");
  if (!response?.ok) {
    return;
  }
  const jobs = response.jobs || [];
  jobListNode.innerHTML = "";
  for (const job of jobs) {
    const wrapper = document.createElement("article");
    wrapper.className = "job";
    const detail = job.active_lesson_title
      ? ` • ${job.active_lesson_title}`
      : (job.detail ? ` • ${job.detail}` : "");
    wrapper.innerHTML = `
      <div class="title">${escapeHtml(job.course_title || job.job_id)}</div>
      <div class="meta">${escapeHtml(job.overall_status)} • ${job.completed_lessons}/${job.total_lessons} lessons${escapeHtml(detail)}</div>
    `;
    jobListNode.appendChild(wrapper);
  }
}

async function openNativeApp() {
  setStatus("Opening the native SWinyDL app…");
  const response = await sendRuntimeMessage({ type: "open-app" }, "Unable to open the native SWinyDL app");
  if (!response?.ok) {
    setStatus(response?.error || "Unable to open the native SWinyDL app. Open SWinyDL manually, or copy the Terminal repair command from the app if setup needs repair.");
    return;
  }
  setStatus("Opened the native SWinyDL app.");
}

async function exportDebugLog() {
  setStatus("Preparing sanitized debug log…");
  const filename = `swinydl-debug-${timestampForFilename()}.json`;
  const response = await sendRuntimeMessage({ type: "export-debug-log", filename }, "Unable to export a debug log");
  if (!response?.ok) {
    setStatus(response?.error || "Unable to export a debug log from this page.");
    return;
  }
  const location = response.directory || response.savedPath || "the SWinyDL Logs folder";
  setStatus(`Saved ${response.filename || filename} in ${location}.`);
}

async function sendRuntimeMessage(message, fallbackMessage) {
  try {
    return await browser.runtime.sendMessage(message);
  } catch (error) {
    return {
      ok: false,
      error: `${fallbackMessage}: ${String(error?.message || error)}`
    };
  }
}

async function loadSettings() {
  const stored = await browser.storage.local.get({ deleteDownloadedMediaAfterTranscription: true });
  state.deleteDownloadedMedia = Boolean(stored.deleteDownloadedMediaAfterTranscription);
  deleteDownloadsNode.checked = state.deleteDownloadedMedia;
}

async function persistSettings() {
  state.deleteDownloadedMedia = Boolean(deleteDownloadsNode.checked);
  await browser.storage.local.set({
    deleteDownloadedMediaAfterTranscription: state.deleteDownloadedMedia
  });
}

function toggleAll(checked) {
  for (const checkbox of document.querySelectorAll("input[data-lesson-id]")) {
    checkbox.checked = checked;
  }
  updateSelectionCount();
}

function updateSelectionCount() {
  const checkboxes = Array.from(document.querySelectorAll("input[data-lesson-id]"));
  const selected = checkboxes.filter((checkbox) => checkbox.checked).length;
  const total = checkboxes.length;
  selectionCountNode.textContent = total ? `${selected}/${total} selected` : "0 selected";
}

function setStatus(value) {
  statusNode.textContent = value;
}

function showHandoff(title, detail) {
  handoffTitleNode.textContent = title;
  handoffDetailNode.textContent = detail;
  handoffNode.classList.remove("hidden");
}

function hideHandoff() {
  handoffNode.classList.add("hidden");
}

function startDiscoveryStatus() {
  stopDiscoveryStatus();
  state.discoveryCount = 1;
  setStatus(`Discovering course content ${state.discoveryCount}...`);
  state.discoveryTimer = setInterval(() => {
    state.discoveryCount += 1;
    setStatus(`Discovering course content ${state.discoveryCount}...`);
  }, 900);
}

function stopDiscoveryStatus() {
  if (state.discoveryTimer) {
    clearInterval(state.discoveryTimer);
    state.discoveryTimer = null;
  }
}

function timestampForFilename() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    "-",
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds())
  ].join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
