import Link from 'next/link';

export default function NotFound() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        background: 'var(--canvas, #06080d)',
        color: 'var(--text-primary, #f8fafc)',
        fontFamily: "var(--font-sans, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)",
      }}
    >
      <div
        style={{
          maxWidth: '480px',
          width: '100%',
          background: 'var(--surface, #0c1017)',
          border: '1px solid var(--border-default, #233047)',
          borderRadius: '8px',
          padding: '32px',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '32px', marginBottom: '12px' }}>🧭 404</div>
        <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '0 0 12px 0' }}>Halaman Tidak Ditemukan</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary, #94a3b8)', lineHeight: 1.5, margin: '0 0 24px 0' }}>
          Rute atau sumber daya intelijen pasar yang diminta tidak tersedia di portal Nexus.
        </p>
        <Link
          href="/"
          style={{
            display: 'inline-block',
            padding: '8px 18px',
            fontSize: '12px',
            fontWeight: 600,
            background: 'var(--accent-blue, #2563eb)',
            color: '#ffffff',
            textDecoration: 'none',
            borderRadius: '4px',
          }}
        >
          Kembali ke Dashboard Utama
        </Link>
      </div>
    </div>
  );
}
