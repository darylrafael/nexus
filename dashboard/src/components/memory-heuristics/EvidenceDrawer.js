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
    trigger,
    outcome,
    category,
    originDate,
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
      title={`Rule ${heuristic.id} · ${category}`}
      subtitle={`Formulated ${originDate || 'in post-market audit'} · Forward Provenance`}
      tag={status}
      maxWidth="660px"
    >
      <div className="evidence-panel-root">
        {/* Structured WHEN -> THEN Rule Card */}
        <div className="evidence-rule-card">
          <div className="evidence-rule-header">
            <span className="detail-label font-mono">Causal Heuristic Structure</span>
            <HeuristicStatusBadge status={status} />
          </div>

          {trigger && outcome ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
              <div style={{ padding: '8px 10px', background: 'var(--surface-well)', borderRadius: '4px', borderLeft: '3px solid var(--accent-cyan)' }}>
                <div className="font-mono text-xs" style={{ color: 'var(--accent-cyan)', fontWeight: 700, marginBottom: '2px' }}>WHEN (CONDITION / DIVERGENCE)</div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-primary)', lineHeight: 1.45 }}>{trigger}</div>
              </div>
              <div style={{ padding: '8px 10px', background: 'var(--surface-well)', borderRadius: '4px', borderLeft: '3px solid var(--matched-text)' }}>
                <div className="font-mono text-xs" style={{ color: 'var(--matched-text)', fontWeight: 700, marginBottom: '2px' }}>THEN (MARKET IMPACT / CONSTRAINT)</div>
                <div style={{ fontSize: '12.5px', color: 'var(--text-primary)', lineHeight: 1.45 }}>{outcome}</div>
              </div>
            </div>
          ) : (
            <p className="evidence-rule-text" style={{ marginTop: '6px' }}>{rule}</p>
          )}
        </div>

        {/* Empirical Metrics Bar */}
        <div className="evidence-metrics-grid">
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-muted">Tested Runs</span>
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
            <span className="font-mono text-xs text-secondary">Win Rate</span>
            <span className="font-mono text-base font-bold">
              {validationRate !== null ? `${validationRate}%` : 'Awaiting'}
            </span>
          </div>
        </div>

        {/* Historical Evidence Provenance Ledger */}
        <div className="evidence-ledger-header">
          <span className="eval-section-heading">Session Provenance Trace</span>
          <span className="eval-section-tag font-mono">{evidence.length} Event{evidence.length === 1 ? '' : 's'}</span>
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
                <span>IHSG Close: </span>
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
