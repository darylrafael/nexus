'use client';

export function StatusBadge({ correct, isPending, size = 'md', isLive = false }) {
  if (isPending || correct === null || correct === undefined) {
    return (
      <span className={`status-pill ${isLive ? 'status-pending' : 'status-unreviewed'} ${size === 'sm' ? 'status-sm' : ''}`}>
        <span className="status-indicator-dot" />
        <span className="status-text font-mono">{isLive ? 'LIVE' : 'NOT REVIEWED'}</span>
      </span>
    );
  }
  return (
    <span className={`status-pill ${correct ? 'status-matched' : 'status-missed'} ${size === 'sm' ? 'status-sm' : ''}`}>
      <span className="status-indicator-dot" />
      <span className="status-text font-mono">{correct ? 'MATCHED' : 'MISSED'}</span>
    </span>
  );
}

export function DirectionBadge({ direction }) {
  const dir = (direction || '').toLowerCase();
  let badgeClass = 'dir-neutral';
  let arrow = '—';
  if (dir.includes('pending')) {
    badgeClass = 'dir-pending';
    arrow = '⏳';
  } else if (dir.includes('bullish') || dir.includes('up')) {
    badgeClass = 'dir-bullish';
    arrow = '▲';
  } else if (dir.includes('bearish') || dir.includes('down')) {
    badgeClass = 'dir-bearish';
    arrow = '▼';
  }
  return (
    <span className={`dir-badge font-mono ${badgeClass}`}>
      <span className="dir-glyph">{arrow}</span>
      <span>{direction || 'NEUTRAL'}</span>
    </span>
  );
}

export function OutcomePip({ isPending, isHit, date, title, isLive = false }) {
  if (isPending) {
    return (
      <span 
        className={`outcome-pip ${isLive ? 'pip-pending' : 'pip-unreviewed'} font-mono`} 
        title={title || `${date}: ${isLive ? 'Session Active Live' : 'Not reviewed'}`}
      >
        {isLive ? '⏳ Live' : '⏳ Not reviewed'}
      </span>
    );
  }
  return (
    <span 
      className={`outcome-pip font-mono ${isHit ? 'pip-hit' : 'pip-miss'}`}
      title={title || `${date}: ${isHit ? 'Hit' : 'Miss'}`}
    >
      {isHit ? '● Hit' : '▲ Miss'}
    </span>
  );
}

export function HeuristicStatusBadge({ status }) {
  const s = (status || '').toUpperCase();
  if (s === 'ACTIVE') {
    return (
      <span className="heuristic-pill pill-active font-mono">
        <span className="status-indicator-dot" />
        <span>ACTIVE</span>
      </span>
    );
  }
  if (s === 'SUPERSEDED') {
    return (
      <span className="heuristic-pill pill-superseded font-mono">
        <span className="status-indicator-dot" />
        <span>SUPERSEDED</span>
      </span>
    );
  }
  return (
    <span className="heuristic-pill pill-observed font-mono">
      <span className="status-indicator-dot" />
      <span>OBSERVED ONLY</span>
    </span>
  );
}

export function DataQualityBadge({ isWebFallback, isUnscorable, confidence }) {
  if (isUnscorable) {
    return (
      <span
        className="font-mono text-xs"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          padding: "2px 6px",
          borderRadius: "var(--radius-sm)",
          background: "var(--surface-well)",
          border: "1px solid var(--border-default)",
          color: "var(--text-tertiary)",
          fontWeight: 600,
          fontSize: "12px",
          letterSpacing: "0.04em",
        }}
        title="Session cannot be scored due to holiday, early close, or market disruption"
      >
        ⏸ UNSCORABLE
      </span>
    );
  }
  if (isWebFallback) {
    return (
      <span
        className="font-mono text-xs"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          padding: "2px 6px",
          borderRadius: "var(--radius-sm)",
          background: "var(--warning-bg)",
          border: "1px solid var(--warning-border)",
          color: "var(--warning-text)",
          fontWeight: 600,
          fontSize: "12px",
          letterSpacing: "0.04em",
        }}
        title="Data sourced via web search fallback, not primary provider"
      >
        ⚡ WEB FALLBACK
      </span>
    );
  }
  return null;
}

