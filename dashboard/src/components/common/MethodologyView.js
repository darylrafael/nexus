"use client";

import React from "react";

export default function MethodologyView({ onClose, historyRescoredAt, nexusStats }) {
  const k = nexusStats?.direction_correct_count ?? 9;
  const n = nexusStats?.direction_scorable_sessions ?? 24;
  const w = Math.min(n / 30, 1.0).toFixed(2);
  const avgStated = nexusStats?.calibration?.average_stated_confidence_pct ?? 79.8;
  const calConf = nexusStats?.calibration?.calibrated_confidence_pct ?? 41.0;
  const validLessonsCount = nexusStats?.all_lessons?.length ?? 38;
  const quarantinedCount = nexusStats?.rejected_lessons?.length ?? 19;
  const rescoredDate = historyRescoredAt || nexusStats?.history_rescored_at || "2026-10-23";

  return (
    <div className="methodology-container" style={{ padding: "16px 20px 40px", color: "var(--text-primary)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, borderBottom: "1px solid var(--border-subtle)", paddingBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>System Methodology &amp; Audit Guide</h2>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Plain-language &amp; quantitative documentation for beginners, researchers, and institutional reviewers</span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: "var(--surface-well)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "6px 12px",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              color: "var(--text-primary)",
              minHeight: 44,
              minWidth: 44
            }}
          >
            Close
          </button>
        )}
      </div>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          1. What Nexus Predicts (06:55 WIB Pre-Market)
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          Every weekday morning at <strong>06:55 WIB</strong> (before the 09:00 WIB IDX opening bell), the automated pipeline synthesizes overnight global macro, commodities, and USD/IDR movements into a cryptographically locked forecast for the Indonesian Stock Exchange (IHSG / ^JKSE):
        </p>
        <ul style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", paddingLeft: 20, margin: 0 }}>
          <li><strong>IHSG Direction:</strong> Projected market bias (Bullish &gt; +0.20%, Bearish &lt; -0.20%, or Neutral &plusmn;0.20%) based on global commodities, currency, and domestic macro catalysts.</li>
          <li><strong>Foreign Flow:</strong> Institutional net foreign flow direction in Pasar Reguler: Accumulation (&gt; +Rp1T), Distribution (&lt; -Rp1T), or Stagnant (&plusmn;Rp1T threshold).</li>
          <li><strong>Sectoral Outlook:</strong> Deterministic commodity-to-sector impact calls mapped to the 11 official IDX-IC parent sectors.</li>
          <li><strong>Key Risk Factor:</strong> The single highest-probability macro or currency catalyst that could invalidate the morning thesis.</li>
        </ul>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          2. Objective Scoring Engine (The 50/30/20 Dynamic Scorable Blend)
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          At <strong>20:00 WIB</strong>, after official IDX market settlement, the evening reviewer grades the morning prediction against actual market closes using a deterministic 3-pillar blend:
        </p>
        <div style={{ background: "var(--surface-subtle)", border: "1px solid var(--border-subtle)", borderRadius: 6, padding: "12px 16px", marginBottom: 12, fontSize: 13 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", gap: 12, alignItems: "baseline" }}>
              <span style={{ fontWeight: 700, color: "var(--accent-cyan)" }}>50% Weight:</span>
              <span><strong>Index Direction:</strong> Evaluated strictly against official close-to-close percentage change (&plusmn;0.20% Neutral band).</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", gap: 12, alignItems: "baseline" }}>
              <span style={{ fontWeight: 700, color: "var(--accent-cyan)" }}>30% Weight:</span>
              <span><strong>Sector Accuracy:</strong> Deterministic rule-based scoring of predicted sectors against 11 IDX-IC closing returns. Subsectors with conflicting calls on the same parent index are marked <em>unverifiable</em> and excluded from scoring.</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", gap: 12, alignItems: "baseline" }}>
              <span style={{ fontWeight: 700, color: "var(--accent-cyan)" }}>20% Weight:</span>
              <span><strong>Foreign Flow:</strong> Strict Indonesian D/M/Y date-verified net flow. If no same-day verified data exists, the metric is marked <em>Unknown</em> and dynamically excluded from the denominator.</span>
            </div>
          </div>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", fontStyle: "italic", margin: 0 }}>
          * Dynamic normalization: Weights automatically rescale over scorable components only. If a component lacks verifiable data, it is recorded as null rather than penalized or fabricated.
        </p>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          3. Self-Learning Loop &amp; 5-Stage Hygiene Quarantine
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          When a prediction diverges from market close, the Root Cause Analysis (RCA) engine diagnoses the missed variables and formulates a structured causal rule (<code>Ketika [kondisi], tetapi [divergensi], maka [aturan kausal]</code>). Before any lesson can enter memory, it must pass <strong>5 deterministic quality gates</strong>:
        </p>
        <ul style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", paddingLeft: 20, margin: 0 }}>
          <li><strong>Gate 1 (Provenance Guard):</strong> Rejects any session with mock or synthetic data sources.</li>
          <li><strong>Gate 2 (Data Quality Gate):</strong> Rejects lessons from sessions with invalid OHLC geometry or inconsistent USD/IDR spot closes.</li>
          <li><strong>Gate 3 (Sign &amp; Numeric Consistency):</strong> Rejects lessons where LLM prose contradicts the actual +/- sign or percentage move of IHSG or FX.</li>
          <li><strong>Gate 4 (Anti-Boilerplate Filter):</strong> Rejects generic advice (e.g., &ldquo;tighten stop-loss&rdquo;) that lacks a specific macro trigger and causal mechanism.</li>
          <li><strong>Gate 5 (Deduplication &amp; Cap):</strong> Caps extraction at 2 unique rules per session. Currently <strong>{validLessonsCount} valid rules</strong> are stored and <strong>{quarantinedCount} faulty rules</strong> are quarantined.</li>
        </ul>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          4. Statistical Baselines &amp; Confidence Calibration
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          Raw win rate alone is meaningless without rigorous benchmarking. Nexus measures hit rates against three persistent baselines:
        </p>
        <ul style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", paddingLeft: 20, marginBottom: 8 }}>
          <li><strong>Always-Bearish / Always-Bullish:</strong> The hit rate achieved by simply predicting the prevailing trend every day.</li>
          <li><strong>Persistence Baseline:</strong> Predicting that today will repeat yesterday&apos;s actual direction.</li>
          <li><strong>Wilson 95% Confidence Interval:</strong> Calculates the true underlying binomial hit rate range given the sample size (<code>n = {n}</code>).</li>
          <li><strong>Brier Score:</strong> Measures probability calibration (0.00 is perfect, 0.25 is random coin-flip, &gt;0.25 indicates overconfidence).</li>
          <li><strong>Calibrated Confidence (Empirical Shrinkage):</strong> Uncalibrated LLM stated confidence (<code>C_stated</code>, averaging ~{avgStated}%) is shrunk toward the empirical hit rate (<code>k / n</code>) using a conservative prior cap (<code>P_cap = 55.0%</code>) and prior strength (<code>N0 = 30</code>), with weight <code>w = min(n / 30, 1.0)</code>:
            <br />
            <code>Calibrated% = round(w &times; (100 &times; k / n) + (1 - w) &times; min(C_stated, 55.0), 1)</code>
            <br />
            For the current dataset <code>k={k}, n={n}</code> (<code>w = {w}</code>) and <code>C_stated &ge; 55%</code>, headline calibrated confidence equals <strong>{calConf}%</strong> (labeled <em>illustrative shrinkage estimate</em> while <code>n &lt; 30</code>).
          </li>
        </ul>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          5. Known Limitations &amp; Buy-Side Caveats
        </h3>
        <div style={{ background: "var(--surface-well)", borderLeft: "3px solid var(--warning-border)", padding: "10px 14px", borderRadius: "0 6px 6px 0", fontSize: 12, lineHeight: 1.6, color: "var(--text-secondary)" }}>
          <p style={{ margin: "0 0 6px 0" }}>
            <strong>Sample Size:</strong> With <code>n = {n} &lt; 30</code> evaluated sessions, statistical power is not yet sufficient to conclude permanent directional alpha over naive baselines.
          </p>
          <p style={{ margin: "0 0 6px 0" }}>
            <strong>Pre-Open Lock Provenance:</strong> Backfilled sessions from 2026-09-22 to 2026-10-19 were hashed retroactively during audit and are explicitly marked <code>lock_status = &quot;retroactive&quot;</code>. Live automated runs executed at 06:55 WIB prior to the 09:00 WIB IDX opening bell carry verified cryptographic pre-open locks (<code>lock_status = &quot;locked_pre_open&quot;</code>).
          </p>
          <p style={{ margin: "0 0 6px 0" }}>
            <strong>Synthetic Index Payoff:</strong> Basis points (bps, where <code>100 bps = 1.00%</code>) capture is a theoretical index tracking calculation before brokerage commissions, borrowing costs, and execution slippage. Indonesian retail investors cannot directly short the IHSG cash index.
          </p>
          <p style={{ margin: 0 }}>
            <strong>Research Data Tier:</strong> Market feeds are aggregated from public web APIs (Yahoo Finance, Tavily) without a direct licensed IDX exchange data feed.
          </p>
        </div>
      </section>

      <section style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, color: "var(--text-tertiary)" }}>
          <span>Authoritative historical corpus rescored through: <strong>{rescoredDate}</strong></span>
          <span>Version: Nexus v2.5 Closed-Loop Architecture</span>
        </div>
      </section>
    </div>
  );
}
