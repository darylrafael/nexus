'use client';

export function StatusBadge({ correct, isPending, size = 'md' }) {
  if (isPending || correct === null || correct === undefined) {
    return (
      <span className={`status-pill status-pending ${size === 'sm' ? 'status-sm' : ''}`}>
        <span className="status-indicator-dot" />
        <span className="status-text font-mono">IN PROGRESS</span>
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

export function OutcomePip({ isPending, isHit, date, title }) {
  if (isPending) {
    return (
      <span 
        className="outcome-pip pip-pending font-mono" 
        title={title || `${date}: Session Active In Progress`}
      >
        ⏳ Live
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
