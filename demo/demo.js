/*
  ClauseGuard - shared demo page behaviour.
  Handles: reading-time estimate, local-only page timer, checkbox nudge,
  Judge Mode toggle/banner, and the comparison-dashboard localStorage reader.

  Nothing in this file calls the backend or the extension. Scanning and
  classification are performed exclusively by the browser extension's
  content script, which is the only code that talks to the FastAPI service.
*/
(function () {
  "use strict";

  const JUDGE_MODE_KEY = "clauseguard_judge_mode";
  const SCAN_RESULTS_KEY = "clauseguard_scan_results";
  const WORDS_PER_MINUTE = 200;

  function isJudgeModeEnabled() {
    return localStorage.getItem(JUDGE_MODE_KEY) === "1";
  }

  function setJudgeMode(enabled) {
    localStorage.setItem(JUDGE_MODE_KEY, enabled ? "1" : "0");
  }

  function renderJudgeBanner(container) {
    if (!container) return;
    if (!isJudgeModeEnabled()) {
      container.innerHTML = "";
      container.style.display = "none";
      return;
    }
    container.style.display = "block";
    container.innerHTML =
      "Judge Mode: Follow the user journey, accept nothing, then run ClauseGuard.";
  }

  function initGalleryJudgeToggle(checkboxEl, bannerEl) {
    if (checkboxEl) {
      checkboxEl.checked = isJudgeModeEnabled();
      checkboxEl.addEventListener("change", () => {
        setJudgeMode(checkboxEl.checked);
        renderJudgeBanner(bannerEl);
      });
    }
    renderJudgeBanner(bannerEl);
  }

  function estimateReadingMinutes(clauseEls) {
    const text = Array.from(clauseEls)
      .map((el) => el.textContent || "")
      .join(" ");
    const words = text.trim().split(/\s+/).filter(Boolean).length;
    const minutes = Math.max(1, Math.round(words / WORDS_PER_MINUTE));
    return { words, minutes };
  }

  function initScenarioPage(options) {
    const {
      clauseSelector = ".tc-clause",
      checkboxId = "cg-accept-checkbox",
      primaryButtonId = "cg-primary-action",
      readingTimeId = "cg-reading-time",
      timerId = "cg-elapsed-timer",
      nudgeId = "cg-review-nudge",
      judgeBannerId = "cg-judge-banner",
    } = options || {};

    const clauseEls = document.querySelectorAll(clauseSelector);
    const checkbox = document.getElementById(checkboxId);
    const primaryButton = document.getElementById(primaryButtonId);
    const readingTimeEl = document.getElementById(readingTimeId);
    const timerEl = document.getElementById(timerId);
    const nudgeEl = document.getElementById(nudgeId);
    const judgeBannerEl = document.getElementById(judgeBannerId);

    renderJudgeBanner(judgeBannerEl);

    if (readingTimeEl) {
      const { minutes } = estimateReadingMinutes(clauseEls);
      readingTimeEl.textContent = `Estimated reading time: ${minutes} minute${
        minutes === 1 ? "" : "s"
      } (estimate, ~200 words/min)`;
    }

    const startTime = performance.now();
    let elapsedTimerHandle = null;
    let stopped = false;

    function renderElapsed() {
      if (stopped || !timerEl) return;
      const seconds = Math.round((performance.now() - startTime) / 1000);
      timerEl.textContent = `You reached the Accept step in ${seconds} second${
        seconds === 1 ? "" : "s"
      }.`;
    }

    if (timerEl) {
      renderElapsed();
      elapsedTimerHandle = setInterval(renderElapsed, 1000);
    }

    if (checkbox && primaryButton) {
      primaryButton.disabled = !checkbox.checked;
      checkbox.addEventListener("change", () => {
        primaryButton.disabled = !checkbox.checked;

        if (checkbox.checked) {
          if (elapsedTimerHandle) {
            clearInterval(elapsedTimerHandle);
            stopped = true;
            renderElapsed();
          }
          if (nudgeEl) {
            nudgeEl.textContent = `You are about to accept ${clauseEls.length} clauses. Have you reviewed them?`;
            nudgeEl.classList.add("cg-visible");
          }

          // Let the ClauseGuard extension (if loaded) know the user just
          // claimed to have reviewed the Terms, so it can automatically
          // run its scan at exactly that moment. This page never talks to
          // the backend itself - only the extension's content script does.
          window.dispatchEvent(
            new CustomEvent("clauseguard:checkbox-checked", {
              detail: { totalClauses: clauseEls.length },
            })
          );
        } else if (nudgeEl) {
          nudgeEl.classList.remove("cg-visible");
        }
      });
    }

    if (primaryButton) {
      primaryButton.addEventListener("click", (event) => {
        event.preventDefault();
        primaryButton.textContent = "Registration simulated (demo only)";
      });
    }
  }

  function readScanResults() {
    try {
      const raw = localStorage.getItem(SCAN_RESULTS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (err) {
      return [];
    }
  }

  function clearScanResults() {
    localStorage.removeItem(SCAN_RESULTS_KEY);
  }

  window.ClauseGuardDemo = {
    initScenarioPage,
    initGalleryJudgeToggle,
    renderJudgeBanner,
    isJudgeModeEnabled,
    readScanResults,
    clearScanResults,
    SCAN_RESULTS_KEY,
  };
})();
