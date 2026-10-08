'use client';

import { useEffect } from 'react';

export default function ErrorBoundary({ error, reset }) {
  useEffect(() => {
    // Log safe telemetry without leaking environment or secret variables
    console.error('Nexus Dashboard Runtime Error:', error?.message || 'Unknown error');
  }, [error]);

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
          maxWidth: '540px',
          width: '100%',
          background: 'var(--surface, #0c1017)',
          border: '1px solid var(--border-default, #233047)',
          borderRadius: '8px',
          padding: '32px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <span style={{ fontSize: '24px' }}>⚠️</span>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>Nexus Telemetry Error</h2>
        </div>
        <p style={{ margin: '0 0 20px 0', fontSize: '13px', color: 'var(--text-secondary, #94a3b8)', lineHeight: 1.6 }}>
          Terjadi kesalahan saat memuat antarmuka analitik pasar. Sistem pipeline backend tetap berjalan normal dan aman.
        </p>
        <div
          style={{
            background: 'var(--surface-well, #161e2c)',
            padding: '12px 14px',
            borderRadius: '6px',
            fontSize: '12px',
            fontFamily: "var(--font-mono, monospace)",
            color: 'var(--missed-text, #ff4d4f)',
            marginBottom: '24px',
            wordBreak: 'break-word',
          }}
        >
          {error?.message || 'An unexpected rendering error occurred'}
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => reset()}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 600,
              background: 'var(--accent-blue, #2563eb)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Coba Lagi (Retry)
          </button>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 500,
              background: 'transparent',
              color: 'var(--text-secondary, #94a3b8)',
              border: '1px solid var(--border-subtle, #182232)',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Muat Ulang Halaman
          </button>
        </div>
      </div>
    </div>
  );
}
