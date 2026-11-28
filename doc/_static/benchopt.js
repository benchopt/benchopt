
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

// Pass the page theme to the landing page figures, and sync the overview with the goal tabs
function initFigure(obj) {
  const svg = obj?.contentDocument?.documentElement;
  if (!svg || svg.tagName.toLowerCase() !== "svg" || svg.dataset.synced) return;
  svg.dataset.synced = "1";

  const html = document.documentElement;
  const setTheme = () => svg.setAttribute("data-theme", html.dataset.theme || "light");
  setTheme();
  new MutationObserver(setTheme).observe(html, {attributes: true, attributeFilter: ["data-theme"]});
  if (obj.classList.contains("benchopt-add")) {
    // The pills in the figure choose the benchmark it shows.
    const keys = ["house", "llm", "ts"];
    const show = (key) => svg.setAttribute("data-example", key);
    // On first view, show each example in turn; any interaction stops it.
    let demo = null;
    const stop = () => { clearTimeout(demo); demo = null; };
    const step = (i) => {
      show(keys[i % keys.length]);
      if (i < keys.length) demo = setTimeout(() => step(i + 1), 2600);
    };
    svg.querySelectorAll(".pill-btn").forEach((pill) => {
      pill.addEventListener("click", () => { stop(); show(pill.dataset.key); });
    });
    new IntersectionObserver((entries, observer) => {
      if (entries[0].isIntersecting) {
        observer.disconnect();
        demo = setTimeout(() => step(1), 2600);
      }
    }, {threshold: 0.6}).observe(obj);
    ["pointerdown", "mouseover"].forEach((ev) => svg.addEventListener(ev, stop));
    return;
  }
  if (!obj.classList.contains("benchopt-overview")) return;

  // Links open in the page, resolved against the figure's own URL
  svg.querySelectorAll("a[href]").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      window.location.href = new URL(a.getAttribute("href"), obj.data).href;
    });
  });

  // The figure highlights the selected goal tab once the reader interacts.
  // The SVG styles let a hover take over, so no pointer state is kept here.
  const tabs = document.querySelector(".goal-tabs");
  if (!tabs) return;
  const inputs = [...tabs.querySelectorAll(":scope > input")];
  let active = false;
  const apply = () => active
    ? svg.setAttribute("data-focus", inputs.findIndex(x => x.checked))
    : svg.removeAttribute("data-focus");
  // On first view, highlight each goal in turn to show the figure reacts;
  // any interaction stops the demo.
  let demo = null;
  const stopDemo = () => { if (demo) { clearTimeout(demo); demo = null; apply(); } };
  const runDemo = (i) => {
    if (i < inputs.length) {
      inputs[i].checked = true;
      svg.setAttribute("data-focus", i);
      demo = setTimeout(() => runDemo(i + 1), 1400);
    } else {
      inputs[0].checked = true;
      apply();
      demo = null;
    }
  };
  new IntersectionObserver((entries, observer) => {
    if (entries[0].isIntersecting) {
      observer.disconnect();
      demo = setTimeout(() => runDemo(0), 600);
    }
  }, {threshold: 0.6}).observe(obj);
  ["pointerdown", "mouseover"].forEach((ev) => {
    svg.addEventListener(ev, stopDemo);
    tabs.addEventListener(ev, stopDemo);
  });
  tabs.addEventListener("change", () => { active = true; apply(); });
  // Clicking the selected tab again, or the figure background, shows everything
  tabs.querySelectorAll(":scope > label").forEach((label) => {
    let wasChecked = false;
    label.addEventListener("pointerdown", () => { wasChecked = label.control.checked; });
    label.addEventListener("click", () => { if (wasChecked) { active = !active; apply(); } });
  });
  svg.addEventListener("click", (e) => { if (!e.target.closest(".goal, a")) { active = false; apply(); } });
  inputs.forEach((input, i) => {
    const goal = svg.getElementById("goal" + i);
    const select = () => { input.checked = true; active = true; apply(); };
    goal?.addEventListener("mouseenter", select);
    goal?.addEventListener("pointerup", (e) => { if (e.pointerType === "touch") select(); });
  });
}
window.addEventListener("load", function() {
  for (const obj of document.querySelectorAll("object.benchopt-figure")) {
    initFigure(obj);
    obj.addEventListener("load", () => initFigure(obj));
  }
});
