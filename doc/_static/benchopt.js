
// Adjust the height of benchmark result iframes based on messages from them
window.addEventListener("message", function(event) {
  if (event.data?.source === "benchopt-result-height") {
    // Match the iframe that sent the message
    for (const iframe of document.querySelectorAll("iframe.benchmark_result")) {
      try {
        if (iframe.contentWindow === event.source) {
          iframe.style.height = event.data.height + "px";
          break;
        }
      } catch(e) { /* ignore */ }
    }
  }
});

// Replace all command code blocks by their equivalent CLI call on page load
window.addEventListener("load", function() {
  for (const cmd of document.querySelectorAll("pre.cmd-equiv")) {
    var code_elem = cmd.parentElement.previousElementSibling;
    var cmd_html = cmd.children[0].children[0].innerHTML;
    code_elem.firstChild.firstChild.innerHTML = cmd_html;
    cmd.setAttribute("style", "display: none;");
  }

  // Show folded summaries inside dropdown headers.
  for (const dd of document.querySelectorAll("details.sd-dropdown.has-folded-summary")) {
    const bodySummary = dd.querySelector(":scope > .sd-summary-content .folded-summary");
    const summaryText = dd.querySelector(":scope > .sd-summary-title .sd-summary-text");
    if (!bodySummary || !summaryText) {
      continue;
    }
    const cloned = bodySummary.cloneNode(true);
    cloned.classList.add("folded-summary-in-header");
    summaryText.appendChild(cloned);
  }
});
