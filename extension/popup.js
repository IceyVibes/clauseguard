/* ClauseGuard - popup script */
(function () {
  "use strict";

  const API_BASE_CANDIDATES = ["http://127.0.0.1:8000", "http://localhost:8000"];
  const MAX_SELECTION_CLAUSES = 40;

  async function fetchFromBackend(path, options) {
    let lastError = null;
    for (const base of API_BASE_CANDIDATES) {
      try {
        const response = await fetch(base + path, options);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
      } catch (err) {
        lastError = err;
      }
    }
    throw lastError || new Error("Unknown network error.");
  }

  function setPill(elId, online) {
    const el = document.getElementById(elId);
    el.classList.remove("cg-status-unknown", "cg-status-online", "cg-status-offline");
    if (online === null) {
      el.classList.add("cg-status-unknown");
      el.textContent = "Checking...";
    } else if (online) {
      el.classList.add("cg-status-online");
      el.textContent = "Online";
    } else {
      el.classList.add("cg-status-offline");
      el.textContent = "Offline";
    }
  }

  async function checkBackend() {
    setPill("cg-backend-status", null);
    setPill("cg-model-status", null);
    document.getElementById("cg-model-status").textContent = "Checking...";

    try {
      const health = await fetchFromBackend("/health", { method: "GET" });
      setPill("cg-backend-status", true);
      const modelPill = document.getElementById("cg-model-status");
      modelPill.classList.remove("cg-status-unknown", "cg-status-online", "cg-status-offline");
      if (health.model_loaded) {
        modelPill.classList.add("cg-status-online");
        modelPill.textContent = "Loaded";
      } else {
        modelPill.classList.add("cg-status-offline");
        modelPill.textContent = "Unavailable";
      }
    } catch (err) {
      setPill("cg-backend-status", false);
      const modelPill = document.getElementById("cg-model-status");
      modelPill.classList.remove("cg-status-unknown", "cg-status-online", "cg-status-offline");
      modelPill.classList.add("cg-status-offline");
      modelPill.textContent = "Unavailable";
    }
  }

  // Splits a free-form block of real-world Terms text into clause-sized
  // chunks so the local model can score them individually. This is only
  // used for the "Analyze Selected Text" reality-test feature; the
  // automatic .tc-clause scan on demo pages does not use this heuristic.
  function splitIntoClauses(rawText) {
    const byLine = rawText
      .split(/\r?\n+/)
      .map((line) => line.trim())
      .filter(Boolean);

    const clauses = [];
    for (const line of byLine) {
      if (line.length <= 400) {
        clauses.push(line);
        continue;
      }
      const sentences = line.match(/[^.!?]+[.!?]+(\s|$)/g) || [line];
      sentences.forEach((s) => {
        const trimmed = s.trim();
        if (trimmed) clauses.push(trimmed);
      });
    }

    return clauses
      .filter((c) => c.length > 0 && c.length <= 2000)
      .slice(0, MAX_SELECTION_CLAUSES);
  }

  async function analyzeSelection() {
    const resultsEl = document.getElementById("cg-selection-results");
    resultsEl.textContent = "Reading your current text selection...";

    let tabs;
    try {
      tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    } catch (err) {
      resultsEl.textContent = "Could not access the active tab.";
      return;
    }

    const tab = tabs[0];
    if (!tab || !tab.id) {
      resultsEl.textContent = "No active tab found.";
      return;
    }

    let injectionResult;
    try {
      [injectionResult] = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => window.getSelection().toString(),
      });
    } catch (err) {
      resultsEl.textContent =
        "ClauseGuard cannot read this page (e.g. a browser internal page).";
      return;
    }

    const selectedText = (injectionResult && injectionResult.result) || "";
    if (!selectedText.trim()) {
      resultsEl.textContent =
        "Select some Terms text on the page first, then click Analyze Selected Text.";
      return;
    }

    const clauses = splitIntoClauses(selectedText);
    if (clauses.length === 0) {
      resultsEl.textContent = "Your selection did not contain any usable text.";
      return;
    }

    resultsEl.textContent = `Analysing ${clauses.length} clause(s) locally...`;

    try {
      const data = await fetchFromBackend("/predict-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clauses }),
      });

      renderSelectionResults(data);
    } catch (err) {
      resultsEl.textContent =
        "ClauseGuard could not reach the local analysis service. Start FastAPI and try again.";
    }
  }

  function renderSelectionResults(data) {
    const resultsEl = document.getElementById("cg-selection-results");
    resultsEl.innerHTML = "";

    const summaryLine = document.createElement("div");
    summaryLine.className = "cg-selection-result-item";
    summaryLine.innerHTML = `<span class="cg-selection-result-label">Summary:</span> ${data.summary.attention_required} of ${data.summary.total_clauses} clause(s) flagged for attention.`;
    resultsEl.appendChild(summaryLine);

    data.results.forEach((result, index) => {
      const item = document.createElement("div");
      item.className = "cg-selection-result-item";
      item.innerHTML = `
        <div><span class="cg-selection-result-label">#${index + 1} ${result.friendly_label}</span> (${Math.round(result.confidence * 100)}% confidence)</div>
        <div>${result.text.length > 140 ? result.text.slice(0, 140) + "…" : result.text}</div>
      `;
      resultsEl.appendChild(item);
    });
  }

  async function loadCachedSitesList() {
    const el = document.getElementById("cg-cached-sites");
    try {
      const response = await fetchFromBackend("/realsite-cache", { method: "GET" });
      const names = Object.values(response.domains || {});
      el.textContent = names.length
        ? `Demo cache available for: ${names.join(", ")}.`
        : "No demo cache built yet.";
    } catch (err) {
      el.textContent = "";
    }
  }

  function normalizeDomain(hostname) {
    return (hostname || "").toLowerCase().replace(/^www\./, "");
  }

  async function getCurrentTab() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs[0] || null;
  }

  async function showCurrentDomain() {
    const el = document.getElementById("cg-current-domain");
    try {
      const tab = await getCurrentTab();
      const url = tab && tab.url ? new URL(tab.url) : null;
      if (url && (url.protocol === "http:" || url.protocol === "https:")) {
        el.textContent = `Current site: ${normalizeDomain(url.hostname)}`;
      } else {
        el.textContent = "Open a website to scan it.";
      }
    } catch (err) {
      el.textContent = "";
    }
  }

  async function scanCurrentSite() {
    const statusEl = document.getElementById("cg-scan-status");
    statusEl.textContent = "Checking for a cached copy of this site...";

    const tab = await getCurrentTab();
    if (!tab || !tab.url) {
      statusEl.textContent = "No active website tab found.";
      return;
    }

    let domain;
    try {
      const url = new URL(tab.url);
      if (url.protocol !== "http:" && url.protocol !== "https:") {
        statusEl.textContent = "This isn't a regular website page.";
        return;
      }
      domain = normalizeDomain(url.hostname);
    } catch (err) {
      statusEl.textContent = "Could not read the current page's address.";
      return;
    }

    try {
      await fetchFromBackend(`/realsite-cache/${encodeURIComponent(domain)}`, {
        method: "GET",
      });
    } catch (err) {
      statusEl.textContent = `No cached demo data for "${domain}" yet. Ask your teacher to add it with build_realsite_cache.py, or use "Analyze Selected Text" below.`;
      return;
    }

    statusEl.textContent = `Found a cached copy for ${domain}. Opening dashboard...`;
    const dashboardUrl = chrome.runtime.getURL(`dashboard.html?domain=${encodeURIComponent(domain)}`);
    chrome.tabs.create({ url: dashboardUrl });
  }

  document.getElementById("cg-check-backend").addEventListener("click", checkBackend);
  document.getElementById("cg-analyze-selection").addEventListener("click", analyzeSelection);
  document.getElementById("cg-scan-site").addEventListener("click", scanCurrentSite);

  checkBackend();
  loadCachedSitesList();
  showCurrentDomain();
})();
