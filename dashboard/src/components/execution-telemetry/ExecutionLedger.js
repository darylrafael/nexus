'use client';
import { useState } from 'react';
import RunDetailDrawer from './RunDetailDrawer';
import { EmptyState } from '../common/StateViews';

export default function ExecutionLedger({ sessions = [] }) {
  const [selectedRun, setSelectedRun] = useState(null);

  if (!sessions || sessions.length === 0) {
    return (
      <div className="history-section">
        <header className="history-header">
          <div>
            <h2 className="history-title">Pipeline Execution Ledger</h2>
            <div className="history-subtitle font-mono text-xs">Recent session invocations stored in SQLite</div>
          </div>
        </header>
        <div style={{ padding: '24px' }}>
          <EmptyState
            title="No Execution Logs"
            message="No pipeline session records found in the SQLite database."
          />
        </div>
      </div>
    );
  }

  return (
    <section className="history-section">
      <header className="history-header">
        <div>
          <h2 className="history-title">Pipeline Execution Ledger</h2>
          <div className="history-subtitle font-mono text-xs">Recent session invocations stored in SQLite (click row to audit)</div>
        </div>
        <span className="eval-section-tag font-mono">{sessions.length} Recent Invocations</span>
      </header>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Agent Component</th>
              <th>Model Core</th>
              <th>Latency</th>
              <th>Status</th>
              <th>Audit</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((run) => (
              <tr 
                key={run.id} 
                className="table-row"
                onClick={() => setSelectedRun(run)}
              >
                <td className="font-mono text-xs text-muted">
                  {run.timestamp?.replace('T', ' ').slice(0, 19) || '—'}
                </td>
                <td className="font-mono font-bold text-primary">
                  {run.agent}
                </td>
                <td className="font-mono text-xs text-secondary">
                  {run.model || 'Default'}
                </td>
                <td className="font-mono text-xs">
                  {run.duration_ms ? `${(run.duration_ms / 1000).toFixed(2)}s` : '—'}
                </td>
                <td>
                  <span className={`status-pill ${run.success ? 'status-matched' : 'status-missed'} status-sm font-mono`}>
                    <span className="status-indicator-dot" />
                    <span>{run.success ? 'SUCCESS' : 'FAILED'}</span>
                  </span>
                </td>
                <td>
                  <button 
                    className="state-action-btn font-mono text-xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedRun(run);
                    }}
                    style={{ padding: '2px 8px' }}
                  >
                    Details →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <RunDetailDrawer
        isOpen={Boolean(selectedRun)}
        onClose={() => setSelectedRun(null)}
        run={selectedRun}
      />
    </section>
  );
}
