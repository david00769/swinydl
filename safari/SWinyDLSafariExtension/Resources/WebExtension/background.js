const CAPTION_EXTENSIONS = new Set(["vtt", "srt"]);
const MEDIA_EXTENSIONS = new Set(["m3u8", "mp4", "m4a", "aac", "mp3", "mov", "webm"]);
const tabContextCache = new Map();

browser.runtime.onMessage.addListener((message, sender) => {
  switch (message?.type) {
    case "page-context-updated":
      rememberPageContext(sender, message.context);
      return false;
    case "load-course":
      return loadCourseForActiveTab();
    case "launch-job":
      return launchJob(message.payload);
    case "job-status":
      return sendNative("job_status", {});
    case "open-output":
      return sendNative("open_output", { path: message.path });
    default:
      return false;
  }
});

if (browser.tabs?.onRemoved) {
  browser.tabs.onRemoved.addListener((tabId) => {
    tabContextCache.delete(tabId);
  });
}

async function loadCourseForActiveTab() {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url) {
    return { ok: false, error: "No active Safari tab was found." };
  }

  let context = { pageUrl: tab.url, pageTitle: tab.title || "", iframeUrls: [], anchorUrls: [], formActionUrls: [], mediaLinks: [] };
  try {
    context = await browser.tabs.sendMessage(tab.id, { type: "collect-page-context" });
    rememberPageContext({ tab }, context);
  } catch (_error) {
  }

  context = mergePageContexts(context, ...(tabContextCache.get(tab.id) || []));
  const courseUrl = deriveCourseUrl(context);
  if (!courseUrl) {
    return { ok: false, error: "This page does not look like a supported Canvas or Echo360 course entrypoint." };
  }

  try {
    const course = await discoverCourse(courseUrl);
    return { ok: true, course, sourcePageUrl: context.pageUrl, courseUrl };
  } catch (error) {
    return { ok: false, error: `Found EchoVideo on this page, but could not load the course inventory: ${String(error?.message || error)}` };
  }
}

async function launchJob(payload) {
  const hosts = new Set([new URL(payload.courseUrl).hostname, new URL(payload.sourcePageUrl).hostname]);
  const cookies = await exportCookies(Array.from(hosts));
  const manifest = {
    source_page_url: payload.sourcePageUrl,
    course_url: payload.courseUrl,
    host: new URL(payload.courseUrl).origin,
    selected_lesson_ids: payload.selectedLessonIds,
    requested_action: payload.requestedAction,
    delete_downloaded_media: payload.deleteDownloadedMediaAfterTranscription !== false,
    cookies,
    course: payload.course,
    output_root: payload.outputRoot || null,
    keep_audio: Boolean(payload.keepAudio),
    keep_video: Boolean(payload.keepVideo),
    transcript_source: payload.transcriptSource || "auto",
    asr_backend: "auto",
    diarization_mode: "on"
  };

  return sendNative("launch_job", { manifest });
}

async function sendNative(operation, payload) {
  try {
    return await browser.runtime.sendNativeMessage("com.davidsiroky.swinydl.SafariApp", {
      operation,
      ...payload
    });
  } catch (error) {
    return { ok: false, error: String(error) };
  }
}

function deriveCourseUrl(context) {
  const candidates = [
    context.pageUrl,
    ...(context.iframeUrls || []),
    ...(context.anchorUrls || []),
    ...(context.formActionUrls || [])
  ].filter(Boolean);
  for (const value of candidates) {
    if (/echo360|\/ess\/portal\/section\/|\/lti\//i.test(value)) {
      return value;
    }
  }
  return null;
}

function rememberPageContext(sender, context) {
  const tabId = sender?.tab?.id;
  if (tabId == null || !context) {
    return;
  }
  const frameId = sender.frameId ?? 0;
  const contextsByFrame = new Map((tabContextCache.get(tabId) || []).map((item) => [item.frameId, item.context]));
  contextsByFrame.set(frameId, context);
  tabContextCache.set(
    tabId,
    Array.from(contextsByFrame.entries()).map(([cachedFrameId, cachedContext]) => ({
      frameId: cachedFrameId,
      context: cachedContext
    }))
  );
}

function mergePageContexts(...contexts) {
  const merged = { pageUrl: "", pageTitle: "", iframeUrls: [], anchorUrls: [], formActionUrls: [], mediaLinks: [] };
  for (const entry of contexts.flat()) {
    const context = entry?.context || entry;
    if (!context) {
      continue;
    }
    merged.pageUrl = merged.pageUrl || context.pageUrl || "";
    merged.pageTitle = merged.pageTitle || context.pageTitle || "";
    for (const key of ["iframeUrls", "anchorUrls", "formActionUrls", "mediaLinks"]) {
      merged[key].push(...(context[key] || []));
    }
  }
  for (const key of ["iframeUrls", "anchorUrls", "formActionUrls", "mediaLinks"]) {
    merged[key] = Array.from(new Set(merged[key].filter(Boolean)));
  }
  return merged;
}

async function discoverCourse(courseUrl) {
  const hostname = extractCourseHostname(courseUrl) || "https://view.streaming.sydney.edu.au:8443";
  const platform = isEcho360CloudHost(hostname) ? "cloud" : "classic";
  const courseUuid = extractCourseUuid(courseUrl, platform === "cloud");
  const fullCourseUrl = extractCourseHostname(courseUrl)
    ? courseUrl
    : `${hostname}/ess/portal/section/${courseUuid}`;

  let course;
  if (platform === "cloud") {
    const payload = await fetchJson(`${hostname}/section/${courseUuid}/syllabus`);
    course = parseCloudLessons(hostname, payload, fullCourseUrl, courseUuid);
  } else {
    const payload = await fetchJson(`${hostname}/ess/client/api/sections/${courseUuid}/section-data.json?pageSize=100`);
    course = parseClassicLessons(payload, fullCourseUrl, hostname, courseUuid);
  }

  for (const lesson of course.lessons) {
    lesson.assets = dedupeAssets([...(lesson.assets || []), ...(await resolveLessonAssets(lesson.lesson_url))]);
  }
  return course;
}

function extractCourseHostname(courseUrl) {
  const match = String(courseUrl).match(/https?:\/\/[^/]+/i);
  return match ? match[0] : null;
}

function isEcho360CloudHost(hostname) {
  return /echo360\.org|echo360\.net/i.test(hostname || "");
}

function extractCourseUuid(courseUrl, usingCloud) {
  const input = String(courseUrl);
  const match = usingCloud
    ? input.match(/([0-9a-zA-Z]+-){3,}[0-9a-zA-Z]+/)
    : input.match(/[^/]+(?=\/?$)/);
  if (!match) {
    throw new Error("Unable to parse a course identifier from the supplied URL.");
  }
  return match[0];
}

async function fetchJson(url) {
  const response = await fetch(url, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Echo360 request failed for ${url} with status ${response.status}.`);
  }
  return await response.json();
}

function parseClassicLessons(payload, sourceUrl, hostname, courseUuid) {
  const section = payload.section || {};
  const course = section.course || {};
  const presentations = (((section.presentations || {}).pageContents) || []);
  return {
    source_url: sourceUrl,
    hostname,
    platform: "classic",
    course_uuid: courseUuid,
    course_id: course.identifier || null,
    course_title: course.name || "Untitled Course",
    lessons: presentations.map((item, index) => ({
      lesson_id: extractLessonId(item.richMedia) || `classic-${index + 1}`,
      title: item.title || `Lesson ${index + 1}`,
      date: normalizeDate(item.startTime),
      lesson_url: item.richMedia || "",
      index: index + 1,
      assets: detectAssets(item)
    }))
  };
}

function parseCloudLessons(hostname, payload, sourceUrl, courseUuid) {
  const lessons = [];
  let courseTitle = "Untitled Course";
  for (const [groupIndex, item] of (payload.data || []).entries()) {
    if (Array.isArray(item.lessons)) {
      const groupName = item.groupInfo?.name || `Group ${groupIndex + 1}`;
      for (const [lessonIndex, lessonItem] of item.lessons.entries()) {
        const lesson = buildCloudLesson(hostname, lessonItem, (groupIndex + 1) * 100 + lessonIndex + 1, `${groupName} - `);
        lessons.push(lesson);
        courseTitle = courseTitle === "Untitled Course" ? extractCloudCourseTitle(lessonItem) : courseTitle;
      }
    } else {
      const lesson = buildCloudLesson(hostname, item, groupIndex + 1, "");
      lessons.push(lesson);
      courseTitle = courseTitle === "Untitled Course" ? extractCloudCourseTitle(item) : courseTitle;
    }
  }

  return {
    source_url: sourceUrl,
    hostname,
    platform: "cloud",
    course_uuid: courseUuid,
    course_id: null,
    course_title: courseTitle,
    lessons
  };
}

function buildCloudLesson(hostname, item, index, prefix) {
  const lessonNode = item.lesson?.lesson || {};
  const lessonId = String(lessonNode.id || `cloud-${index}`);
  return {
    lesson_id: lessonId,
    title: `${prefix}${lessonNode.name || `Lesson ${index}`}`,
    date: normalizeDate(item.lesson?.startTimeUTC || lessonNode.createdAt || item.groupInfo?.createdAt),
    lesson_url: `${hostname}/lesson/${lessonId}/classroom`,
    index,
    assets: detectAssets(item)
  };
}

function extractCloudCourseTitle(item) {
  return item.lesson?.video?.published?.courseName || "Untitled Course";
}

async function resolveLessonAssets(lessonUrl) {
  if (!lessonUrl) {
    return [];
  }
  try {
    const response = await fetch(lessonUrl, { credentials: "include" });
    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const assets = [];
    for (const video of Array.from(doc.querySelectorAll("video[src]"))) {
      assets.push({
        kind: "media",
        url: video.src,
        label: "page-video",
        ext: mediaExtension(video.src)
      });
    }
    for (const track of Array.from(doc.querySelectorAll("track[src]"))) {
      assets.push({
        kind: "caption",
        url: track.src,
        label: track.getAttribute("label") || track.getAttribute("kind") || "track",
        ext: mediaExtension(track.src)
      });
    }
    return assets;
  } catch (_error) {
    return [];
  }
}

function detectAssets(value, path = "") {
  const assets = [];
  if (Array.isArray(value)) {
    value.forEach((item, index) => {
      assets.push(...detectAssets(item, `${path}[${index}]`));
    });
    return dedupeAssets(assets);
  }
  if (value && typeof value === "object") {
    Object.entries(value).forEach(([key, item]) => {
      assets.push(...detectAssets(item, path ? `${path}.${key}` : key));
    });
    return dedupeAssets(assets);
  }
  if (typeof value !== "string" || !value.startsWith("http")) {
    return assets;
  }
  const ext = mediaExtension(value);
  const lowerPath = path.toLowerCase();
  if (CAPTION_EXTENSIONS.has(ext) || /caption|subtitle|transcript/.test(lowerPath)) {
    assets.push({ kind: "caption", url: value, label: path || null, ext });
  } else if (MEDIA_EXTENSIONS.has(ext)) {
    assets.push({ kind: "media", url: value, label: path || null, ext });
  }
  return assets;
}

function dedupeAssets(assets) {
  const seen = new Set();
  return assets.filter((asset) => {
    const key = `${asset.kind}:${asset.url}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function normalizeDate(value) {
  if (!value) {
    return null;
  }
  const match = String(value).match(/(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : null;
}

function extractLessonId(url) {
  if (!url) {
    return null;
  }
  const match = String(url).match(/([0-9a-zA-Z]{8,}(?:-[0-9a-zA-Z]{4,})+)/);
  return match ? match[1] : null;
}

function mediaExtension(url) {
  const match = String(url).match(/\.([a-zA-Z0-9]{2,5})(?:$|\?)/);
  return match ? match[1].toLowerCase() : null;
}

async function exportCookies(hosts) {
  const all = [];
  const seen = new Set();
  for (const host of hosts) {
    const cleanHost = String(host).replace(/^\./, "");
    const cookies = await browser.cookies.getAll({ domain: cleanHost });
    for (const cookie of cookies) {
      const key = `${cookie.domain}:${cookie.path}:${cookie.name}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      all.push({
        name: cookie.name,
        value: cookie.value,
        domain: cookie.domain,
        path: cookie.path || "/",
        secure: Boolean(cookie.secure),
        httpOnly: Boolean(cookie.httpOnly),
        expirationDate: cookie.expirationDate ? Math.floor(cookie.expirationDate) : null,
        sameSite: cookie.sameSite || null
      });
    }
  }
  return all;
}
