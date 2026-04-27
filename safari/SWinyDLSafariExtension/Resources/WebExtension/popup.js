const state = {
  course: null,
  sourcePageUrl: null,
  courseUrl: null,
  deleteDownloadedMedia: true
};

const statusNode = document.getElementById("status");
const controlsNode = document.getElementById("controls");
const courseNode = document.getElementById("course");
const lessonListNode = document.getElementById("lesson-list");
const jobListNode = document.getElementById("job-list");
const deleteDownloadsNode = document.getElementById("delete-downloads");

document.getElementById("refresh").addEventListener("click", loadCourse);
document.getElementById("select-all").addEventListener("change", toggleAll);
document.getElementById("transcribe").addEventListener("click", () => launchJob("transcribe"));
document.getElementById("download-transcribe").addEventListener("click", () => launchJob("download_and_transcribe"));
document.getElementById("refresh-jobs").addEventListener("click", () => pollJobStatuses());
deleteDownloadsNode.addEventListener("change", persistSettings);

loadSettings().then(loadCourse);
setInterval(pollJobStatuses, 3000);

async function loadCourse() {
  setStatus("Loading course inventory…");
  const response = await browser.runtime.sendMessage({ type: "load-course" });
  if (!response?.ok) {
    setStatus(response?.error || "Unable to load a supported course from the current page.");
    controlsNode.classList.add("hidden");
    courseNode.classList.add("hidden");
    lessonListNode.innerHTML = "";
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
  document.getElementById("course-title").textContent = course.course_title;
  document.getElementById("course-meta").textContent = `${course.platform} • ${course.lessons.length} lessons`;
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
  const response = await browser.runtime.sendMessage({
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
  });

  if (!response?.ok) {
    setStatus(response?.error || "Unable to queue the job in the native wrapper.");
    return;
  }
  setStatus(`Queued job ${response.jobId}. The native SWinyDL app will show progress.`);
  await pollJobStatuses();
}

async function pollJobStatuses() {
  const response = await browser.runtime.sendMessage({ type: "job-status" });
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

function toggleAll(event) {
  const checked = event.target.checked;
  for (const checkbox of document.querySelectorAll("input[data-lesson-id]")) {
    checkbox.checked = checked;
  }
}

function setStatus(value) {
  statusNode.textContent = value;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
