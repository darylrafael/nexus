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
        fontSize: "11px",
        lineHeight: 1.5,
        display: "flex",
        alignItems: "flex-start",
        gap: "8px",
      }}
    >
      <span style={{ fontSize: "14px", lineHeight: 1 }}>⚖️</span>
      <div>
        <strong style={{ fontWeight: 600, color: "var(--warning-text)" }}>REGULATORY DISCLAIMER: </strong>
        Riset &amp; intelijen pasar ini dihasilkan secara otonom oleh model AI untuk tujuan informasi dan edukasi. Bukan merupakan rekomendasi investasi, anjuran transaksi, atau penawaran efek (UU No. 8/1995 &amp; POJK). Analisis mandiri (DYOR) selalu diwajibkan sebelum mengambil keputusan investasi.
      </div>
    </div>
  );
}

export function LegalDisclaimerFooter() {
  return (
    <footer
      className="nexus-legal-footer"
      style={{
        marginTop: "48px",
        padding: "24px 20px",
        borderTop: "1px solid var(--border-subtle)",
        background: "var(--surface)",
        fontSize: "11px",
        color: "var(--text-tertiary)",
        lineHeight: 1.6,
      }}
    >
      <div style={{ maxWidth: "1280px", margin: "0 auto", display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontFamily: "var(--font-mono)" }}>
            <span style={{ fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.05em" }}>NEXUS MARKET INTELLIGENCE</span>
            <span>•</span>
            <span>AUTONOMOUS PIPELINE</span>
            <span>•</span>
            <span>TELEMETRY v2.0</span>
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "10px" }}>
            IDX SESSION: 06:55 WIB BRIEF / 20:00 WIB REVIEW
          </div>
        </div>
        <p style={{ margin: 0, textAlign: "justify" }}>
          <strong>Pemberitahuan Hukum &amp; Penafian Tanggung Jawab:</strong> Seluruh materi analisis, proyeksi arah, estimasi aliran dana, dan ringkasan sektor yang disajikan dalam dashboard ini diproduksi oleh pipeline AI multi-agen secara independen dan murni ditujukan sebagai alat bantu riset kuantitatif dan edukasi. Nexus tidak beroperasi sebagai perusahaan efek, perantara pedagang efek, atau penasihat investasi berizin OJK. Kinerja prediksi historis bukan merupakan jaminan kinerja di masa depan. Seluruh risiko investasi dan keputusan finansial berada sepenuhnya di tangan masing-masing pelaku pasar.
        </p>
      </div>
    </footer>
  );
}
