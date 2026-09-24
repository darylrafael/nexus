'use client';
import { OutcomePip } from '../common/Badges';

function PerformanceSparkline({ reviews = [] }) {
  const evaluated = reviews.filter((r) => !r.isPendingReview && r.accuracy_score !== undefined);
  if (evaluated.length < 2) return null;
  const scores = evaluated.map((r) => Number(r.accuracy_score) || 0).reverse();

  const width = 84;
  const height = 24;
  const min = Math.min(...scores, 40);
  const max = Math.max(...scores, 100);
  const range = max - min || 1;

  const points = scores
    .map((score, i) => {
      const x = (i / (scores.length - 1)) * (width - 4) + 2;
      const y = height - ((score - min) / range) * (height - 6) - 3;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <div className="sparkline-wrapper" title={`Accuracy trajectory across ${scores.length} sessions`}>
      <svg width={width} height={height} className="sparkline-svg">
        <polyline
          fill="none"
          stroke="var(--accent-cyan)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={points}
        />
        {scores.map((score, i) => {
          const x = (i / (scores.length - 1)) * (width - 4) + 2;
          const y = height - ((score - min) / range) * (height - 6) - 3;
          const isLatest = i === scores.length - 1;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r={isLatest ? 2.5 : 1.5}
              fill={isLatest ? 'var(--matched-text)' : 'var(--accent-cyan)'}
            />
          );
        })}
      </svg>
    </div>
  );
}

export default function MarketOverviewKPIs({ dashboard }) {
  if (!dashboard) return null;

  const {
    winRate,
    wins,
    evaluatedCount,
    avgAccuracy,
    reviews = [],
    latest,
    stats = {}
  } = dashboard;

  const sectorBreadth = stats.sectorBreadth || { bullish: 0, bearish: 0, neutral: 0, total: 0 };
  const foreignFlow = latest?.isPendingReview
    ? (latest?.foreign_flow_predicted || 'Market Open')
    : (latest?.foreign_flow_actual || 'Neutral');

  return (
    <section className="kpi-row">
      {/* Card 1: IHSG Hit Rate */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">IHSG Hit Rate</span>
          <span className="kpi-target-tag font-mono">Directional</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono">{winRate}%</div>
          <div className="outcome-pips font-mono">
            {reviews.slice(0, 5).map((r) => (
              <OutcomePip
                key={r.date}
                date={r.date}
                isPending={r.isPendingReview}
                isHit={r.ihsg_correct}
              />
            ))}
          </div>
        </div>
        <div className="kpi-context">
          <span>{wins} of {evaluatedCount} evaluated sessions matched call</span>
          <div className="kpi-mini-bar">
            <div
              className="kpi-mini-fill"
              style={{ width: `${Math.min(100, Math.max(0, Number(winRate) || 0))}%` }}
            />
          </div>
        </div>
      </div>

      {/* Card 2: Composite Accuracy Trajectory */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Overall Accuracy</span>
          <span className="kpi-target-tag font-mono">Target ≥60%</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono">{avgAccuracy}%</div>
          <PerformanceSparkline reviews={reviews} />
        </div>
        <div className="kpi-context">
          <span>Trailing multi-factor attribution score</span>
          <div className="kpi-mini-bar">
            <div
              className="kpi-mini-fill"
              style={{ width: `${Math.min(100, Math.max(0, Number(avgAccuracy) || 0))}%` }}
            />
          </div>
        </div>
      </div>

      {/* Card 3: Foreign Capital Flow Bias */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Foreign Flow</span>
          <span className="kpi-target-tag font-mono">IDX Net Flow</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono text-base" style={{ fontSize: '18px', paddingTop: '6px' }}>
            {foreignFlow}
          </div>
          <span className="kpi-tag-visual font-mono text-xs">
            {latest?.isPendingReview ? 'Predicted Bias' : 'Closing Flow'}
          </span>
        </div>
        <div className="kpi-context">
          <span>Institutional capital tracking</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '70%' }} />
          </div>
        </div>
      </div>

      {/* Card 4: Sector Breadth & Regime (Replaces Telemetry Sync) */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Sector Breadth</span>
          <span className="kpi-target-tag font-mono">Deterministic</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono" style={{ fontSize: '20px', paddingTop: '4px' }}>
            <span className="text-matched">{sectorBreadth.bullish}▲</span>
            <span className="text-muted" style={{ margin: '0 6px' }}>·</span>
            <span className="text-missed">{sectorBreadth.bearish}▼</span>
            <span className="text-muted" style={{ margin: '0 6px' }}>·</span>
            <span className="text-muted">{sectorBreadth.neutral}—</span>
          </div>
          <span className="kpi-tag-visual font-mono text-xs">
            {sectorBreadth.total} Tracked
          </span>
        </div>
        <div className="kpi-context">
          <span>Deterministic sector causality distribution</span>
          <div className="kpi-mini-bar">
            <div
              className="kpi-mini-fill"
              style={{
                width: `${sectorBreadth.total > 0 ? (sectorBreadth.bullish / sectorBreadth.total) * 100 : 50}%`
              }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
