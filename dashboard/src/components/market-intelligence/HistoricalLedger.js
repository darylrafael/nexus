'use client';
import { useState, useMemo } from 'react';
import { DirectionBadge, StatusBadge } from '../common/Badges';

function formatNumber(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return num.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 2 });
}

function formatPct(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
}

function cleanNarrative(text) {
  if (!text) return '';
  return text.replace(/\[src_[^\]]+\]/g, '').trim();
}

function HistoryRow({ review, isSelected, onSelectSession }) {
  const [expanded, setExpanded] = useState(false);
  const isUp = Number(review.ihsg_actual_pct) >= 0;
  const accuracyNum = Math.min(100, Math.max(0, Number(review.accuracy_score) || 0));
  const bpsNum = Math.round(Number(review.ihsg_actual_pct || 0) * 100);

  const secEntries = Object.entries(review.sector_accuracy || {});
  const secMatches = secEntries.filter(([_, hit]) => hit === true).length;
  const secTotal = secEntries.length;

  return (
    <>
      <tr 
        className={`table-row ${isSelected ? 'active-row' : ''} ${expanded ? 'expanded' : ''}`}
        onClick={() => onSelectSession && onSelectSession(review.date)}
      >
        <td className="font-mono font-medium">
          <div className="table-call-cell">
            <span
              className={`chevron-icon ${expanded ? 'rotated' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                setExpanded(!expanded);
              }}
              title="Expand audit breakdown"
            >
              ▶
            </span>
            <span>{review.date}</span>
          </div>
        </td>
        <td>
          <div className="table-call-cell">
            <DirectionBadge direction={review.ihsg_predicted} />
            {review.ihsg_confidence && (
              <span className="font-mono text-xs text-muted">({review.ihsg_confidence}%)</span>
            )}
          </div>
        </td>
        <td>
          <DirectionBadge direction={review.isPendingReview ? 'PENDING' : review.ihsg_actual} />
        </td>
        <td>
          {review.isPendingReview ? (
            <span className="font-mono text-xs text-muted">In Progress</span>
          ) : (
            <div className="delta-cell font-mono">
              <span className={isUp ? 'text-matched' : 'text-missed'}>{formatPct(review.ihsg_actual_pct)}</span>
              <span className="bps-text text-muted">({bpsNum > 0 ? `+${bpsNum}` : bpsNum} bps)</span>
            </div>
          )}
        </td>
        <td>
          <div className="font-mono text-xs flow-cell">
            <span>{review.foreign_flow_actual || 'N/A'}</span>
            {review.foreign_flow_correct !== undefined && review.foreign_flow_correct !== null && (
              <span className={`font-semibold ${review.foreign_flow_correct ? 'text-matched' : 'text-missed'}`}>
                ({review.foreign_flow_correct ? '✓' : '✗'})
              </span>
            )}
          </div>
        </td>
        <td>
          <span className="font-mono text-xs text-muted">
            {review.isPendingReview
              ? `${secTotal} Tracked`
              : (secTotal > 0 ? `${secMatches}/${secTotal} (${Math.round((secMatches / secTotal) * 100)}%)` : '—')}
          </span>
        </td>
        <td>
          {review.isPendingReview ? (
            <span className="font-mono text-xs text-muted">Pending</span>
          ) : (
            <div className="accuracy-cell font-mono">
              <span className="accuracy-text">{formatNumber(review.accuracy_score)}%</span>
              <div className="accuracy-bar-track">
                <div className="accuracy-bar-fill" style={{ width: `${accuracyNum}%` }} />
              </div>
            </div>
          )}
        </td>
        <td>
          <StatusBadge correct={review.ihsg_correct} isPending={review.isPendingReview} size="sm" />
        </td>
      </tr>
      {expanded && (
        <tr className="expanded-row">
          <td colSpan="8" className="expanded-cell">
            <div className="expanded-panel">
              <div className="expanded-grid">
                <div className="detail-item">
                  <div className="detail-label font-mono">Executive Summary</div>
                  <div className="detail-value">{cleanNarrative(review.summary) || 'No narrative logged.'}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label font-mono">Key Market Risk</div>
                  <div className="detail-value">{cleanNarrative(review.key_risk) || 'None documented.'}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label font-mono">Active Emittents</div>
                  <div className="detail-value font-mono text-xs">
                    {(review.recommended_tickers || []).join(', ') || 'None selected'}
                  </div>
                </div>
              </div>
              {review.lessons && review.lessons.length > 0 && (
                <div className="expanded-lesson">
                  <div className="detail-label font-mono" style={{ marginBottom: '4px' }}>Captured Learning Heuristic</div>
                  <p className="expanded-lesson-text">“{cleanNarrative(review.lessons[0])}”</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function HistoricalLedger({ reviews = [], activeReview, onSelectSession, wins = 0, evaluatedCount = 0 }) {
  const [filter, setFilter] = useState('all');

  const filteredReviews = useMemo(() => {
    if (filter === 'matched') return reviews.filter((r) => r.ihsg_correct === true);
    if (filter === 'missed') return reviews.filter((r) => !r.isPendingReview && r.ihsg_correct === false);
    return reviews;
  }, [reviews, filter]);

  return (
    <section className="history-section">
      <header className="history-header">
        <div>
          <h2 className="history-title">Historical Evaluation Archive</h2>
          <div className="history-subtitle font-mono text-xs">Chronological ledger of autonomous post-market evaluations</div>
        </div>
        <div className="filter-tabs">
          <button
            className={`filter-tab-btn font-mono ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All ({reviews.length})
          </button>
          <button
            className={`filter-tab-btn font-mono ${filter === 'matched' ? 'active' : ''}`}
            onClick={() => setFilter('matched')}
          >
            Matched ({wins})
          </button>
          <button
            className={`filter-tab-btn font-mono ${filter === 'missed' ? 'active' : ''}`}
            onClick={() => setFilter('missed')}
          >
            Missed ({Math.max(0, evaluatedCount - wins)})
          </button>
        </div>
      </header>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Session Date</th>
              <th>Pre-Market Call</th>
              <th>Session Close</th>
              <th>Spread (Bps)</th>
              <th>Foreign Flow</th>
              <th>Sector Hit</th>
              <th>Accuracy</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {filteredReviews.map((review) => (
              <HistoryRow
                key={review.date}
                review={review}
                isSelected={activeReview?.date === review.date}
                onSelectSession={onSelectSession}
              />
            ))}
            {filteredReviews.length === 0 && (
              <tr>
                <td colSpan="8" className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '24px 0' }}>
                  No evaluation records match the selected filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
