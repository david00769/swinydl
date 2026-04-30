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
    const mediaLinks = Array.from(document.querySelectorAll("video[src], track[src]"))
      .map((node) => node.src)
      .filter(Boolean);
    return {
      pageUrl: window.location.href,
      pageTitle: document.title,
      iframeUrls,
      anchorUrls,
      formActionUrls,
      mediaLinks
    };
  }

  function isSupportedEchoUrl(value) {
    return /echo360|\/ess\/portal\/section\/|\/lti\//i.test(String(value || ""));
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
