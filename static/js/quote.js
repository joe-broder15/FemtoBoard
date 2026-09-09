(() => {
  "use strict";

  function getComposerBody() {
    const panel = document.querySelector("[data-composer]");
    if (!panel) return null;
    return panel.querySelector("[data-composer-body]");
  }

  document.addEventListener("click", (event) => {
    const quoteButton = event.target.closest(".quote-btn");
    if (quoteButton) {
      const postId = quoteButton.getAttribute("data-post-id");
      const body = getComposerBody();
      const panel = document.getElementById("composer-panel");
      if (panel && panel.classList.contains("composer-collapsed")) {
        panel.classList.remove("composer-collapsed");
      }
      if (body) {
        const insertion = `>>${postId}\n`;
        const start = body.selectionStart ?? body.value.length;
        const end = body.selectionEnd ?? body.value.length;
        body.value = body.value.slice(0, start) + insertion + body.value.slice(end);
        body.focus();
        const cursor = start + insertion.length;
        body.setSelectionRange(cursor, cursor);
      }
      return;
    }

    const toggleButton = event.target.closest("[data-composer-toggle]");
    if (toggleButton) {
      const panel = document.getElementById("composer-panel");
      if (panel) panel.classList.toggle("composer-collapsed");
    }
  });

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (form instanceof HTMLFormElement && form.hasAttribute("data-confirm")) {
      const message = form.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    }
  });
})();
