
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
  for (const cmd of document.querySelectorAll("pre.code-cell-equiv")) {
    var code_elem = cmd.parentElement.previousElementSibling;
    if (!code_elem.className.includes("highlight")){
      // Case where the output figure is above the command
      code_elem = code_elem.previousElementSibling;
    }

    var cmd_html = cmd.children[0].innerHTML;
    code_elem.firstChild.innerHTML = cmd_html;
    cmd.setAttribute("style", "display: none;");
  }

  // Move folded summary on div outside the dropdown content.
  for (const dd of document.querySelectorAll("details.sd-dropdown.has-folded-summary")) {
    const bodySummary = dd.querySelector(":scope > .sd-summary-content .folded-summary");
    const summaryText = dd.querySelector(":scope > .sd-summary-title .sd-summary-text");
    if (!bodySummary || !summaryText) {
      continue;
    }
    summaryText.appendChild(bodySummary);
    bodySummary.classList.add("folded-summary");
  }
});

// Sync the landing page overview figure with the page theme and the goal tabs
function initOverviewFigure() {
  const obj = document.querySelector("object.benchopt-overview");
  const svg = obj?.contentDocument?.documentElement;
  if (!svg || svg.dataset.synced) return;
  svg.dataset.synced = "1";

  const html = document.documentElement;
  const setTheme = () => svg.setAttribute("data-theme", html.dataset.theme || "light");
  setTheme();
  new MutationObserver(setTheme).observe(html, {attributes: true, attributeFilter: ["data-theme"]});

  // Hovering the tabs highlights the selected goal, hovering a goal selects its tab
  const tabs = document.querySelector(".goal-tabs");
  if (!tabs) return;
  const inputs = [...tabs.querySelectorAll(":scope > input")];
  const focus = () => svg.setAttribute("data-focus", inputs.findIndex(x => x.checked));
  tabs.addEventListener("mouseenter", focus);
  tabs.addEventListener("change", focus);
  tabs.addEventListener("mouseleave", () => svg.removeAttribute("data-focus"));
  inputs.forEach((input, i) => {
    svg.getElementById("goal" + i)?.addEventListener("mouseenter", () => { input.checked = true; });
  });
}
window.addEventListener("load", function() {
  initOverviewFigure();
  document.querySelector("object.benchopt-overview")?.addEventListener("load", initOverviewFigure);
});
