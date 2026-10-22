"use client";

import React from "react";

export default function MethodologyView({ onClose, historyRescoredAt = "2026-10-14" }) {
  return (
    <div className="methodology-container" style={{ padding: "16px 20px 40px", color: "var(--text-primary)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, borderBottom: "1px solid var(--border-subtle)", paddingBottom: 12 }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0, letterSpacing: "-0.01em" }}>System Methodology & Audit Guide</h2>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Transparent documentation for outside investors, researchers, and recruiters</span>
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
          1. What Nexus Predicts
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          Every weekday morning at <strong>06:55 WIB</strong>, the automated pipeline produces a structured pre-market forecast for the Indonesian Stock Exchange (IHSG / ^JKSE):
        </p>
        <ul style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", paddingLeft: 20, margin: 0 }}>
          <li><strong>IHSG Direction:</strong> Projected market bias (Bullish, Bearish, or Neutral) based on global commodities, currency, and macro catalysts.</li>
          <li><strong>Foreign Flow:</strong> Institutional net foreign flow direction: Accumulation (&gt; +Rp1T), Distribution (&lt; -Rp1T), or Stagnant (&plusmn; Rp1T threshold).</li>
          <li><strong>Sectoral Outlook:</strong> Thematic calls mapped to the 11 official IDX-IC parent sectors.</li>
          <li><strong>Dynamic Volatility Bands:</strong> Reference support (S1) and resistance (R1) levels derived from 14-day Average True Range (ATR) or previous-day range. These are mathematical reference boundaries, not trading recommendations.</li>
        </ul>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          2. Scoring Engine (The 50/30/20 Dynamic Scorable Blend)
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          At <strong>20:00 WIB</strong>, the evening review evaluates morning projections against authoritative market close data using an explicit scorable blend:
        </p>
        <div style={{ background: "var(--surface-subtle)", border: "1px solid var(--border-subtle)", borderRadius: 6, padding: "12px 16px", marginBottom: 12, fontSize: 13 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "grid", gridTemplateColumns: "100px 1fr", gap: 12, alignItems: "baseline" }}>
              <span style={{ fontWeight: 700, color: "var(--accent-cyan)" }}>50% Weight:</span>
              <span><strong>Index Direction:</strong> Evaluated strictly against official close-to-close percentage change (&plusmn;0.2% Neutral band).</span>
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
          * Dynamic normalization: Weights automatically rescale over scorable components only. If a component lacks verifiable data, it is recorded as null rather than penalized as a failure.
        </p>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          3. Statistical Baselines &amp; Confidence Calibration
        </h3>
        <p style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", marginBottom: 8 }}>
          Raw win rate alone is meaningless without rigorous benchmarking. Nexus measures hit rates against three persistent baselines:
        </p>
        <ul style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-secondary)", paddingLeft: 20, marginBottom: 8 }}>
          <li><strong>Always-Bearish / Always-Bullish:</strong> The hit rate achieved by simply predicting the prevailing trend every day.</li>
          <li><strong>Persistence Baseline:</strong> Predicting that today will repeat yesterday&apos;s actual direction.</li>
          <li><strong>Wilson 95% Confidence Interval:</strong> Calculates the true underlying binomial hit rate range given the small sample size.</li>
          <li><strong>Brier Score:</strong> Measures probability calibration (0.00 is perfect, 0.25 is random coin-flip).</li>
          <li><strong>Calibrated Confidence (Empirical Shrinkage):</strong> Uncalibrated LLM stated confidence (<code>C_stated</code>, averaging ~80.5%) is shrunk toward the empirical hit rate (<code>k / n</code>) using a conservative prior cap (<code>P_cap = 55.0%</code>) and prior strength (<code>N0 = 30</code>), with weight <code>w = min(n / 30, 1.0)</code>:
            <br />
            <code>Calibrated% = round(w &times; (100 &times; k / n) + (1 - w) &times; min(C_stated, 55.0), 1)</code>
            <br />
            For current audit dataset <code>k=9, n=20</code> (<code>w = 0.67</code>) and <code>C_stated &ge; 55%</code>, headline calibrated confidence equals <strong>48.3%</strong> (labeled <em>illustrative shrinkage estimate</em> while <code>n &lt; 30</code>).
          </li>
        </ul>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 700, color: "var(--accent-cyan)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          4. Known Limitations &amp; Buy-Side Caveats
        </h3>
        <div style={{ background: "var(--surface-well)", borderLeft: "3px solid var(--warning-border)", padding: "10px 14px", borderRadius: "0 6px 6px 0", fontSize: 12, lineHeight: 1.6, color: "var(--text-secondary)" }}>
          <p style={{ margin: "0 0 6px 0" }}>
            <strong>Sample Size:</strong> With $n &lt; 30$ historical sessions, statistical power is insufficient to conclude that accuracy differs from random variation.
          </p>
          <p style={{ margin: "0 0 6px 0" }}>
            <strong>Pre-Open Lock Provenance:</strong> All 20 historical sessions in this audit dataset (2026-09-22 to 2026-10-19) were hashed retroactively during post-hoc audit and are explicitly marked <code>lock_status = &quot;retroactive&quot;</code> (<em>Hash added retroactively; not proof of pre-open lock</em>). Only live automated runs executed at 06:55 WIB carry verified pre-open locks.
          </p>
          <p style={{ margin: "0 0 6px 0" }}>
            <strong>Synthetic Index Payoff:</strong> Basis points (bps) capture is a theoretical index tracking calculation before brokerage commissions, borrowing costs, and execution slippage. Indonesian retail investors cannot directly short the IHSG cash index.
          </p>
          <p style={{ margin: 0 }}>
            <strong>Research Data Tier:</strong> Market feeds are aggregated from public web APIs (Yahoo Finance, Tavily) without a direct licensed exchange data feed.
          </p>
        </div>
      </section>

      <section style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, color: "var(--text-tertiary)" }}>
          <span>Authoritative historical audit rescored on: <strong>{historyRescoredAt}</strong></span>
          <span>Version: Nexus 2.5 Architecture</span>
        </div>
      </section>
    </div>
  );
}
