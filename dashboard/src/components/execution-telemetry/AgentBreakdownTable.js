'use client';
import { EmptyState } from '../common/StateViews';

export default function AgentBreakdownTable({ breakdown = [] }) {
  if (!breakdown || breakdown.length === 0) {
    return (
      <div className="eval-pane" style={{ marginBottom: '24px' }}>
        <div className="eval-pane-header">
          <span className="eval-pane-title">Deterministic Agent Performance</span>
          <span className="eval-section-tag font-mono">Aggregation</span>
        </div>
        <div style={{ padding: '24px' }}>
          <EmptyState 
            title="No Agent Records" 
            message="No agent execution telemetry has been aggregated in SQLite yet."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="eval-pane" style={{ marginBottom: '28px' }}>
      <div className="eval-pane-header">
        <div className="eval-pane-header-left">
          <span className="eval-pane-title">Deterministic Agent Performance Breakdown</span>
          <span className="eval-section-tag font-mono">SQLite Session Telemetry</span>
        </div>
        <span className="eval-section-tag font-mono">{breakdown.length} Component Agents</span>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Agent Component</th>
              <th>Total Invocations</th>
              <th>Avg Latency</th>
              <th>Success Rate</th>
              <th>Error Count</th>
            </tr>
          </thead>
          <tbody>
            {breakdown.map((agent) => (
              <tr key={agent.agent} className="table-row">
                <td className="font-mono font-bold text-primary">{agent.agent}</td>
                <td className="font-mono">{agent.total_calls} calls</td>
                <td className="font-mono text-muted">
                  {agent.avg_duration_ms > 1000 
                    ? `${(agent.avg_duration_ms / 1000).toFixed(2)}s` 
                    : `${agent.avg_duration_ms}ms`}
                </td>
                <td className="font-mono font-semibold">
                  <span className={Number(agent.success_rate_pct) >= 90 ? 'text-matched' : 'text-warning'}>
                    {agent.success_rate_pct}%
                  </span>
                </td>
                <td className="font-mono text-xs">
                  {agent.error_count > 0 ? (
                    <span className="text-missed font-bold">▲ {agent.error_count}</span>
                  ) : (
                    <span className="text-muted">0</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
