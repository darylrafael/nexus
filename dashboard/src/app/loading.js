export default function Loading() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '16px',
        background: 'var(--canvas, #06080d)',
        color: 'var(--text-secondary, #94a3b8)',
        fontFamily: "var(--font-mono, monospace)",
        fontSize: '13px',
      }}
    >
      <div
        style={{
          width: '36px',
          height: '36px',
          border: '2px solid var(--border-subtle, #182232)',
          borderTopColor: 'var(--accent-cyan, #0891b2)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <div style={{ letterSpacing: '0.05em' }}>
        MEMUAT TELEMETRI PASAR NEXUS...
      </div>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
