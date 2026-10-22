'use client';

export function LegalDisclaimerBanner() {
  return (
    <div
      className="disclaimer-banner"
      style={{
        margin: "0 0 16px 0",
        padding: "10px 14px",
        borderRadius: "var(--radius-md)",
        background: "var(--warning-bg)",
        border: "1px solid var(--warning-border)",
        color: "var(--warning-body)",
        fontSize: "12px",
        lineHeight: 1.5,
        display: "flex",
        alignItems: "flex-start",
        gap: "8px",
      }}
    >
      <span style={{ fontSize: "14px", lineHeight: 1 }}>⚖️</span>
      <div>
        <strong style={{ fontWeight: 600, color: "var(--warning-text)" }}>REGULATORY &amp; DATA DISCLAIMER: </strong>
        Not investment advice. All intelligence is autonomously generated for research, architectural demonstration, and educational purposes. Data is research-tier aggregated from public web APIs without a direct licensed IDX exchange feed. Historical performance does not guarantee future results. Independent research (DYOR) is strictly required.
      </div>
    </div>
  );
}

export function LegalDisclaimerFooter() {
  return (
    <footer
      className="nexus-legal-footer"
      style={{
        marginTop: "20px",
        padding: "12px 16px",
        borderTop: "1px solid var(--border-subtle)",
        background: "var(--surface)",
        fontSize: "12px",
        color: "var(--text-tertiary)",
        lineHeight: 1.45,
      }}
    >
      <div style={{ maxWidth: "1280px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-mono)" }}>
            <span style={{ fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.04em" }}>NEXUS MARKET INTEL</span>
            <span>•</span>
            <span>AUTONOMOUS PIPELINE</span>
            <span>•</span>
            <span>TELEMETRY v2.1</span>
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>
            IDX: 06:55 WIB BRIEF / 20:00 WIB REVIEW
          </div>
        </div>
        <p style={{ margin: 0, fontSize: "12px", lineHeight: 1.45 }}>
          <strong>Legal Notice &amp; Disclaimer:</strong> All market intelligence, directional forecasts, and sector analyses are autonomously generated for quantitative research and educational evaluation. Nexus does not provide investment advice, brokerage, or asset management services. Market data is research-tier from public APIs without a direct licensed IDX feed. Past hit rates do not guarantee future returns. Independent verification (DYOR) required.
        </p>
      </div>
    </footer>
  );
}
