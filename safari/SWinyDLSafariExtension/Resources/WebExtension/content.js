(function () {
  function collectPageContext() {
    const iframeUrls = Array.from(document.querySelectorAll("iframe[src]"))
      .map((node) => node.src)
      .filter(Boolean);
    const anchorUrls = Array.from(document.querySelectorAll("a[href]"))
      .map((node) => node.href)
      .filter((href) => /echo360|\/ess\/portal\/section\//i.test(href));
    const mediaLinks = Array.from(document.querySelectorAll("video[src], track[src]"))
      .map((node) => node.src)
      .filter(Boolean);
    return {
      pageUrl: window.location.href,
      pageTitle: document.title,
      iframeUrls,
      anchorUrls,
      mediaLinks
    };
  }

  browser.runtime.onMessage.addListener((message) => {
    if (message && message.type === "collect-page-context") {
      return Promise.resolve(collectPageContext());
    }
    return false;
  });
})();
