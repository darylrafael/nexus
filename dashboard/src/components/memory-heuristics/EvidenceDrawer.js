'use client';
import SideSheet from '../common/SideSheet';
import { HeuristicStatusBadge } from '../common/Badges';

function formatPct(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
}

export default function EvidenceDrawer({ isOpen, onClose, heuristic }) {
  if (!heuristic) return null;

  const {
    rule,
    category,
    status,
    observed,
    validated,
    contradicted,
    validationRate,
    evidence = []
  } = heuristic;

  return (
    <SideSheet
      isOpen={isOpen}
      onClose={onClose}
      title="Heuristic Provenance & Evidence"
      subtitle={`Category: ${category} · Rule ${heuristic.id}`}
      tag="Audit Provenance"
      maxWidth="680px"
    >
      <div className="evidence-panel-root">
        {/* Rule Definition Box */}
        <div className="evidence-rule-card">
          <div className="evidence-rule-header">
            <span className="detail-label font-mono">Formulated Heuristic Rule</span>
            <HeuristicStatusBadge status={status} />
          </div>
          <p className="evidence-rule-text">“{rule}”</p>
        </div>

        {/* Empirical Metrics Bar */}
        <div className="evidence-metrics-grid">
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-muted">Observed</span>
            <span className="font-mono text-base font-bold">{observed}</span>
          </div>
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-matched">Validated</span>
            <span className="font-mono text-base font-bold text-matched">{validated}</span>
          </div>
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-missed">Contradicted</span>
            <span className="font-mono text-base font-bold text-missed">{contradicted}</span>
          </div>
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-secondary">Validation Rate</span>
            <span className="font-mono text-base font-bold">
              {validationRate !== null ? `${validationRate}%` : 'Unresolved'}
            </span>
          </div>
        </div>

        {/* Historical Evidence Provenance Ledger */}
        <div className="evidence-ledger-header">
          <span className="eval-section-heading">Observed Session History</span>
          <span className="eval-section-tag font-mono">{evidence.length} Record{evidence.length === 1 ? '' : 's'}</span>
        </div>

        <div className="evidence-timeline">
          {evidence.map((item, idx) => (
            <div className="evidence-timeline-item" key={idx}>
              <div className="evidence-timeline-top">
                <span className="font-mono font-bold text-sm">{item.date}</span>
                <span className={`evidence-outcome-tag font-mono text-xs ${
                  item.outcome === 'VALIDATED' ? 'outcome-valid' : (item.outcome === 'CONTRADICTED' ? 'outcome-contra' : 'outcome-obs')
                }`}>
                  {item.outcome}
                </span>
              </div>
              <div className="evidence-timeline-body font-mono text-xs">
                <span>IHSG Actual: </span>
                <span className="font-bold">{item.ihsg_actual}</span>
                {item.ihsg_actual_pct !== undefined && item.ihsg_actual_pct !== 0 && (
                  <span className="text-muted"> ({formatPct(item.ihsg_actual_pct)})</span>
                )}
              </div>
              <p className="evidence-timeline-desc text-xs">{item.summary}</p>
            </div>
          ))}

          {evidence.length === 0 && (
            <div className="text-muted font-mono text-xs" style={{ padding: '16px 0' }}>
              No historical trace log attached to this rule.
            </div>
          )}
        </div>
      </div>
    </SideSheet>
  );
}
