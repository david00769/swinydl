(function () {
  function collectPageContext() {
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
      pageText: collectPageText(),
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
  }

  function isSupportedEchoUrl(value) {
    return /echo360|\/ess\/portal\/section\/|\/lti\//i.test(String(value || ""));
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

  function collectPageText() {
    return [
      document.title,
      document.querySelector("[aria-current='page']")?.textContent || "",
      document.querySelector("iframe[title]")?.getAttribute("title") || "",
      document.body?.className || ""
    ].join(" ");
  }

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

  function publishPageContext() {
    try {
      browser.runtime.sendMessage({
        type: "page-context-updated",
        context: collectPageContext()
      });
    } catch (_error) {
    }
  }

  browser.runtime.onMessage.addListener((message) => {
    if (message && message.type === "collect-page-context") {
      return Promise.resolve(collectPageContext());
    }
    return false;
  });

  publishPageContext();
  window.addEventListener("load", publishPageContext, { once: true });
})();
