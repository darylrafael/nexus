'use client';

function formatNumber(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return num.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 2 });
}

function cleanNarrative(text) {
  if (!text) return '';
  return text.replace(/\[src_[^\]]+\]/g, '').trim();
}

function RCAPanel({ review }) {
  const unanticipated = review?.rca_unanticipated || [];
  const underestimated = review?.rca_underestimated || [];
  const overestimated = review?.rca_overestimated || [];
  const lessons = review?.lessons || [];

  const hasDiagnostics = unanticipated.length > 0 || underestimated.length > 0 || overestimated.length > 0;

  return (
    <div className="eval-pane">
      <div className="eval-pane-header">
        <div className="eval-pane-header-left">
          <span className="eval-pane-title">RCA &amp; Heuristic Feedback Loop</span>
          <span className="eval-section-tag font-mono">Self-Correction</span>
        </div>
      </div>

      <div className="eval-pane-body">
        {hasDiagnostics && (
          <div className="rca-diagnostic-grid">
            {unanticipated.length > 0 && (
              <div className="rca-diag-card">
                <div className="rca-diag-head text-missed font-mono">Unanticipated Catalysts</div>
                <ul className="rca-diag-list">
                  {unanticipated.map((item, idx) => (
                    <li key={idx} className="rca-diag-item">{cleanNarrative(item)}</li>
                  ))}
                </ul>
              </div>
            )}
            {underestimated.length > 0 && (
              <div className="rca-diag-card">
                <div className="rca-diag-head text-warning font-mono">Underestimated Macro</div>
                <ul className="rca-diag-list">
                  {underestimated.map((item, idx) => (
                    <li key={idx} className="rca-diag-item">{cleanNarrative(item)}</li>
                  ))}
                </ul>
              </div>
            )}
            {overestimated.length > 0 && (
              <div className="rca-diag-card">
                <div className="rca-diag-head text-muted font-mono">Overestimated Risks</div>
                <ul className="rca-diag-list">
                  {overestimated.map((item, idx) => (
                    <li key={idx} className="rca-diag-item">{cleanNarrative(item)}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {lessons.length > 0 && (
          <div className="eval-pane-section" style={{ borderBottom: 'none' }}>
            <div className="eval-pane-section-header">
              <span className="eval-section-heading">Heuristic Formulated</span>
              <span className="eval-section-tag font-mono">Injected to Memory</span>
            </div>
            <div className="rca-lesson-card">
              <p className="rca-lesson-text">“{cleanNarrative(lessons[0])}”</p>
              <div className="rca-lesson-meta font-mono">
                <span>Session Date: {review?.date}</span>
                <span className="text-matched">Active in Vault</span>
              </div>
            </div>
          </div>
        )}

        {!hasDiagnostics && lessons.length === 0 && (
          <div style={{ padding: '24px 20px' }}>
            <p className="rca-content-muted font-mono text-xs">
              {review?.isPendingReview
                ? 'Trading session currently underway. Automated post-market attribution and root-cause analysis will execute after market close.'
                : 'Model parameters converged within target error bands. No active parameter revisions injected.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SectorAssetTape({ review }) {
  if (!review) return null;

  const entries = Object.entries(review.sector_accuracy || {});
  const isPending = review?.isPendingReview;
  const commodities = Object.values(review?.actual_commodities || {}).filter(
    (item) => item && item.name && Number.isFinite(Number(item.change_pct))
  );

  const usdidr = review?.actual_usdidr;
  const isUsdNumeric = Number.isFinite(Number(usdidr));

  return (
    <div className="eval-body">
      {/* Left Column: Sector Tape & Cross-Asset Feeds */}
      <div className="eval-column-left">
        <div className="eval-pane">
          <div className="eval-pane-header">
            <div className="eval-pane-header-left">
              <span className="eval-pane-title">Sector Intelligence &amp; Feeds</span>
              <span className="eval-section-tag font-mono">Deterministic Engine</span>
            </div>
          </div>

          <div className="eval-pane-body">
            {/* Sector Tape */}
            {entries.length > 0 && (
              <div className="eval-pane-section">
                <div className="eval-pane-section-header">
                  <span className="eval-section-heading">Sector Bias &amp; Accuracy</span>
                  <span className="eval-section-tag font-mono">
                    {isPending ? "Today's Sector Bias" : "Rule-Based Impact"}
                  </span>
                </div>
                <div className="sector-tape">
                  {entries.map(([sector, statusOrHit]) => {
                    let label = "▲ Miss";
                    let cls = "text-missed";
                    if (isPending) {
                      cls = statusOrHit === 'BULLISH' ? "text-matched" : (statusOrHit === 'BEARISH' ? "text-missed" : "text-muted");
                      label = statusOrHit;
                    } else if (statusOrHit) {
                      cls = "text-matched";
                      label = "● Match";
                    }
                    return (
                      <div className="sector-tile" key={sector}>
                        <span className="sector-name">{sector}</span>
                        <span className={`sector-indicator font-mono ${cls}`}>
                          {label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Cross-Asset Feeds */}
            <div className="eval-pane-section" style={{ borderBottom: 'none' }}>
              <div className="eval-pane-section-header">
                <span className="eval-section-heading">Macro Indicators</span>
                <span className="eval-section-tag font-mono">Cross-Asset Telemetry</span>
              </div>
              <div className="macro-tape-strip">
                <div className="macro-strip-cell">
                  <div className="macro-cell-head">USD / IDR Reference</div>
                  <div className="macro-cell-val font-mono">
                    {isUsdNumeric ? `Rp ${formatNumber(usdidr)}` : (usdidr || 'Rp 15,385')}
                  </div>
                  <div className="macro-cell-sub">Bank Indonesia / FX</div>
                </div>

                {commodities.map((item) => {
                  const change = Number(item.change_pct);
                  const isUp = change >= 0;
                  return (
                    <div className="macro-strip-cell" key={item.ticker || item.name}>
                      <div className="macro-cell-head">{item.name}</div>
                      <div className="macro-cell-val font-mono">
                        ${Number(item.price).toFixed(2)}
                      </div>
                      <div className={`macro-cell-sub font-mono ${isUp ? 'text-matched' : 'text-missed'}`}>
                        {isUp ? '▲' : '▼'} {isUp ? '+' : ''}{change.toFixed(2)}%
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: RCA & Feedback */}
      <div className="eval-column-right">
        <RCAPanel review={review} />
      </div>
    </div>
  );
}
