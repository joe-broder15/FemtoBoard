(() => {
  "use strict";

  const workerUrl = document.currentScript ? document.currentScript.dataset.workerUrl : null;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : null;
  }

  async function issueChallenge(url) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") || "" },
      credentials: "same-origin",
    });
    if (!response.ok) {
      throw new Error(`challenge request failed: ${response.status}`);
    }
    return response.json();
  }

  function initComposer(panel) {
    const form = panel.querySelector("[data-composer-form]");
    const status = panel.querySelector("[data-composer-status]");
    const submitButton = panel.querySelector("[data-composer-submit]");
    const powIdField = panel.querySelector("[data-pow-id]");
    const powNonceField = panel.querySelector("[data-pow-nonce]");
    const powUrl = panel.getAttribute("data-pow-url");
    if (!form || !status || !submitButton || !powIdField || !powNonceField || !powUrl || !workerUrl) {
      return;
    }

    let worker = null;
    let refreshTimer = null;

    function setStatus(text) {
      status.textContent = text;
    }

    async function refresh() {
      submitButton.disabled = true;
      powIdField.value = "";
      powNonceField.value = "";
      setStatus("Requesting proof-of-work challenge…");
      if (worker) {
        worker.terminate();
        worker = null;
      }
      let challenge;
      try {
        challenge = await issueChallenge(powUrl);
      } catch (err) {
        setStatus("Could not reach the server. Retrying…");
        window.setTimeout(refresh, 5000);
        return;
      }

      setStatus("Solving proof-of-work…");
      worker = new Worker(workerUrl);
      worker.onmessage = (event) => {
        const msg = event.data;
        if (!msg.done) {
          setStatus(`Solving proof-of-work… (${msg.progress.toLocaleString()} tried)`);
          return;
        }
        powIdField.value = challenge.id;
        powNonceField.value = msg.nonce;
        setStatus("Ready.");
        submitButton.disabled = false;
      };
      worker.postMessage({
        challenge: challenge.challenge,
        difficultyBits: challenge.difficulty_bits,
        requestId: challenge.id,
      });

      if (refreshTimer) window.clearTimeout(refreshTimer);
      const expiresInMs = new Date(challenge.expires_at).getTime() - Date.now();
      const refreshInMs = Math.max(expiresInMs - 30000, 10000);
      refreshTimer = window.setTimeout(refresh, refreshInMs);
    }

    form.addEventListener("submit", (event) => {
      if (!powIdField.value || !powNonceField.value) {
        event.preventDefault();
        setStatus("Still solving proof-of-work, please wait…");
      }
    });

    refresh();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-composer]").forEach(initComposer);
  });
})();
