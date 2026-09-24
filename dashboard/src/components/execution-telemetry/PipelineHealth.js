'use client';

export default function PipelineHealth({ stats }) {
  if (!stats) return null;

  const {
    totalRuns = 0,
    successfulRuns = 0,
    failedRuns = 0,
    successRate = '0.0',
    avgDurationMs = 0,
    runsToday = 0
  } = stats;

  const avgSeconds = (avgDurationMs / 1000).toFixed(2);

  return (
    <section className="kpi-row">
      {/* Card 1: Success Rate */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Success Rate</span>
          <span className="kpi-target-tag font-mono">Reliability</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono text-matched">{successRate}%</div>
          <span className="kpi-tag-visual font-mono text-xs">
            {failedRuns} Failed
          </span>
        </div>
        <div className="kpi-context">
          <span>{successfulRuns} of {totalRuns} total pipeline calls succeeded</span>
          <div className="kpi-mini-bar">
            <div 
              className="kpi-mini-fill" 
              style={{ width: `${Math.min(100, Math.max(0, Number(successRate) || 0))}%` }} 
            />
          </div>
        </div>
      </div>

      {/* Card 2: Average Duration */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Avg Latency</span>
          <span className="kpi-target-tag font-mono">Compute Time</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono">{avgSeconds}s</div>
          <span className="kpi-tag-visual font-mono text-xs text-muted">
            {avgDurationMs}ms
          </span>
        </div>
        <div className="kpi-context">
          <span>Mean end-to-end execution duration</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '65%' }} />
          </div>
        </div>
      </div>

      {/* Card 3: Runs Today */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Runs Today</span>
          <span className="kpi-target-tag font-mono">Cadence</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono">{runsToday}</div>
          <span className="kpi-tag-visual font-mono text-xs text-matched">Active</span>
        </div>
        <div className="kpi-context">
          <span>Invocations logged for current trading date</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '80%' }} />
          </div>
        </div>
      </div>

      {/* Card 4: SQLite Database Ledger */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">SQLite Ledger</span>
          <span className="kpi-target-tag font-mono">Audit Store</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono text-base" style={{ fontSize: '18px', paddingTop: '6px' }}>
            nexus_sessions
          </div>
          <span className="kpi-tag-visual font-mono text-xs text-matched">Connected</span>
        </div>
        <div className="kpi-context">
          <span>Persistent local transactional session store</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '100%' }} />
          </div>
        </div>
      </div>
    </section>
  );
}
