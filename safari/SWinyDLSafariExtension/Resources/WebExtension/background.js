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
    case "open-app":
      return sendNative("open_app", {});
    case "export-debug-log":
      return exportDebugLogForActiveTab();
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
  const active = await collectActiveTabContext();
  if (!active.ok) {
    return active;
  }
  const { context, courseUrl } = active;

  try {
    const course = await discoverCourse(courseUrl, context);
    return {
      ok: true,
      course: decorateCourseDisplay(course, context, courseUrl),
      sourcePageUrl: context.pageUrl,
      courseUrl
    };
  } catch (error) {
    return { ok: false, error: `Found EchoVideo on this page, but could not load the course inventory: ${String(error?.message || error)}` };
  }
}

async function collectActiveTabContext() {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url) {
    return { ok: false, error: "No active Safari tab was found." };
  }

  let context = emptyPageContext(tab.url, tab.title || "");
  const contexts = [context];
  try {
    context = await browser.tabs.sendMessage(tab.id, { type: "collect-page-context" });
    rememberPageContext({ tab }, context);
    contexts.push(context);
  } catch (_error) {
  }

  contexts.push(...(await collectInjectedPageContexts(tab.id)));
  context = mergePageContexts(...contexts, ...(tabContextCache.get(tab.id) || []));
  const courseUrl = deriveCourseUrl(context);
  if (!courseUrl) {
    if (looksLikeCanvasEchoVideoPage(context)) {
      return { ok: false, error: "This looks like a Canvas EchoVideo page, but Safari did not expose the EchoVideo launch URL yet. Reload the Canvas page, then open SWinyDL again." };
    }
    return { ok: false, error: "This page does not look like a supported Canvas or Echo360 course entrypoint." };
  }

  return { ok: true, tab, context, courseUrl };
}

async function exportDebugLogForActiveTab() {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url) {
    return { ok: false, error: "No active Safari tab was found." };
  }

  let error = null;
  let active = null;
  try {
    active = await collectActiveTabContext();
  } catch (caught) {
    error = String(caught?.message || caught);
  }

  const context = active?.context || mergePageContexts(
    emptyPageContext(tab.url, tab.title || ""),
    ...(tabContextCache.get(tab.id) || [])
  );
  const courseUrl = active?.courseUrl || deriveCourseUrl(context);
  const debugLog = buildDebugLog({
    tab,
    context,
    courseUrl,
    error: error || (active?.ok === false ? active.error : null)
  });
  return { ok: true, debugLog };
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
    ...(context.pageUrls || []),
    ...(context.iframeUrls || []),
    ...(context.anchorUrls || []),
    ...(context.formActionUrls || []),
    ...(context.dataUrls || []),
    ...(context.inputUrls || []),
    ...(context.embeddedUrls || []),
    ...(context.storageUrls || [])
  ].filter(Boolean).map(String);

  const uniqueCandidates = Array.from(new Set(candidates));
  const preferredPatterns = [
    /\/ess\/portal\/section\/[^/?#]+/i,
    /\/section\/[^/?#]+/i,
    /\/lti\/[^/?#]+/i
  ];
  for (const pattern of preferredPatterns) {
    const value = uniqueCandidates.find((candidate) => pattern.test(candidate));
    if (value) {
      return value;
    }
  }

  for (const value of uniqueCandidates) {
    if (isSupportedEchoCourseUrl(value)) {
      return value;
    }
  }
  return null;
}

function isSupportedEchoCourseUrl(value) {
  const text = String(value || "");
  if (!/echo360|streaming\.sydney\.edu\.au/i.test(text)) {
    return false;
  }
  return !/\/(assets|img|images|favicon)|\/api\/?lti\/?$/i.test(text);
}

async function collectInjectedPageContexts(tabId) {
  if (!browser.scripting?.executeScript) {
    return [];
  }
  try {
    const results = await browser.scripting.executeScript({
      target: { tabId, allFrames: true },
      func: collectPageContextFromDocument
    });
    return (results || []).map((item) => item.result).filter(Boolean);
  } catch (_error) {
    return [];
  }
}

function emptyPageContext(pageUrl = "", pageTitle = "") {
  return {
    pageUrl,
    pageUrls: [],
    pageTitle,
    pageText: "",
    iframeUrls: [],
    anchorUrls: [],
    formActionUrls: [],
    dataUrls: [],
    inputUrls: [],
    embeddedUrls: [],
    storageUrls: [],
    lessonCandidates: [],
    mediaLinks: [],
    titleCandidates: [],
    textSnippets: []
  };
}

function looksLikeCanvasEchoVideoPage(context) {
  const haystack = `${context.pageUrl || ""} ${context.pageTitle || ""} ${context.pageText || ""}`;
  return /instructure\.com\/courses\/\d+\/external_tools\/\d+/i.test(haystack) && /echo(video|360)/i.test(haystack);
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
  const merged = emptyPageContext();
  for (const entry of contexts.flat()) {
    const context = entry?.context || entry;
    if (!context) {
      continue;
    }
    merged.pageUrl = merged.pageUrl || context.pageUrl || "";
    merged.pageTitle = merged.pageTitle || context.pageTitle || "";
    merged.pageText = `${merged.pageText} ${context.pageText || ""}`.trim();
    if (context.pageUrl) {
      merged.pageUrls.push(context.pageUrl);
    }
    merged.pageUrls.push(...(context.pageUrls || []));
    for (const key of ["iframeUrls", "anchorUrls", "formActionUrls", "dataUrls", "inputUrls", "embeddedUrls", "storageUrls", "mediaLinks", "titleCandidates", "textSnippets"]) {
      merged[key].push(...(context[key] || []));
    }
    merged.lessonCandidates.push(...(context.lessonCandidates || []));
  }
  for (const key of ["pageUrls", "iframeUrls", "anchorUrls", "formActionUrls", "dataUrls", "inputUrls", "embeddedUrls", "storageUrls", "mediaLinks", "titleCandidates", "textSnippets"]) {
    merged[key] = Array.from(new Set(merged[key].filter(Boolean)));
  }
  const seenLessonCandidates = new Set();
  merged.lessonCandidates = merged.lessonCandidates.filter((candidate) => {
    const url = candidate?.url;
    if (!url || seenLessonCandidates.has(url)) {
      return false;
    }
    seenLessonCandidates.add(url);
    return true;
  });
  return merged;
}

function collectPageContextFromDocument() {
  function isSupportedEchoUrl(value) {
    return /echo360|\/ess\/portal\/section\/|\/lti\//i.test(String(value || ""));
  }

  function extractSupportedUrlsFromText(value) {
    const normalized = String(value || "")
      .replace(/\\u002[fF]/g, "/")
      .replace(/\\\//g, "/")
      .replace(/&amp;/g, "&");
    const matches = normalized.match(/https?:\/\/[^\s"'<>\\)]+/gi) || [];
    return matches
      .map((url) => url.replace(/[.,;]+$/g, ""))
      .filter(isSupportedEchoUrl);
  }

  function extractElementDataUrls(node) {
    const values = [];
    const toolId = node.getAttribute("data-tool-id") || "";
    const toolPath = node.getAttribute("data-tool-path") || "";
    if (toolId && toolPath) {
      values.push(`https://${toolId}${toolPath}`);
    }
    for (const attr of ["data-url", "data-href", "data-tool-id", "data-tool-path"]) {
      values.push(node.getAttribute(attr) || "");
    }
    return values.flatMap(extractSupportedUrlsFromText);
  }

  const iframeUrls = Array.from(document.querySelectorAll("iframe[src]"))
    .map((node) => node.src)
    .filter(Boolean);
  const anchorUrls = Array.from(document.querySelectorAll("a[href]"))
    .map((node) => node.href)
    .filter(isSupportedEchoUrl);
  const formActionUrls = Array.from(document.querySelectorAll("form[action]"))
    .map((node) => node.action)
    .filter(isSupportedEchoUrl);
  const dataUrls = Array.from(document.querySelectorAll("[data-tool-id], [data-tool-path], [data-url], [data-href]"))
    .flatMap(extractElementDataUrls)
    .filter(isSupportedEchoUrl);
  const inputUrls = Array.from(document.querySelectorAll("input[type='hidden'][value], input[value]"))
    .flatMap((node) => extractSupportedUrlsFromText(node.value));
  const embeddedUrls = Array.from(document.scripts)
    .flatMap((node) => extractSupportedUrlsFromText(node.textContent || ""));
  const storageUrls = collectStorageUrls();
  const lessonCandidates = collectLessonCandidates([...embeddedUrls, ...storageUrls]);
  const mediaLinks = Array.from(document.querySelectorAll("video[src], track[src]"))
    .map((node) => node.src)
    .filter(Boolean);
  const titleCandidates = collectTitleCandidates();
  const textSnippets = collectTextSnippets(titleCandidates);

  return {
    pageUrl: window.location.href,
    pageTitle: document.title,
    pageText: [
      document.title,
      document.querySelector("[aria-current='page']")?.textContent || "",
      document.querySelector("iframe[title]")?.getAttribute("title") || "",
      document.body?.className || ""
    ].join(" "),
    iframeUrls,
    anchorUrls,
    formActionUrls,
    dataUrls,
    inputUrls,
    embeddedUrls,
    storageUrls,
    lessonCandidates,
    mediaLinks,
    titleCandidates,
    textSnippets
  };

  function collectLessonCandidates(embeddedUrls) {
    const candidates = [];
    const lessonAnchors = Array.from(document.querySelectorAll("a[href*='/lesson/'], a[href*='/classroom']"));
    for (const anchor of lessonAnchors) {
      candidates.push({
        url: anchor.href,
        title: anchor.getAttribute("aria-label") || anchor.getAttribute("title") || anchor.textContent || "",
        text: anchor.closest("tr, li, article, [role='row'], [class*='lesson'], [class*='class']")?.textContent || anchor.textContent || ""
      });
    }
    for (const url of embeddedUrls.filter((value) => /\/lesson\//i.test(value))) {
      candidates.push({ url, title: "", text: "" });
    }
    return candidates;
  }

  function collectStorageUrls() {
    const urls = [];
    for (const store of [window.localStorage, window.sessionStorage]) {
      try {
        for (let index = 0; index < store.length; index += 1) {
          const key = store.key(index);
          urls.push(...extractSupportedUrlsFromText(store.getItem(key) || ""));
        }
      } catch (_error) {
      }
    }
    return urls;
  }

  function collectTitleCandidates() {
    const selectors = [
      "[aria-current='page']",
      ".ic-app-course-menu .active",
      ".pages .active",
      ".course-title",
      ".ellipsible",
      "h1",
      "h2",
      "iframe[title]"
    ];
    return selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)))
      .map((node) => node.getAttribute("title") || node.getAttribute("aria-label") || node.textContent || "")
      .map((value) => value.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .slice(0, 12);
  }

  function collectTextSnippets(titleCandidates) {
    return [
      document.title,
      ...titleCandidates,
      document.querySelector("main")?.textContent || document.body?.innerText || ""
    ]
      .map((value) => value.replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .map((value) => value.slice(0, 240))
      .slice(0, 10);
  }
}

async function discoverCourse(courseUrl, context = {}) {
  const hostname = extractCourseHostname(courseUrl) || "https://view.streaming.sydney.edu.au:8443";
  const platform = isEcho360CloudHost(hostname) ? "cloud" : "classic";
  const courseUuid = extractCourseUuid(courseUrl, platform === "cloud");
  const fullCourseUrl = extractCourseHostname(courseUrl)
    ? courseUrl
    : `${hostname}/ess/portal/section/${courseUuid}`;

  let course;
  if (platform === "cloud") {
    try {
      const payload = await fetchJson(`${hostname}/section/${courseUuid}/syllabus`);
      course = parseCloudLessons(hostname, payload, fullCourseUrl, courseUuid);
    } catch (error) {
      course = buildCloudCourseFromPageContext(hostname, context, fullCourseUrl, courseUuid);
      if (!course.lessons.length) {
        throw error;
      }
    }
  } else {
    const payload = await fetchJson(`${hostname}/ess/client/api/sections/${courseUuid}/section-data.json?pageSize=100`);
    course = parseClassicLessons(payload, fullCourseUrl, hostname, courseUuid);
  }

  for (const lesson of course.lessons) {
    lesson.assets = dedupeAssets([...(lesson.assets || []), ...(await resolveLessonAssets(lesson.lesson_url))]);
  }
  return course;
}

function decorateCourseDisplay(course, context, courseUrl) {
  const title = bestCourseTitle(course, context);
  const contextLabel = bestContextLabel(context, courseUrl);
  return {
    ...course,
    course_title: title,
    course_description: contextLabel === title ? null : contextLabel,
    course_context_label: course.platform
  };
}

function bestCourseTitle(course, context) {
  const candidates = [
    course?.course_title,
    ...(course?.lessons || []).map((lesson) => lesson.course_name),
    ...(context.titleCandidates || []),
    context.pageTitle,
    ...(context.textSnippets || [])
  ];
  for (const candidate of candidates) {
    const title = cleanCourseTitle(candidate);
    if (title) {
      return title;
    }
  }
  return "EchoVideo Course";
}

function bestContextLabel(context, courseUrl) {
  const candidates = [
    context.pageTitle,
    ...(context.titleCandidates || []),
    courseUrl
  ];
  for (const candidate of candidates) {
    const label = cleanDisplayText(candidate);
    if (label && !isPlaceholderCourseTitle(label)) {
      return label;
    }
  }
  return null;
}

function cleanCourseTitle(value) {
  const text = cleanDisplayText(value);
  if (!text || isPlaceholderCourseTitle(text)) {
    return "";
  }
  const parts = text
    .split(/\s*[>|:\u203a]\s*/)
    .map((part) => part.trim())
    .filter(Boolean)
    .filter((part) => !/^(canvas|echo(video|360)|classes|q&a|study guide|search|dashboard|courses)$/i.test(part));
  const useful = parts.find((part) => !isPlaceholderCourseTitle(part));
  return useful || text;
}

function cleanDisplayText(value) {
  return String(value || "")
    .replace(/\s+/g, " ")
    .replace(/\bEchoVideo\b\s*/gi, "")
    .trim()
    .replace(/^[-:|>\u203a]+|[-:|>\u203a]+$/g, "")
    .trim();
}

function isPlaceholderCourseTitle(value) {
  return /^(untitled course|echo(video)? course|course|classes|loading|home)$/i.test(String(value || "").trim());
}

function buildDebugLog({ tab, context, courseUrl, error }) {
  const manifest = browser.runtime.getManifest ? browser.runtime.getManifest() : {};
  return sanitizeDebugValue({
    generatedAt: new Date().toISOString(),
    extension: {
      name: manifest.name || "SWinyDL Safari",
      version: manifest.version || null,
      userAgent: navigator.userAgent,
      platform: navigator.platform
    },
    activeTab: {
      url: tab?.url || null,
      title: tab?.title || null
    },
    discovery: {
      derivedCourseUrl: courseUrl || null,
      error: error || null,
      pageUrl: context.pageUrl,
      pageTitle: context.pageTitle,
      pageText: context.pageText,
      candidateEchoUrls: allCandidateUrls(context),
      iframeUrls: context.iframeUrls,
      anchorUrls: context.anchorUrls,
      formActionUrls: context.formActionUrls,
      dataUrls: context.dataUrls,
      embeddedUrls: context.embeddedUrls,
      mediaLinks: context.mediaLinks,
      titleCandidates: context.titleCandidates,
      textSnippets: context.textSnippets,
      lessonCandidates: context.lessonCandidates
    },
    privacy: {
      sanitized: true,
      excluded: [
        "cookies",
        "localStorage values",
        "sessionStorage values",
        "hidden input values",
        "full raw HTML"
      ]
    }
  });
}

function allCandidateUrls(context) {
  return Array.from(new Set([
    context.pageUrl,
    ...(context.pageUrls || []),
    ...(context.iframeUrls || []),
    ...(context.anchorUrls || []),
    ...(context.formActionUrls || []),
    ...(context.dataUrls || []),
    ...(context.inputUrls || []),
    ...(context.embeddedUrls || []),
    ...(context.storageUrls || []),
    ...(context.mediaLinks || [])
  ].filter(Boolean)));
}

function sanitizeDebugValue(value) {
  if (Array.isArray(value)) {
    return value.map(sanitizeDebugValue);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => !/cookie|storageValue|hiddenInputValue/i.test(key))
        .map(([key, item]) => [key, sanitizeDebugValue(item)])
    );
  }
  if (typeof value === "string") {
    return sanitizeDebugString(value);
  }
  return value;
}

function sanitizeDebugString(value) {
  const withRedactedUrls = String(value).replace(/https?:\/\/[^\s"'<>\\)]+/gi, (url) => sanitizeUrl(url));
  return withRedactedUrls
    .replace(/\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+/gi, "$1 [REDACTED]")
    .replace(/\b(access[_-]?token|id[_-]?token|refresh[_-]?token|session|cookie|authorization|signature|sig|key|code)=([^&\s]+)/gi, "$1=[REDACTED]");
}

function sanitizeUrl(value) {
  try {
    const url = new URL(value);
    for (const key of Array.from(url.searchParams.keys())) {
      if (/token|session|cookie|auth|sig|signature|key|code|state/i.test(key)) {
        url.searchParams.set(key, "[REDACTED]");
      }
    }
    return url.toString();
  } catch (_error) {
    return String(value);
  }
}

function buildCloudCourseFromPageContext(hostname, context, sourceUrl, courseUuid) {
  const candidates = [];
  for (const candidate of context.lessonCandidates || []) {
    candidates.push(candidate);
  }
  for (const url of [...(context.anchorUrls || []), ...(context.embeddedUrls || []), ...(context.storageUrls || [])]) {
    if (/\/lesson\//i.test(url)) {
      candidates.push({ url, title: "", text: "" });
    }
  }

  const seen = new Set();
  const lessons = [];
  for (const candidate of candidates) {
    const lessonUrl = normalizeLessonUrl(candidate.url, hostname);
    if (!lessonUrl || seen.has(lessonUrl)) {
      continue;
    }
    seen.add(lessonUrl);
    const index = lessons.length + 1;
    const lessonId = extractLessonId(lessonUrl) || `cloud-page-${index}`;
    const label = cleanLessonTitle(candidate.title || candidate.text) || `Lesson ${index}`;
    lessons.push({
      lesson_id: lessonId,
      title: label,
      date: normalizeDate(`${candidate.text || ""} ${candidate.title || ""}`),
      lesson_url: lessonUrl,
      index,
      assets: []
    });
  }

  return {
    source_url: sourceUrl,
    hostname,
    platform: "cloud-page",
    course_uuid: courseUuid,
    course_id: null,
    course_title: context.pageTitle || "EchoVideo Course",
    lessons
  };
}

function normalizeLessonUrl(value, hostname) {
  const text = String(value || "");
  if (!/\/lesson\//i.test(text)) {
    return null;
  }
  if (/^https?:\/\//i.test(text)) {
    return text;
  }
  return `${hostname}${text.startsWith("/") ? "" : "/"}${text}`;
}

function cleanLessonTitle(value) {
  const lines = String(value || "")
    .split(/\n|\r|\t/)
    .map((line) => line.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .filter((line) => !/^(watch|play|open|details|q&a|study guide|search|\d+)$|comments?/i.test(line));
  return lines[0] || "";
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
    course_name: extractCloudCourseTitle(item),
    date: normalizeDate(item.lesson?.startTimeUTC || lessonNode.createdAt || item.groupInfo?.createdAt),
    lesson_url: `${hostname}/lesson/${lessonId}/classroom`,
    index,
    assets: detectAssets(item)
  };
}

function extractCloudCourseTitle(item) {
  return item.lesson?.video?.published?.courseName
    || item.lesson?.lesson?.courseName
    || item.section?.name
    || item.groupInfo?.sectionName
    || "Untitled Course";
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
