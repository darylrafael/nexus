'use client';
import SideSheet from '../common/SideSheet';

export default function RunDetailDrawer({ isOpen, onClose, run }) {
  if (!run) return null;

  return (
    <SideSheet
      isOpen={isOpen}
      onClose={onClose}
      title={`Run Audit #${run.id}`}
      subtitle={`Agent: ${run.agent} · ${run.timestamp}`}
      tag="Execution Detail"
      maxWidth="680px"
    >
      <div className="evidence-panel-root">
        {/* Metric Summary */}
        <div className="evidence-metrics-grid">
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-muted">Status</span>
            <span className={`font-mono text-base font-bold ${run.success ? 'text-matched' : 'text-missed'}`}>
              {run.success ? '✓ SUCCESS' : '✕ FAILED'}
            </span>
          </div>
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-muted">Latency</span>
            <span className="font-mono text-base font-bold">
              {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(2)}s` : '—'}
            </span>
          </div>
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-muted">Model Core</span>
            <span className="font-mono text-xs font-semibold">{run.model || 'Default'}</span>
          </div>
          <div className="evidence-metric-item">
            <span className="font-mono text-xs text-muted">Timestamp</span>
            <span className="font-mono text-xs font-medium">{run.timestamp?.slice(11, 19) || '—'}</span>
          </div>
        </div>

        {/* Query Input */}
        <div className="detail-item" style={{ marginTop: '16px' }}>
          <div className="detail-label font-mono">Invocation Query / Trigger</div>
          <div className="detail-value font-mono text-xs" style={{ background: 'var(--surface-subtle)', padding: '12px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
            {run.query || 'Scheduled autonomous trigger'}
          </div>
        </div>

        {/* Error Trace if Failed */}
        {run.error_msg && (
          <div className="detail-item" style={{ marginTop: '16px' }}>
            <div className="detail-label font-mono text-missed">Error Traceback</div>
            <pre className="font-mono text-xs text-missed" style={{ background: 'var(--missed-bg)', padding: '12px', borderRadius: '4px', border: '1px solid var(--missed-border)', whiteSpace: 'pre-wrap' }}>
              {run.error_msg}
            </pre>
          </div>
        )}

        {/* Execution Output Preview */}
        {run.result && (
          <div className="detail-item" style={{ marginTop: '16px' }}>
            <div className="detail-label font-mono">Generated Output Preview</div>
            <pre className="font-mono text-xs" style={{ background: 'var(--surface-subtle)', padding: '14px', borderRadius: '4px', border: '1px solid var(--border-subtle)', whiteSpace: 'pre-wrap', maxHeight: '360px', overflowY: 'auto' }}>
              {run.result}
            </pre>
          </div>
        )}
      </div>
    </SideSheet>
  );
}
