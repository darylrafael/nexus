"use client";

import React from "react";

export default function PipelineStatusView({ status, pipelineHealth, telemetry, latestDate }) {
  const isStale = Boolean(pipelineHealth?.isStale);
  const tradingDaysStale = pipelineHealth?.tradingDaysSinceLatest || 0;

  return (
    <div className="pipeline-status-view" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Current Operational State Banner */}
      <div
        style={{
          padding: "16px",
          borderRadius: "var(--radius-sm)",
          background: isStale ? "var(--warning-bg)" : "var(--matched-bg)",
          border: `1px solid ${isStale ? "var(--warning-border)" : "var(--matched-border)"}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "18px" }}>{isStale ? "⚠️" : "🟢"}</span>
            <span
              className="font-mono text-sm font-bold"
              style={{ color: isStale ? "var(--warning-text)" : "var(--matched-text)" }}
            >
              {isStale ? `FEED PAUSED (${tradingDaysStale} TRADING DAYS)` : "PIPELINE AUTOMATION HEALTHY"}
            </span>
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
            {isStale
              ? `Market feed was paused following the ${latestDate || "8 Oct"} session. GitHub Actions scheduled workflows run automatically at 06:55 and 20:00 WIB.`
              : "All scheduled autonomous agents are actively tracking the Indonesian Stock Exchange (IHSG)."}
          </div>
        </div>
        <div className="font-mono text-xs" style={{ background: "var(--surface)", padding: "6px 12px", borderRadius: "4px", border: "1px solid var(--border-default)" }}>
          {status?.label || "IDX STATUS"}
        </div>
      </div>

      {/* Cadence Timetable */}
      <div>
        <div className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", marginBottom: "8px", letterSpacing: "0.05em" }}>
          SCHEDULED RUN TIMETABLE (WIB / ASIA/JAKARTA)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px" }}>
          <div style={{ background: "var(--surface)", border: "1px solid var(--border-default)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
            <div className="font-mono text-xs text-muted">MORNING INTELLIGENCE BRIEF</div>
            <div className="font-mono text-base font-bold" style={{ margin: "4px 0", color: "var(--text-primary)" }}>
              06:55 WIB
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
              Autonomous macro sentiment, commodity proxy mapping, sector impact inference, and cryptographic prediction lock before the 09:00 opening bell.
            </div>
          </div>

          <div style={{ background: "var(--surface)", border: "1px solid var(--border-default)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
            <div className="font-mono text-xs text-muted">IDX MARKET CLOSE &amp; SETTLE</div>
            <div className="font-mono text-base font-bold" style={{ margin: "4px 0", color: "var(--text-primary)" }}>
              16:00 WIB
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
              Official closing auction concludes. Post-market exchange data finalized across Yahoo Finance and IDX-IC sector feeds.
            </div>
          </div>

          <div style={{ background: "var(--surface)", border: "1px solid var(--border-default)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
            <div className="font-mono text-xs text-muted">EVENING EVALUATION &amp; RCA</div>
            <div className="font-mono text-base font-bold" style={{ margin: "4px 0", color: "var(--text-primary)" }}>
              20:00 WIB
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
              Automated scoring against actuals, directional attribution, root cause analysis (RCA), and lesson extraction for prompt feedback.
            </div>
          </div>
        </div>
      </div>

      {/* Holiday Awareness & Next Event */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border-default)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
        <div className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", marginBottom: "6px" }}>
          CALENDAR &amp; HOLIDAY HANDLING
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-primary)", marginBottom: "8px" }}>
          Next Scheduled Event: <strong>{status?.nextEvent || "06:55 WIB Morning Brief"}</strong>
        </div>
        <div style={{ fontSize: "11px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
          The autonomous scheduler cross-references official Indonesian Stock Exchange (IDX) statutory holidays from <code>data/idx_holidays.json</code>. Pipeline runs never trigger on weekends or verified exchange holidays.
        </div>
      </div>

      {/* Provenance Guard & Test Data Quarantine (Phase 2.3) */}
      <div
        style={{
          background: pipelineHealth?.mockDataDetected ? "var(--missed-bg)" : "var(--surface)",
          border: `1px solid ${pipelineHealth?.mockDataDetected ? "var(--missed-border)" : "var(--border-default)"}`,
          padding: "14px",
          borderRadius: "var(--radius-sm)",
        }}
      >
        <div
          className="font-mono text-xs font-bold"
          style={{
            color: pipelineHealth?.mockDataDetected ? "var(--missed-text)" : "var(--accent-cyan)",
            marginBottom: "6px",
          }}
        >
          PROVENANCE GUARD &amp; MOCK DATA QUARANTINE
        </div>
        {pipelineHealth?.mockDataDetected && Array.isArray(pipelineHealth?.detectedMockRuns) && pipelineHealth.detectedMockRuns.length > 0 ? (
          <div>
            <div style={{ fontSize: "12px", color: "var(--missed-text)", fontWeight: 600, marginBottom: "8px" }}>
              🚨 Test data detected and excluded from scoring ({pipelineHealth.detectedMockRuns.length} run directory/directories):
            </div>
            <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "12px", color: "var(--text-primary)" }}>
              {pipelineHealth.detectedMockRuns.map((item) => (
                <li key={item.date} className="font-mono" style={{ marginBottom: "4px" }}>
                  <strong>{item.date}</strong> — {Array.isArray(item.reasons) ? item.reasons.join("; ") : "mock provenance"}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.45 }}>
            🟢 All active run directories passed provenance verification (0 <code>mock_*</code> or synthetic sources detected).
          </div>
        )}
      </div>

      {/* Non-Silent Error Taxonomy Telemetry (Phase A6) */}
      <div style={{ background: "var(--surface)", border: "1px solid var(--border-default)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
        <div className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", marginBottom: "6px" }}>
          ERROR TAXONOMY &amp; TELEMETRY (PHASE A6)
        </div>
        <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.45 }}>
          Nexus enforces explicit error logging across all pipeline modules. Broad exception swallowing is prohibited; failed data collection steps (foreign flow, FX, commodities, sectors) record structured payloads with error type and message:
        </div>
        <pre className="font-mono text-xs" style={{ background: "var(--surface-well)", padding: "10px", borderRadius: "4px", marginTop: "8px", overflowX: "auto" }}>
{`{
  "status": "error",
  "error_type": "DataFetchException",
  "message": "Vendor timeout / format mismatch",
  "data_quality": { "ohlc_valid": false }
}`}
        </pre>
        <div style={{ fontSize: "11px", color: "var(--text-tertiary)", marginTop: "6px" }}>
          Dashboard UI surfaces data errors explicitly rather than defaulting to 0 or &quot;Unknown&quot;.
        </div>
      </div>
    </div>
  );
}
