/* ClauseGuard - dashboard logic.

Loads this site's pre-built clause cache from the local backend, classifies
it LIVE via /predict-batch (proving the analysis is real, not pre-baked),
and renders a simple, plain-language grade plus a category breakdown loosely
mapped to themes in India's Digital Personal Data Protection Act, 2023 -
for awareness only, not a legal compliance assessment.
*/
(function () {
  "use strict";

  const API_BASE_CANDIDATES = ["http://127.0.0.1:8000", "http://localhost:8000"];

  const DPDP_CATEGORY_META = {
    safe: {
      title: "✅ No Concerns Flagged",
      dpdp: "No prototype attention category detected.",
      color: "#1b8a5a",
    },
    privacy_attention: {
      title: "🔐 Personal Data &amp; Consent",
      dpdp: "Loosely related to DPDP Act, 2023 themes: Consent, Purpose Limitation, Data Minimisation.",
      color: "#b05a00",
    },
    payment_attention: {
      title: "💳 Charges, Renewals &amp; Refunds",
      dpdp: "Consumer billing terms - renewal, refund and fee conditions.",
      color: "#b91c1c",
    },
    user_rights_attention: {
      title: "⚖️ Your Rights &amp; Dispute Resolution",
      dpdp: "Loosely related to DPDP Act, 2023 themes: Grievance Redressal, Data Principal Rights.",
      color: "#6d28d9",
    },
  };

  function getQueryDomain() {
    const params = new URLSearchParams(window.location.search);
    return (params.get("domain") || "").toLowerCase().trim();
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

  function renderError(message) {
    document.getElementById("cg-dash-content").innerHTML = `
      <p class="cg-dash-error">${message}</p>
    `;
  }

  const GRADE_BANDS = [
    {
      min: 0,
      max: 25,
      letter: "A",
      cls: "cg-grade-a",
      label: "Mostly user-friendly terms",
      explanation: "Under 1 in 4 clauses were flagged. Most of what's here reads as fairly standard.",
    },
    {
      min: 25,
      max: 50,
      letter: "B",
      cls: "cg-grade-b",
      label: "Some clauses need your review",
      explanation: "Roughly 1 in 4 to 1 in 2 clauses were flagged. Worth skimming the highlighted sections.",
    },
    {
      min: 50,
      max: 75,
      letter: "C",
      cls: "cg-grade-c",
      label: "Several clauses need attention",
      explanation: "More than half the clauses were flagged. It's worth reading the flagged sections before agreeing.",
    },
    {
      min: 75,
      max: 101,
      letter: "D",
      cls: "cg-grade-d",
      label: "Many clauses need careful review",
      explanation: "3 in 4 or more clauses were flagged across privacy, payment, or rights categories. Read carefully before accepting - this doesn't mean the site is unsafe, just that there's a lot here worth your attention.",
    },
  ];

  function gradeFor(attentionPct) {
    return GRADE_BANDS.find((b) => attentionPct >= b.min && attentionPct < b.max) || GRADE_BANDS[GRADE_BANDS.length - 1];
  }

  function renderGradeLegend(currentLetter) {
    return `
      <div class="cg-grade-legend">
        <h4>What the grades mean</h4>
        ${GRADE_BANDS
          .map(
            (b) => `
          <div class="cg-grade-legend-row ${b.letter === currentLetter ? "cg-grade-legend-current" : ""}">
            <span class="cg-grade-legend-badge ${b.cls}">${b.letter}</span>
            <span class="cg-grade-legend-range">${b.min}-${b.max > 100 ? 100 : b.max}% flagged</span>
            <span class="cg-grade-legend-text">${b.label}</span>
          </div>
        `
          )
          .join("")}
      </div>
    `;
  }

  function categoryCard(key, count, total) {
    const meta = DPDP_CATEGORY_META[key];
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    return `
      <div class="cg-category-card">
        <h3>${meta.title}</h3>
        <div class="cg-category-count" style="color:${meta.color};">${count}</div>
        <div>${pct}% of clauses</div>
        <div class="cg-category-dpdp">${meta.dpdp}</div>
      </div>
    `;
  }

  function evidenceList(results) {
    const flagged = results.filter((r) => r.is_attention_required);
    if (flagged.length === 0) {
      return "<p>No flagged clauses - nothing to show as evidence.</p>";
    }
    return flagged
      .map(
        (r) => `
        <div class="cg-evidence-item">
          <span class="cg-evidence-badge">${r.friendly_label}</span>
          ${Math.round(r.confidence * 100)}% confidence<br />
          ${r.text.length > 220 ? r.text.slice(0, 220) + "…" : r.text}
        </div>
      `
      )
      .join("");
  }

  async function run() {
    const domain = getQueryDomain();
    if (!domain) {
      renderError("No site was specified. Open this dashboard from the ClauseGuard popup's Scan button.");
      return;
    }

    let cacheResponse;
    try {
      cacheResponse = await fetchFromBackend(`/realsite-cache/${encodeURIComponent(domain)}`, {
        method: "GET",
      });
    } catch (err) {
      renderError(
        `No cached demo data for "${domain}". Ask your teacher to add it with backend/scripts/build_realsite_cache.py.`
      );
      return;
    }

    const pages = cacheResponse.pages || {};
    const clauses = [];
    const sourceLinks = [];
    for (const [pageType, page] of Object.entries(pages)) {
      clauses.push(...(page.clauses || []));
      sourceLinks.push(`${pageType}: <a href="${page.source_url}" target="_blank" rel="noopener">${page.source_url}</a>`);
    }

    if (clauses.length === 0) {
      renderError(`The cached copy for "${domain}" has no usable clause text.`);
      return;
    }

    const startTime = performance.now();
    let predictResponse;
    try {
      predictResponse = await fetchFromBackend("/predict-batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ clauses: clauses.slice(0, 100) }),
      });
    } catch (err) {
      renderError(
        "ClauseGuard could not reach the local analysis service. Start FastAPI and reload this page."
      );
      return;
    }
    const elapsedSeconds = ((performance.now() - startTime) / 1000).toFixed(2);

    const summary = predictResponse.summary;
    const attentionPct = summary.total_clauses > 0
      ? Math.round((summary.attention_required / summary.total_clauses) * 100)
      : 0;
    const grade = gradeFor(attentionPct);

    let modelInfo = null;
    try {
      modelInfo = await fetchFromBackend("/model-info", { method: "GET" });
    } catch (err) {
      modelInfo = null;
    }

    const content = document.getElementById("cg-dash-content");
    content.innerHTML = `
      <h2 class="cg-site-title">${cacheResponse.site_name}</h2>
      <p class="cg-site-domain">${domain} &middot; cached copy built ${new Date(cacheResponse.fetched_at).toLocaleDateString()}</p>

      <div class="cg-grade-card">
        <div class="cg-grade-badge ${grade.cls}">${grade.letter}</div>
        <div>
          <div class="cg-grade-label">${grade.label}</div>
          <p class="cg-grade-summary">
            ${summary.attention_required} of ${summary.total_clauses} clauses analysed may need your
            attention (${attentionPct}%). In plain language: ${grade.explanation}
          </p>
          <div class="cg-score-track">
            <div class="cg-score-fill" style="width:${attentionPct}%; background:${grade.cls === "cg-grade-a" ? "#1b8a5a" : grade.cls === "cg-grade-b" ? "#0a7ea4" : grade.cls === "cg-grade-c" ? "#b05a00" : "#b91c1c"};"></div>
          </div>
        </div>
      </div>

      ${renderGradeLegend(grade.letter)}

      <div class="cg-category-grid">
        ${categoryCard("safe", summary.safe, summary.total_clauses)}
        ${categoryCard("privacy_attention", summary.privacy_attention, summary.total_clauses)}
        ${categoryCard("payment_attention", summary.payment_attention, summary.total_clauses)}
        ${categoryCard("user_rights_attention", summary.user_rights_attention, summary.total_clauses)}
      </div>

      <div class="cg-meta-card">
        Analysed <strong>${summary.total_clauses}</strong> real clauses from ${domain} in
        <strong>${elapsedSeconds} seconds</strong>, live, just now${modelInfo ? ` using a model with
        <strong>${Math.round(modelInfo.test_accuracy * 100)}%</strong> measured test accuracy
        (trained ${new Date(modelInfo.training_timestamp).toLocaleDateString()})` : ""}.
        This proves the classification ran in real time on this page load, not a pre-baked result.
        <br />Sources: ${sourceLinks.join(" &middot; ")}
      </div>

      <details class="cg-evidence">
        <summary>Show flagged clauses (evidence)</summary>
        ${evidenceList(predictResponse.results)}
      </details>
    `;
  }

  run();
})();
