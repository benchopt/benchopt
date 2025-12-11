
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
window.onload = function() {
  for (const cmd of document.querySelectorAll("pre.cmd-equiv")) {
    var code_elem = cmd.parentElement.previousElementSibling;
    var cmd_html = cmd.children[0].children[0].innerHTML;
    code_elem.firstChild.firstChild.innerHTML = cmd_html;
    cmd.setAttribute("style", "display: none;");
  }
};
