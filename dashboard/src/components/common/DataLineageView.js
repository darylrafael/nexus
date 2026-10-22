"use client";

import React from "react";

export default function DataLineageView({ review }) {
  if (!review) {
    return (
      <div style={{ padding: "20px", color: "var(--text-secondary)", fontFamily: "var(--font-mono)", fontSize: "12px" }}>
        No session selected. Please select a trading session to view quantitative data lineage.
      </div>
    );
  }

  const dq = review.data_quality || {};
  const dqChecks = dq.checks || {};
  const rawFlowMatch = dq.flow_date_matched !== undefined ? dq.flow_date_matched : dqChecks.flow_date_matched;
  let flowValidity = "VALID";
  if (rawFlowMatch !== undefined) {
    if (typeof rawFlowMatch === "string") {
      flowValidity = (rawFlowMatch.includes("matched=") && !rawFlowMatch.includes("matched=none") && !rawFlowMatch.includes("matched=mismatch")) ? "VALID" : "INVALID";
    } else {
      flowValidity = rawFlowMatch ? "VALID" : "INVALID";
    }
  }

  const usdidrVal = review.actual_usdidr || review.macro?.usdidr_rate;
  const usdidrDisplay = (usdidrVal && Number.isFinite(Number(usdidrVal)) && Number(usdidrVal) > 0)
    ? `Rp ${Number(usdidrVal).toLocaleString("id-ID")}`
    : (usdidrVal && usdidrVal !== "Illustrative" ? String(usdidrVal) : "Not recorded");

  const flowVal = review.foreign_flow_actual;
  const flowDisplay = (flowVal && flowVal !== "Unknown" && flowVal !== "Not reviewed")
    ? flowVal
    : (flowVal || "Unrecorded / Missing");

  const comEntries = Object.entries(review.actual_commodities || {});
  const commodityDisplay = comEntries.length > 0
    ? comEntries.map(([k, v]) => `${v?.name || k}: ${v?.price ? '$' + Number(v.price).toLocaleString('en-US', { maximumFractionDigits: 2 }) : (v?.signal || 'Ref')}`).slice(0, 3).join(" · ")
    : "No commodity feeds logged for this session";

  const lineageItems = [
    {
      metric: "IHSG Index Close (^JKSE)",
      value: review.ihsg_actual ? `${review.ihsg_actual.toUpperCase()} (${review.ihsg_actual_pct > 0 ? "+" : ""}${Number(review.ihsg_actual_pct || 0).toFixed(2)}%)` : "Pending Close",
      source: "Yahoo Finance (^JKSE)",
      date: review.date,
      retrievalTime: "20:00 WIB",
      validityFlag: dq.ohlc_valid !== undefined ? (dq.ohlc_valid ? "VALID" : "INVALID") : (review.ihsg_actual ? "VALID" : "PENDING"),
      note: "Validated against strict OHLC checks: Close <= High, Close >= Low, distinct from previous candle.",
    },
    {
      metric: "USD/IDR Exchange Rate (USDIDR=X)",
      value: usdidrDisplay,
      source: "Yahoo Finance (USDIDR=X) & Bank Indonesia",
      date: review.date,
      retrievalTime: "20:00 WIB",
      validityFlag: dq.fx_consistent !== undefined ? (dq.fx_consistent ? "VALID" : "INVALID") : (usdidrVal ? "VALID" : "UNAVAILABLE"),
      note: "Cross-checked with stored consecutive levels; daily percent delta mathematically verified.",
    },
    {
      metric: "Foreign Net Flow (Regular Market)",
      value: flowDisplay,
      source: "IDX Regular Market News (Antara/Bisnis via Tavily Search)",
      date: review.date,
      retrievalTime: "20:00 WIB",
      validityFlag: flowValidity,
      note: typeof rawFlowMatch === "string"
        ? `Calendar verification (${rawFlowMatch}). Strict Indonesian D/M/Y calendar date matching.`
        : "Strict Indonesian D/M/Y calendar date matching. Scope restricted to Regular Market to avoid crossing/negotiated distortion.",
    },
    {
      metric: "Sector Breakdown (11 IDX-IC Indices)",
      value: review.sector_accuracy ? `${Object.keys(review.sector_accuracy).length} Sectors Scored` : "Pending Attribution",
      source: "IDX-IC Sector Indices via IDX Web Feeds",
      date: review.date,
      retrievalTime: "20:00 WIB",
      validityFlag: dq.sector_data_is_close !== undefined ? (dq.sector_data_is_close ? "VALID" : "INVALID") : "VALID",
      note: "Close data enforced. Midday and Sesi I snapshots detected and rejected.",
    },
    {
      metric: "Commodity Proxies (Energy, Metals, Ag)",
      value: commodityDisplay,
      source: "Yahoo Finance (BZ=F, GC=F) & Verified Cash Indices",
      date: review.date,
      retrievalTime: "06:55 WIB (Morning)",
      validityFlag: comEntries.length > 0 ? "VALID" : "UNAVAILABLE",
      note: "Liquid international futures & reference prices. Coal, CPO, and Nickel without structured APIs marked 'Price unavailable' (Rule B4).",
    },
  ];

  return (
    <div className="data-lineage-view" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div style={{ background: "var(--surface)", border: "1px solid var(--border-default)", padding: "16px", borderRadius: "var(--radius-sm)" }}>
        <div className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", marginBottom: "4px" }}>
          DATA PROVENANCE &amp; QUALITY ASSURANCE (PHASE B2)
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.45 }}>
          Session: <strong>{review.date}</strong> · Every evening evaluation records an explicit <code>data_quality</code> audit block. Sessions with failed data checks are automatically quarantined from historical scoring benchmarks and self-learning loops.
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {lineageItems.map((item, idx) => (
          <div
            key={idx}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              padding: "14px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "8px", marginBottom: "6px" }}>
              <div>
                <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>
                  {item.metric}
                </div>
                <div className="font-mono text-xs" style={{ color: "var(--accent-cyan)", marginTop: "2px" }}>
                  Source: {item.source}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span
                  className="font-mono text-xs font-bold"
                  style={{
                    padding: "3px 8px",
                    borderRadius: "4px",
                    background: item.validityFlag === "VALID" ? "var(--matched-bg)" : "var(--missed-bg)",
                    color: item.validityFlag === "VALID" ? "var(--matched-text)" : "var(--missed-text)",
                    border: `1px solid ${item.validityFlag === "VALID" ? "var(--matched-border)" : "var(--missed-border)"}`,
                  }}
                >
                  {item.validityFlag}
                </span>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "8px", margin: "8px 0", fontSize: "12px", fontFamily: "var(--font-mono)" }}>
              <div>Recorded Value: <strong style={{ color: "var(--text-primary)" }}>{item.value}</strong></div>
              <div>Snapshot Date: <strong>{item.date}</strong></div>
              <div>Retrieval Timestamp: <strong>{item.retrievalTime}</strong></div>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-tertiary)", borderTop: "1px solid var(--border-subtle)", paddingTop: "6px", marginTop: "6px" }}>
              {item.note}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
