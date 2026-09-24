'use client';
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

function formatHeaderDate(d) {
  if (!d) return '';
  const parts = d.split('-');
  if (parts.length === 3) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const m = months[parseInt(parts[1], 10) - 1];
    return `${m} ${parts[2]}, ${parts[0]}`;
  }
  return d;
}

export default function VarianceBridge({ activeReview, isHistorical, onResetSelectedDate, latestDate }) {
  if (!activeReview) return null;

  const isMatched = activeReview.ihsg_correct;
  const isUp = Number(activeReview.ihsg_actual_pct) >= 0;
  const isPending = activeReview.isPendingReview;

  return (
    <section className="eval-section">
      <header className="eval-header">
        <div className="eval-header-title">
          {isPending 
            ? 'Active Trading Session — Pending Review' 
            : (isHistorical ? 'Historical Session Audit' : 'Post-Market Evaluation')}
        </div>
        <div className="eval-header-right">
          {isHistorical && (
            <button
              className="jump-latest-btn font-mono"
              onClick={onResetSelectedDate}
            >
              ← Jump to Latest ({formatHeaderDate(latestDate)})
            </button>
          )}
          <div className="eval-date-badge font-mono">{formatHeaderDate(activeReview.date)}</div>
        </div>
      </header>

      {/* 4-Column Execution Variance Bridge */}
      <div className="variance-bridge-grid">
        {/* Cell 1: Pre-Market Thesis */}
        <div className="bridge-cell">
          <div className="bridge-cell-header font-mono">PRE-MARKET THESIS</div>
          <div className="bridge-cell-body">
            <DirectionBadge direction={activeReview.ihsg_predicted} />
            {activeReview.ihsg_confidence && (
              <span className="confidence-pill font-mono">{activeReview.ihsg_confidence}% Conf</span>
            )}
          </div>
          <div className="bridge-cell-sub font-mono text-xs">
            Exp. Flow: <span className="text-secondary font-medium">{activeReview.foreign_flow_predicted || 'Neutral'}</span>
          </div>
        </div>

        {/* Cell 2: Session Close */}
        <div className="bridge-cell">
          <div className="bridge-cell-header font-mono">SESSION CLOSE</div>
          <div className="bridge-cell-body">
            {isPending ? (
              <span className="font-mono text-xs text-warning">Trading In Progress</span>
            ) : (
              <>
                <DirectionBadge direction={activeReview.ihsg_actual} />
                <span className={`font-mono text-sm font-semibold ${isUp ? 'text-matched' : 'text-missed'}`}>
                  ({formatPct(activeReview.ihsg_actual_pct)})
                </span>
              </>
            )}
          </div>
          <div className="bridge-cell-sub font-mono text-xs">
            Act. Flow: <span className="text-secondary font-medium">
              {isPending ? 'Pending Close' : (activeReview.foreign_flow_actual || 'N/A')}
            </span>
          </div>
        </div>

        {/* Cell 3: Spread & Delta */}
        <div className="bridge-cell">
          <div className="bridge-cell-header font-mono">SPREAD &amp; DELTA</div>
          <div className="bridge-cell-body">
            {isPending ? (
              <span className="font-mono text-xs text-muted">Awaiting Market Close</span>
            ) : (
              <>
                <span className={`font-mono text-base font-bold ${isUp ? 'text-matched' : 'text-missed'}`}>
                  {formatPct(activeReview.ihsg_actual_pct)}
                </span>
                <span className="font-mono text-xs text-muted">
                  ({Math.round(Number(activeReview.ihsg_actual_pct || 0) * 100)} bps)
                </span>
              </>
            )}
          </div>
          <div className="bridge-cell-sub font-mono text-xs">
            Variance: <span className={isPending ? 'text-muted' : (isMatched ? 'text-matched font-medium' : 'text-missed font-medium')}>
              {isPending ? 'Session Active' : (isMatched ? 'Direction Aligned' : 'Direction Divergence')}
            </span>
          </div>
        </div>

        {/* Cell 4: Attribution Verdict */}
        <div className="bridge-cell" style={{ borderRight: 'none' }}>
          <div className="bridge-cell-header font-mono">ATTRIBUTION VERDICT</div>
          <div className="bridge-cell-body">
            <StatusBadge correct={isMatched} isPending={isPending} />
          </div>
          <div className="bridge-cell-sub font-mono text-xs">
            Accuracy Score: <span className="text-primary font-bold">
              {isPending ? 'Awaiting Post-Market Review' : `${formatNumber(activeReview.accuracy_score)}%`}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
