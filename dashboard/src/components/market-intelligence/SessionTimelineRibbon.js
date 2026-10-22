'use client';

function formatPillDate(dateStr) {
  if (!dateStr) return '';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const mIdx = parseInt(parts[1], 10) - 1;
      return `${parseInt(parts[2], 10)} ${monthNames[mIdx] || parts[1]}`;
    }
  } catch (e) {}
  return dateStr;
}

export default function SessionTimelineRibbon({ reviews = [], activeDate, onSelectDate }) {
  if (!reviews || reviews.length === 0) return null;

  return (
    <div className="session-timeline-ribbon-module" style={{
      background: 'var(--surface)',
      border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-md)',
      padding: '10px 14px',
      marginTop: '8px',
      marginBottom: '10px',
      boxShadow: 'var(--shadow-card)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="font-mono text-xs font-bold" style={{ color: 'var(--accent-cyan)', letterSpacing: '0.04em' }}>
            SESSION TIMELINE SCRUBBER
          </span>
          <span className="font-mono text-xs text-muted">
            · Tap session to inspect
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          <span style={{ color: 'var(--matched-text)' }}>● 9 Hits</span>
          <span style={{ color: 'var(--missed-text)' }}>▲ 11 Misses</span>
        </div>
      </div>

      {/* Horizontal Scrollable Ribbon */}
      <div
        tabIndex={0}
        role="region"
        aria-label="Historical session timeline ribbon"
        style={{
          display: 'flex',
          gap: '6px',
          overflowX: 'auto',
          paddingBottom: '6px',
          scrollbarWidth: 'thin',
        }}
      >
        {reviews.map((r) => {
          const isSelected = (activeDate || reviews[0]?.date) === r.date;
          const isHit = r.ihsg_correct === true;
          const isPending = r.isPendingReview;
          const isBull = (r.ihsg_predicted || '').toLowerCase().includes('bullish');

          const borderColor = isSelected
            ? 'var(--accent-cyan)'
            : 'var(--border-default)';

          const bgColor = isSelected
            ? 'var(--surface-well)'
            : 'var(--surface-subtle)';

          const statusColor = isPending
            ? 'var(--warning-text)'
            : isHit
            ? 'var(--matched-text)'
            : 'var(--missed-text)';

          return (
            <button
              key={r.date}
              type="button"
              className={`timeline-pill ${isSelected ? 'timeline-pill-selected' : ''}`}
              onClick={() => onSelectDate && onSelectDate(r.date)}
              style={{
                display: 'inline-flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                padding: '8px 12px',
                borderRadius: '6px',
                border: `1.5px solid ${borderColor}`,
                background: bgColor,
                cursor: 'pointer',
                minWidth: '78px',
                minHeight: '52px',
                touchAction: 'manipulation',
                transition: 'all 0.15s ease',
                boxShadow: isSelected ? '0 0 10px rgba(8, 145, 178, 0.25)' : 'none',
              }}
              title={`${r.date}: Call ${r.ihsg_predicted || '—'} vs Actual ${r.ihsg_actual || '—'} (${isHit ? 'Hit' : 'Miss'})`}
            >
              <span className="font-mono text-xs font-bold" style={{ color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                {formatPillDate(r.date)}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '3px' }}>
                <span style={{ fontSize: '12px', color: isBull ? 'var(--matched-text)' : 'var(--missed-text)' }}>
                  {isBull ? '▲' : '▼'}
                </span>
                <span className="font-mono text-xs font-semibold" style={{ color: statusColor }}>
                  {isPending ? 'Pending' : isHit ? 'Hit' : 'Miss'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
