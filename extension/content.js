/*
  ClauseGuard - content script (demo sites only).

  This script ONLY runs on the fictional local demo pages declared in
  manifest.json (http://127.0.0.1:5500/* and http://localhost:5500/*). It:
    - reads ONLY the trimmed text of explicit `.tc-clause` elements
    - never reads password/email/payment/signup form fields
    - sends exactly one /predict-batch request per user-initiated scan
    - highlights clauses and renders a fixed side panel with the results
    - never auto-accepts or touches the page's Terms checkbox
*/
(function () {
  "use strict";

  const API_BASE_CANDIDATES = ["http://127.0.0.1:8000", "http://localhost:8000"];
  const SCAN_RESULTS_KEY = "clauseguard_scan_results";

  const CATEGORY_META = {
    SAFE: { cssClass: "cg-highlight-safe", short: "Safe" },
    PRIVACY_RISK: { cssClass: "cg-highlight-privacy", short: "Privacy" },
    PAYMENT_RISK: { cssClass: "cg-highlight-payment", short: "Payment" },
    USER_RIGHTS_RISK: { cssClass: "cg-highlight-rights", short: "Rights" },
  };

  const HIGHLIGHT_CLASSES = Object.values(CATEGORY_META).map((m) => m.cssClass);

  let isScanning = false;
  let lastResults = null; // { clauseResults: [{el, prediction}], summary, flaggedIndex }
  let showOnlyFlagged = false;
  let flaggedCursor = -1;

  function getScenarioMeta() {
    return {
      id: document.body.getAttribute("data-clauseguard-scenario") || "unknown",
      title: document.body.getAttribute("data-clauseguard-title") || "Unknown scenario",
    };
  }

  function getClauseElements() {
    return Array.from(document.querySelectorAll(".tc-clause"));
  }

  function clearPreviousBadges() {
    getClauseElements().forEach((el) => {
      HIGHLIGHT_CLASSES.forEach((cls) => el.classList.remove(cls));
      const badge = el.querySelector(".cg-badge");
      if (badge) badge.remove();
      const explanation = el.querySelector(".cg-badge-explanation");
      if (explanation) explanation.remove();
    });
  }

  function ensureFloatingButton() {
    if (document.getElementById("cg-scan-button")) return;

    const button = document.createElement("button");
    button.id = "cg-scan-button";
    button.className = "cg-floating-scan-btn";
    button.type = "button";
    button.textContent = "Scan Terms Before Accepting";
    button.addEventListener("click", handleScanClick);
    document.body.appendChild(button);
  }

  function ensureSidePanel() {
    if (document.getElementById("cg-side-panel")) {
      return document.getElementById("cg-side-panel");
    }

    const panel = document.createElement("div");
    panel.id = "cg-side-panel";
    panel.className = "cg-side-panel cg-hidden";
    panel.innerHTML = `
      <div class="cg-panel-header">
        <strong>ClauseGuard</strong>
        <span id="cg-panel-scenario"></span>
      </div>
      <div id="cg-panel-status" class="cg-panel-status"></div>
      <div id="cg-panel-stats" class="cg-panel-stats"></div>
      <div id="cg-panel-score" class="cg-panel-score"></div>
      <p class="cg-panel-disclaimer">
        This score shows the proportion of clauses classified into a
        prototype attention category. It is not a legal assessment.
      </p>
      <div class="cg-panel-controls">
        <label class="cg-panel-toggle">
          <input type="checkbox" id="cg-only-flagged" />
          Show only flagged clauses
        </label>
        <div class="cg-panel-nav">
          <button id="cg-prev-flagged" type="button">⟵ Prev flagged</button>
          <button id="cg-next-flagged" type="button">Next flagged ⟶</button>
        </div>
        <button id="cg-clear-results" type="button">Clear Results</button>
        <button id="cg-copy-summary" type="button">Copy Summary</button>
        <button id="cg-model-details" type="button">Model Details</button>
      </div>
      <div id="cg-model-details-box" class="cg-model-details-box cg-hidden"></div>
      <p class="cg-panel-footer">
        Processed by a locally running student-trained model.<br />
        Educational prototype using synthetic training data. Results may be
        inaccurate and are not legal advice.
      </p>
    `;
    document.body.appendChild(panel);

    panel.querySelector("#cg-only-flagged").addEventListener("change", (e) => {
      showOnlyFlagged = e.target.checked;
      applyFlaggedFilter();
    });
    panel.querySelector("#cg-prev-flagged").addEventListener("click", () => jumpToFlagged(-1));
    panel.querySelector("#cg-next-flagged").addEventListener("click", () => jumpToFlagged(1));
    panel.querySelector("#cg-clear-results").addEventListener("click", clearResults);
    panel.querySelector("#cg-copy-summary").addEventListener("click", copySummary);
    panel.querySelector("#cg-model-details").addEventListener("click", toggleModelDetails);

    return panel;
  }

  function setPanelStatus(message, isError) {
    const panel = ensureSidePanel();
    panel.classList.remove("cg-hidden");
    const statusEl = panel.querySelector("#cg-panel-status");
    statusEl.textContent = message;
    statusEl.classList.toggle("cg-panel-status-error", Boolean(isError));
  }

  async function fetchFromBackend(path, options) {
    let lastError = null;
    for (const base of API_BASE_CANDIDATES) {
      try {
        const response = await fetch(base + path, options);
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(`HTTP ${response.status}: ${detail}`);
        }
        return await response.json();
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError || new Error("Unknown network error.");
  }

  async function handleScanClick() {
    await performScan({ source: "button" });
  }

  async function performScan({ source }) {
    if (isScanning) return;
    const button = document.getElementById("cg-scan-button");
    const clauseEls = getClauseElements();

    if (clauseEls.length === 0) {
      setPanelStatus("No Terms clauses were found on this page.", true);
      return;
    }

    isScanning = true;
    button.disabled = true;
    const originalLabel = button.textContent;
    button.textContent = "Analysing clauses locally...";
    setPanelStatus("Analysing clauses locally...", false);

    clearPreviousBadges();

    const texts = clauseEls.map((el) => (el.textContent || "").trim());

    try {
      const data = await fetchFromBackend("/predict-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clauses: texts }),
      });

      applyResults(clauseEls, data);
      saveComparisonSummary(data.summary);
      setPanelStatus("Scan complete.", false);
      showAttentionPopup(data.summary);
    } catch (err) {
      setPanelStatus(
        "ClauseGuard could not reach the local analysis service. Start FastAPI and try again.",
        true
      );
      if (source === "checkbox") {
        showAttentionPopup(null, true);
      }
    } finally {
      isScanning = false;
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }

  function applyResults(clauseEls, data) {
    const clauseResults = clauseEls.map((el, index) => ({
      el,
      prediction: data.results[index],
    }));

    clauseResults.forEach(({ el, prediction }, index) => {
      const meta = CATEGORY_META[prediction.label];
      el.classList.add(meta.cssClass);

      const badge = document.createElement("span");
      badge.className = "cg-badge";
      const confidencePct = Math.round(prediction.confidence * 100);
      badge.textContent = `#${index + 1} · ${prediction.friendly_label} · ${confidencePct}% confidence`;
      el.appendChild(badge);

      const explanation = document.createElement("span");
      explanation.className = "cg-badge-explanation";
      explanation.textContent = prediction.message;
      el.appendChild(explanation);
    });

    lastResults = {
      clauseResults,
      summary: data.summary,
    };
    flaggedCursor = -1;

    renderStats(data.summary);
    applyFlaggedFilter();
  }

  function renderStats(summary) {
    const panel = ensureSidePanel();
    const scenario = getScenarioMeta();
    panel.querySelector("#cg-panel-scenario").textContent = scenario.title;

    const statsEl = panel.querySelector("#cg-panel-stats");
    statsEl.innerHTML = `
      <div>Clauses reviewed: <strong>${summary.total_clauses}</strong></div>
      <div>Need attention: <strong>${summary.attention_required}</strong></div>
      <div>No prototype warning: <strong>${summary.safe}</strong></div>
      <div>Privacy attention: <strong>${summary.privacy_attention}</strong></div>
      <div>Payment attention: <strong>${summary.payment_attention}</strong></div>
      <div>User-rights attention: <strong>${summary.user_rights_attention}</strong></div>
    `;

    const attentionPct =
      summary.total_clauses > 0
        ? (summary.attention_required / summary.total_clauses) * 100
        : 0;

    let band = "Few clauses flagged";
    if (attentionPct >= 75) band = "Careful review strongly recommended";
    else if (attentionPct >= 50) band = "Multiple clauses need attention";
    else if (attentionPct >= 25) band = "Review recommended";

    const scoreEl = panel.querySelector("#cg-panel-score");
    scoreEl.innerHTML = `
      <strong>Prototype attention score: ${Math.round(attentionPct)}%</strong>
      <div>${band}</div>
    `;
  }

  function applyFlaggedFilter() {
    if (!lastResults) return;
    lastResults.clauseResults.forEach(({ el, prediction }) => {
      const isFlagged = prediction.is_attention_required;
      el.style.display = showOnlyFlagged && !isFlagged ? "none" : "";
    });
  }

  function jumpToFlagged(direction) {
    if (!lastResults) return;
    const flaggedIndexes = lastResults.clauseResults
      .map((r, idx) => (r.prediction.is_attention_required ? idx : -1))
      .filter((idx) => idx !== -1);

    if (flaggedIndexes.length === 0) return;

    let pointer = flaggedIndexes.indexOf(flaggedCursor);
    pointer = pointer === -1 ? 0 : (pointer + direction + flaggedIndexes.length) % flaggedIndexes.length;
    flaggedCursor = flaggedIndexes[pointer];

    const target = lastResults.clauseResults[flaggedCursor].el;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("cg-flagged-focus");
    setTimeout(() => target.classList.remove("cg-flagged-focus"), 1200);
  }

  function clearResults() {
    clearPreviousBadges();
    getClauseElements().forEach((el) => {
      el.style.display = "";
    });
    lastResults = null;
    flaggedCursor = -1;
    showOnlyFlagged = false;

    const panel = document.getElementById("cg-side-panel");
    if (panel) {
      panel.querySelector("#cg-only-flagged").checked = false;
      panel.querySelector("#cg-panel-stats").innerHTML = "";
      panel.querySelector("#cg-panel-score").innerHTML = "";
      setPanelStatus("Results cleared. Click Scan Terms Before Accepting to re-run.", false);
    }
  }

  function copySummary() {
    if (!lastResults) return;
    const scenario = getScenarioMeta();
    const s = lastResults.summary;
    const text = [
      `ClauseGuard prototype summary - ${scenario.title}`,
      `Total clauses reviewed: ${s.total_clauses}`,
      `Clauses needing attention: ${s.attention_required}`,
      `No prototype warning: ${s.safe}`,
      `Privacy attention: ${s.privacy_attention}`,
      `Payment attention: ${s.payment_attention}`,
      `User-rights attention: ${s.user_rights_attention}`,
      "Educational prototype using synthetic training data. Not legal advice.",
    ].join("\n");

    navigator.clipboard
      .writeText(text)
      .then(() => setPanelStatus("Summary copied to clipboard.", false))
      .catch(() => setPanelStatus("Could not copy summary.", true));
  }

  async function toggleModelDetails() {
    const box = document.getElementById("cg-model-details-box");
    if (!box.classList.contains("cg-hidden")) {
      box.classList.add("cg-hidden");
      return;
    }

    box.classList.remove("cg-hidden");
    box.textContent = "Loading model details...";

    try {
      const info = await fetchFromBackend("/model-info", { method: "GET" });
      box.innerHTML = `
        <div>Encoder: <strong>${info.encoder_name}</strong></div>
        <div>Classes: <strong>${info.class_names.join(", ")}</strong></div>
        <div>Dataset size: <strong>${info.dataset_size}</strong></div>
        <div>Measured test accuracy: <strong>${Math.round(info.test_accuracy * 100)}%</strong></div>
        <div>Trained: <strong>${new Date(info.training_timestamp).toLocaleString()}</strong></div>
      `;
    } catch (err) {
      box.textContent = "Could not load model details. Is the backend running?";
    }
  }

  function saveComparisonSummary(summary) {
    const scenario = getScenarioMeta();
    const attentionPercentage =
      summary.total_clauses > 0
        ? (summary.attention_required / summary.total_clauses) * 100
        : 0;

    const entry = {
      scenarioId: scenario.id,
      scenarioTitle: scenario.title,
      timestamp: new Date().toISOString(),
      totalClauses: summary.total_clauses,
      attentionClauseCount: summary.attention_required,
      categoryCounts: {
        safe: summary.safe,
        privacy_attention: summary.privacy_attention,
        payment_attention: summary.payment_attention,
        user_rights_attention: summary.user_rights_attention,
      },
      attentionPercentage,
    };

    let existing = [];
    try {
      const raw = localStorage.getItem(SCAN_RESULTS_KEY);
      existing = raw ? JSON.parse(raw) : [];
    } catch (err) {
      existing = [];
    }

    existing = existing.filter((item) => item.scenarioId !== entry.scenarioId);
    existing.push(entry);
    localStorage.setItem(SCAN_RESULTS_KEY, JSON.stringify(existing));
  }

  let popupDismissTimer = null;

  function ensureAttentionPopup() {
    if (document.getElementById("cg-attention-popup")) {
      return document.getElementById("cg-attention-popup");
    }
    const popup = document.createElement("div");
    popup.id = "cg-attention-popup";
    popup.className = "cg-attention-popup cg-hidden";
    popup.innerHTML = `
      <button type="button" class="cg-attention-popup-close" aria-label="Dismiss">×</button>
      <div class="cg-attention-popup-title"></div>
      <div class="cg-attention-popup-body"></div>
    `;
    document.body.appendChild(popup);
    popup.querySelector(".cg-attention-popup-close").addEventListener("click", hideAttentionPopup);
    return popup;
  }

  function hideAttentionPopup() {
    const popup = document.getElementById("cg-attention-popup");
    if (popup) popup.classList.add("cg-hidden");
    if (popupDismissTimer) {
      clearTimeout(popupDismissTimer);
      popupDismissTimer = null;
    }
  }

  // Shown right after a scan completes. This is intentionally the most
  // visible feedback in the whole extension: the moment a user ticks "I
  // have reviewed the Terms", this pops up to show whether that claim
  // matches what the clauses actually contain.
  function showAttentionPopup(summary, isOfflineError) {
    const popup = ensureAttentionPopup();
    const titleEl = popup.querySelector(".cg-attention-popup-title");
    const bodyEl = popup.querySelector(".cg-attention-popup-body");

    popup.classList.remove(
      "cg-attention-popup-high",
      "cg-attention-popup-medium",
      "cg-attention-popup-low",
      "cg-attention-popup-offline"
    );

    if (isOfflineError) {
      popup.classList.add("cg-attention-popup-offline");
      titleEl.textContent = "⚠️ ClauseGuard could not check these terms";
      bodyEl.textContent =
        "The local analysis service is unreachable. Start FastAPI and tick the box again to re-check.";
    } else {
      const pct =
        summary.total_clauses > 0
          ? Math.round((summary.attention_required / summary.total_clauses) * 100)
          : 0;

      if (summary.attention_required === 0) {
        popup.classList.add("cg-attention-popup-low");
        titleEl.textContent = "✅ No prototype warning flags found";
        bodyEl.textContent = `All ${summary.total_clauses} clauses matched the "no prototype warning" category in this demo model.`;
      } else {
        popup.classList.add(pct >= 50 ? "cg-attention-popup-high" : "cg-attention-popup-medium");
        titleEl.textContent = `⚠️ ${summary.attention_required} of ${summary.total_clauses} clauses may need your attention`;
        bodyEl.innerHTML = `
          Privacy: <strong>${summary.privacy_attention}</strong> ·
          Payment: <strong>${summary.payment_attention}</strong> ·
          User-rights: <strong>${summary.user_rights_attention}</strong><br />
          Review the highlighted clauses before accepting. This is a prototype signal, not a legal assessment.
        `;
      }
    }

    popup.classList.remove("cg-hidden");
    if (popupDismissTimer) clearTimeout(popupDismissTimer);
    popupDismissTimer = setTimeout(hideAttentionPopup, 12000);
  }

  function init() {
    ensureFloatingButton();
    ensureSidePanel();
    ensureAttentionPopup();

    // When the demo page's own Terms checkbox is ticked, demo.js dispatches
    // this event. We treat "I have reviewed the Terms" as the trigger to
    // actually run the scan automatically, instead of waiting for a
    // separate manual click on the floating button.
    window.addEventListener("clauseguard:checkbox-checked", () => {
      performScan({ source: "checkbox" });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
