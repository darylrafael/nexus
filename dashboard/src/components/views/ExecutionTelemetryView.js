'use client';
import { useState, useEffect, useMemo } from 'react';

function formatDuration(ms) {
  if (ms === null || ms === undefined) return '—';
  const num = Number(ms);
  if (Number.isNaN(num)) return '—';
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}s`;
  }
  return `${Math.round(num)}ms`;
}

function formatTimestamp(isoStr) {
  if (!isoStr) return '—';
  try {
    const parts = isoStr.split('T');
    if (parts.length === 2) {
      const date = parts[0];
      const time = parts[1].split('.')[0];
      return `${date} ${time}`;
    }
    return isoStr;
  } catch {
    return isoStr;
  }
}

function SessionRow({ session, expanded, onToggle }) {
  const isSuccess = Number(session.success) === 1;

  return (
    <>
      <tr 
        className={`table-row ${expanded ? 'expanded' : ''}`}
        onClick={onToggle}
      >
        <td className="font-mono font-medium">
          <div className="table-call-cell">
            <span className={`chevron-icon ${expanded ? 'rotated' : ''}`}>
              ▶
            </span>
            <span>#{session.id}</span>
          </div>
        </td>
        <td className="font-mono text-xs text-secondary">
          {formatTimestamp(session.timestamp)}
        </td>
        <td>
          <span className="font-mono text-xs font-semibold text-primary">
            {session.agent}
          </span>
        </td>
        <td>
          <span className="font-mono text-xs text-tertiary">
            {session.model || 'llm_client'}
          </span>
        </td>
        <td style={{ maxWidth: '280px', whiteSpace: 'normal', padding: '12px 14px' }}>
          <span className="font-mono text-xs text-primary font-medium">
            {session.query}
          </span>
        </td>
        <td className="font-mono text-xs">
          {formatDuration(session.duration_ms)}
        </td>
        <td>
          <span className={`status-pill ${isSuccess ? 'status-matched' : 'status-missed'} status-sm font-mono`}>
            <span className="status-indicator-dot" />
            <span>{isSuccess ? 'SUCCESS' : 'FAILED'}</span>
          </span>
        </td>
      </tr>
      {expanded && (
        <tr className="expanded-row">
          <td colSpan="7" className="expanded-cell">
            <div className="expanded-panel">
              <div className="expanded-grid">
                <div className="detail-item">
                  <div className="detail-label font-mono">Session ID &amp; Agent</div>
                  <div className="detail-value font-mono">#{session.id} · {session.agent}</div>
                  <div className="detail-sub font-mono">Model: {session.model || 'llm_client'}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label font-mono">Execution Latency</div>
                  <div className="detail-value font-mono">{formatDuration(session.duration_ms)}</div>
                  <div className="detail-sub font-mono">{session.duration_ms ? `${session.duration_ms} ms wall clock` : 'No duration metric'}</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label font-mono">Timestamp &amp; Status</div>
                  <div className="detail-value font-mono">{formatTimestamp(session.timestamp)}</div>
                  <div className="detail-sub font-mono">
                    {isSuccess ? 'Completed successfully (code 1)' : 'Failed execution (code 0)'}
                  </div>
                </div>
              </div>

              {/* Error Message if Failed */}
              {session.error_msg && (
                <div style={{ marginTop: '12px', padding: '10px 14px', background: 'var(--missed-bg)', border: '1px solid var(--missed-border)', borderRadius: 'var(--radius-sm)' }}>
                  <div className="font-mono text-xs font-bold text-missed" style={{ marginBottom: '4px' }}>
                    EXECUTION ERROR LOG:
                  </div>
                  <pre style={{ margin: 0, fontSize: '11px', color: 'var(--missed-text)', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                    {session.error_msg}
                  </pre>
                </div>
              )}

              {/* Execution Result Log */}
              <div className="expanded-lesson">
                <div className="detail-label font-mono" style={{ marginBottom: '8px' }}>
                  Raw Pipeline Output Payload
                </div>
                <div style={{
                  background: 'var(--surface)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  maxHeight: '260px',
                  overflowY: 'auto'
                }}>
                  <pre style={{
                    margin: 0,
                    fontSize: '11px',
                    lineHeight: '1.5',
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'var(--font-mono)'
                  }}>
                    {session.result || 'No output payload recorded.'}
                  </pre>
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function ExecutionTelemetryView({ theme, toggleTheme }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    fetch('/api/telemetry')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (!json.success) throw new Error(json.error || 'Failed parsing telemetry data');
        setData(json);
      })
      .catch((err) => {
        console.error(err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const stats = data?.stats || {};
  const agentBreakdown = data?.agentBreakdown || [];
  const sessions = data?.sessions || [];
  const isAvailable = data?.isAvailable ?? true;

  const filteredSessions = useMemo(() => {
    if (filter === 'success') return sessions.filter((s) => Number(s.success) === 1);
    if (filter === 'failed') return sessions.filter((s) => Number(s.success) === 0);
    return sessions;
  }, [sessions, filter]);

  if (loading) {
    return <main className="center-state">Loading telemetry ledger...</main>;
  }

  if (error) {
    return (
      <main className="center-state">
        <span className="text-missed font-medium">Failed to load telemetry store: {error}</span>
      </main>
    );
  }

  if (!isAvailable) {
    return (
      <div className="content-container">
        <header className="page-header">
          <div>
            <div className="breadcrumb">NEXUS / System Operations</div>
            <h1 className="page-title">Execution Telemetry</h1>
          </div>
        </header>
        <div className="eval-pane" style={{ padding: '36px 24px', textAlign: 'center', margin: '40px 0' }}>
          <span className="status-pill status-missed status-sm font-mono" style={{ margin: '0 auto 12px' }}>
            <span>NO DATABASE FOUND</span>
          </span>
          <h3 style={{ fontSize: '15px', color: 'var(--text-primary)', marginBottom: '8px' }}>
            nexus_sessions.db Unavailable
          </h3>
          <p className="text-secondary" style={{ fontSize: '13px', maxWidth: '480px', margin: '0 auto' }}>
            The SQLite database file has not been initialized yet. Run a brief or review locally via Python to generate initial session logs.
          </p>
        </div>
      </div>
    );
  }

  const successCount = sessions.filter((s) => Number(s.success) === 1).length;
  const failedCount = sessions.filter((s) => Number(s.success) === 0).length;

  return (
    <div className="content-container">
      {/* Page Header (Exact baseline layout) */}
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS / System Operations</div>
          <h1 className="page-title">Execution Telemetry &amp; Agent Health</h1>
        </div>
        <div className="header-actions">
          <div className="market-status-chip">
            <span>SQLITE LEDGER</span>
          </div>
          <div className="live-badge">
            <span className="live-dot" />
            <span>Pipeline Telemetry</span>
          </div>
          <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            ) : (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* Structured System Context Bar */}
      <div className="system-context-strip">
        <div className="context-item">
          <span className="context-label font-mono">PIPELINE STATUS</span>
          <div className="context-value">
            <span className="live-dot" style={{ width: 6, height: 6 }} />
            <span>Engine Active</span>
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">SUCCESS RATE</span>
          <div className="context-value font-mono font-semibold text-matched">
            {stats.successRate}%
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">TOTAL INVOCATIONS</span>
          <div className="context-value font-mono font-medium">
            {stats.totalRuns} Runs
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">AVG PIPELINE LATENCY</span>
          <div className="context-value font-mono font-medium">
            {formatDuration(stats.avgDurationMs)}
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">STORAGE REPLICA</span>
          <div className="context-value font-mono text-matched">
            nexus_sessions.db
          </div>
        </div>
      </div>

      {/* 01 · KPI Header */}
      <div className="section-eyebrow font-mono">01 · PIPELINE RELIABILITY &amp; RUNTIME PERFORMANCE</div>
      <section className="kpi-row">
        {/* Card 1: Pipeline Success Rate */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Pipeline Success Rate</span>
            <span className="kpi-target-tag font-mono">Reliability</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched">{stats.successRate}%</div>
            <span className="kpi-tag-visual font-mono text-xs">
              {stats.successfulRuns} / {stats.totalRuns} Runs
            </span>
          </div>
          <div className="kpi-context">
            <span>{stats.failedRuns === 0 ? 'Zero unhandled pipeline crashes' : `${stats.failedRuns} execution failures logged`}</span>
            <div className="kpi-mini-bar">
              <div
                className="kpi-mini-fill"
                style={{ width: `${Math.min(100, Math.max(0, Number(stats.successRate) || 0))}%` }}
              />
            </div>
          </div>
        </div>

        {/* Card 2: Total Orchestrations */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Total Invocations</span>
            <span className="kpi-target-tag font-mono">Ledger Store</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{stats.totalRuns}</div>
            <span className="kpi-tag-visual font-mono text-xs">
              {stats.runsToday} Today
            </span>
          </div>
          <div className="kpi-context">
            <span>Recorded in local SQLite session database</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '100%' }} />
            </div>
          </div>
        </div>

        {/* Card 3: Mean Pipeline Latency */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Mean Pipeline Latency</span>
            <span className="kpi-target-tag font-mono">End-to-End</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{formatDuration(stats.avgDurationMs)}</div>
            <span className="kpi-tag-visual font-mono text-xs">
              LLM + Tools
            </span>
          </div>
          <div className="kpi-context">
            <span>Averaged across multi-turn agent runs</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '85%' }} />
            </div>
          </div>
        </div>

        {/* Card 4: Database Storage Engine */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Storage Engine</span>
            <span className="kpi-target-tag font-mono">Local Replica</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched" style={{ fontSize: '18px', paddingTop: '6px' }}>
              ONLINE
            </div>
            <span className="kpi-tag-visual font-mono text-xs text-matched">WAL Mode</span>
          </div>
          <div className="kpi-context">
            <span>Read-only queries to nexus_sessions.db</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '100%' }} />
            </div>
          </div>
        </div>
      </section>

      {/* 02 · Twin Panes: Agent Breakdown & Execution Flow */}
      <div className="section-eyebrow font-mono">02 · DETERMINISTIC AGENT PERFORMANCE &amp; ORCHESTRATION TOPOLOGY</div>
      <section className="eval-section">
        <header className="eval-header">
          <div className="eval-header-title">Agent Telemetry &amp; Pipeline Execution State Machine</div>
          <div className="eval-header-right">
            <div className="eval-date-badge font-mono">Deterministic SQL</div>
          </div>
        </header>

        <div className="eval-body">
          {/* Left Column: Deterministic Agent Breakdown Table */}
          <div className="eval-column-left">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Deterministic Agent Performance</span>
                  <span className="eval-section-tag font-mono">SQL Aggregates</span>
                </div>
                <span className="eval-section-tag font-mono">{agentBreakdown.length} Active Agents</span>
              </div>
              <div className="eval-pane-body" style={{ padding: '0' }}>
                <table className="eval-table" style={{ width: '100%' }}>
                  <thead>
                    <tr>
                      <th style={{ paddingLeft: '16px' }}>Agent</th>
                      <th>Calls</th>
                      <th>Mean Duration</th>
                      <th>Success Rate</th>
                      <th>Errors</th>
                      <th style={{ paddingRight: '16px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agentBreakdown.map((ag) => (
                      <tr key={ag.agent} className="table-row">
                        <td style={{ paddingLeft: '16px' }} className="font-mono font-medium text-primary">
                          {ag.agent}
                        </td>
                        <td className="font-mono text-xs">{ag.total_calls}</td>
                        <td className="font-mono text-xs">{formatDuration(ag.avg_duration_ms)}</td>
                        <td className="font-mono text-xs text-matched font-bold">
                          {ag.success_rate_pct}%
                        </td>
                        <td className="font-mono text-xs">
                          <span className={ag.error_count > 0 ? 'text-missed font-bold' : 'text-secondary'}>
                            {ag.error_count}
                          </span>
                        </td>
                        <td style={{ paddingRight: '16px' }}>
                          <span className="status-pill status-matched status-sm font-mono">
                            <span className="status-indicator-dot" />
                            <span>HEALTHY</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                    {agentBreakdown.length === 0 && (
                      <tr>
                        <td colSpan="6" className="text-secondary" style={{ textAlign: 'center', padding: '24px 0' }}>
                          No agent breakdown records available.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Right Column: Execution Topology */}
          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Pipeline Architecture &amp; Telemetry Flow</span>
                  <span className="eval-section-tag font-mono">Multi-Stage</span>
                </div>
                <span className="eval-section-tag font-mono">State Machine</span>
              </div>
              <div className="eval-pane-body" style={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ background: 'var(--surface)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div className="font-mono text-xs font-bold text-primary" style={{ marginBottom: '2px' }}>
                      1. Scheduled Morning Brief (06:55 WIB)
                    </div>
                    <p className="text-secondary text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
                      GitHub Actions cron fires Python runner. Ingests macro feeds via Tavily + yfinance commodity contracts.
                    </p>
                  </div>
                  <div style={{ background: 'var(--surface)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div className="font-mono text-xs font-bold text-primary" style={{ marginBottom: '2px' }}>
                      2. Deterministic Economics Engine &amp; Validator
                    </div>
                    <p className="text-secondary text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
                      Hardcoded commodity-to-sector rules calculate deterministic impact. Output validator cross-verifies ticker mentions.
                    </p>
                  </div>
                  <div style={{ background: 'var(--surface)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                    <div className="font-mono text-xs font-bold text-primary" style={{ marginBottom: '2px' }}>
                      3. Evening Review &amp; Closed-Loop RCA (18:55 WIB)
                    </div>
                    <p className="text-secondary text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
                      Post-market evaluation records actual closes, calculates sector hit rates, logs root cause analysis into Obsidian.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 03 · Table Card: Session Ledger */}
      <div className="section-eyebrow font-mono">03 · HISTORICAL EXECUTION LEDGER</div>
      <section className="table-card">
        <header className="table-card-header">
          <div className="table-card-title">
            <span>Execution Ledger (nexus_sessions.db)</span>
            <span className="table-card-count font-mono">{filteredSessions.length} Recorded Runs</span>
          </div>
          <div className="table-filter-tabs font-mono">
            <button
              className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({sessions.length})
            </button>
            <button
              className={`filter-tab ${filter === 'success' ? 'active' : ''}`}
              onClick={() => setFilter('success')}
            >
              Success ({successCount})
            </button>
            <button
              className={`filter-tab ${filter === 'failed' ? 'active' : ''}`}
              onClick={() => setFilter('failed')}
            >
              Failed ({failedCount})
            </button>
          </div>
        </header>

        <div className="eval-table-wrap">
          <table className="eval-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Timestamp</th>
                <th>Agent</th>
                <th>Model</th>
                <th>Task / Query</th>
                <th>Latency</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.map((session) => (
                <SessionRow
                  key={session.id}
                  session={session}
                  expanded={expandedId === session.id}
                  onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)}
                />
              ))}
              {filteredSessions.length === 0 && (
                <tr>
                  <td colSpan="7" className="text-muted" style={{ textAlign: 'center', padding: '28px 0' }}>
                    No sessions match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
