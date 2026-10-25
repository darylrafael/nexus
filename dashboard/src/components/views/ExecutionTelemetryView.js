'use client';
import { useState, useEffect, useMemo } from 'react';
import RunDetailDrawer from '../execution-telemetry/RunDetailDrawer';

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

function CompactSessionRow({ session, expanded, onToggle, onDeepInspect }) {
  const isSuccess = Number(session.success) === 1;

  return (
    <>
      <tr
        className={`table-row ${expanded ? 'expanded' : ''}`}
        onClick={onToggle}
        style={{ cursor: 'pointer' }}
      >
        <td className="font-mono text-xs" style={{ width: '100px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <svg
              className={`chevron-icon ${expanded ? 'rotated' : ''}`}
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
            <span className="font-bold text-primary">#{session.id}</span>
          </div>
        </td>
        <td className="font-mono text-xs text-secondary" style={{ width: '180px' }}>
          {formatTimestamp(session.timestamp)}
        </td>
        <td>
          <span className="font-mono text-xs font-semibold text-primary">
            {session.agent}
          </span>
        </td>
        <td className="font-mono text-xs font-semibold" style={{ width: '130px' }}>
          {formatDuration(session.duration_ms)}
        </td>
        <td style={{ width: '130px' }}>
          <span className={`status-pill ${isSuccess ? 'status-matched' : 'status-missed'} status-sm font-mono`}>
            <span className="status-indicator-dot" />
            <span className="status-text">{isSuccess ? 'SUCCESS' : 'FAILED'}</span>
          </span>
        </td>
      </tr>
      {expanded && (
        <tr className="expanded-row">
          <td colSpan={5} style={{ padding: 0 }}>
            <div className="expanded-panel" style={{ padding: '12px 18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontSize: '12px' }}>
                  <div>
                    <span className="font-mono text-tertiary" style={{ marginRight: '6px' }}>TASK:</span>
                    <span className="font-mono font-bold text-primary">{session.query}</span>
                  </div>
                  <div>
                    <span className="font-mono text-tertiary" style={{ marginRight: '6px' }}>ENGINE:</span>
                    <span className="font-mono font-medium text-secondary">{session.model || 'llm_client'}</span>
                  </div>
                  <div>
                    <span className="font-mono text-tertiary" style={{ marginRight: '6px' }}>DURATION:</span>
                    <span className="font-mono font-medium text-primary">
                      {session.duration_ms ? `${session.duration_ms.toLocaleString()} ms` : '—'}
                    </span>
                  </div>
                </div>
                <button
                  className="brief-read-btn font-mono"
                  style={{ padding: '6px 12px', fontSize: '12px', minHeight: '36px', display: 'inline-flex', alignItems: 'center' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeepInspect(session);
                  }}
                >
                  Inspect Trace ↗
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

const AGENT_CATALOG = [
  {
    name: 'market_agent',
    role: 'Pre-Market Synthesis',
    layer: '06:55 WIB Orchestrator',
    model: 'OpenRouter (gpt-oss-120b)',
    latency: '~115s',
    status: 'HEALTHY',
    desc: 'Synthesizes macro, commodities, and past heuristics into the pre-market forecast.'
  },
  {
    name: 'commodity_agent',
    role: 'Commodity Tapes',
    layer: 'Market Data Feed',
    model: 'yfinance + Web Fallback',
    latency: '~1.2s',
    status: 'ACTIVE',
    desc: 'Fetches Brent, Coal, CPO, Gold, Nickel, Tin, Copper, and USD/IDR.'
  },
  {
    name: 'web_agent',
    role: 'Macro & IDX News',
    layer: 'Search Discovery',
    model: 'Tavily Search API',
    latency: '~2.4s',
    status: 'ACTIVE',
    desc: 'Crawls BI policy, global macro catalysts, and IDX sector closing reports.'
  },
  {
    name: 'economics_engine',
    role: 'Sector Transmission',
    layer: 'Deterministic Logic',
    model: 'Rule-Based Engine',
    latency: '<1ms',
    status: 'ACTIVE',
    desc: 'Maps commodity moves to IDX-IC sectors without LLM hallucination.'
  },
  {
    name: 'validator',
    role: 'Sanity & Ticker Gate',
    layer: 'Post-LLM Verification',
    model: 'Deterministic Regex',
    latency: '~5ms',
    status: 'ACTIVE',
    desc: 'Enforces directional consistency and validates IDX stock tickers.'
  },
  {
    name: 'evening_reviewer',
    role: 'Post-Market Audit & RCA',
    layer: '20:00 WIB Evaluation',
    model: 'OpenRouter + Hygiene Gate',
    latency: '~85s',
    status: 'STANDBY',
    desc: 'Grades calls against IDX closes, diagnoses variance, and filters lessons.'
  }
];

export default function ExecutionTelemetryView({ theme, toggleTheme }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);

  const PAGE_SIZE = 10;

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
  const sessions = useMemo(() => data?.sessions || [], [data?.sessions]);
  const isAvailable = data?.isAvailable ?? true;

  const filteredSessions = useMemo(() => {
    if (filter === 'success') return sessions.filter((s) => Number(s.success) === 1);
    if (filter === 'failed') return sessions.filter((s) => Number(s.success) === 0);
    return sessions;
  }, [sessions, filter]);

  const totalPages = Math.max(1, Math.ceil(filteredSessions.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginatedSessions = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return filteredSessions.slice(start, start + PAGE_SIZE);
  }, [filteredSessions, safePage]);

  if (loading) {
    return <main className="center-state">Loading execution telemetry...</main>;
  }

  if (error) {
    return (
      <main className="center-state">
        <span className="text-missed font-medium">Failed to load telemetry: {error}</span>
      </main>
    );
  }

  if (!isAvailable) {
    return (
      <div className="content-container">
        <header className="page-header">
          <div>
            <div className="breadcrumb">NEXUS · Execution Telemetry</div>
            <h1 className="page-title">Execution Telemetry</h1>
          </div>
        </header>
        <div className="eval-pane" style={{ padding: '36px 24px', textAlign: 'center', margin: '40px 0' }}>
          <span className="status-pill status-missed status-sm font-mono" style={{ margin: '0 auto 12px' }}>
            <span>NO TELEMETRY FOUND</span>
          </span>
          <p className="text-secondary" style={{ fontSize: '13px', maxWidth: '480px', margin: '0 auto' }}>
            No telemetry records available yet.
          </p>
        </div>
      </div>
    );
  }

  const successCount = sessions.filter((s) => Number(s.success) === 1).length;
  const failedCount = sessions.filter((s) => Number(s.success) === 0).length;

  return (
    <div className="content-container">
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS · Pipeline Telemetry</div>
          <h1 className="page-title">Agent Health &amp; Execution Log</h1>
        </div>
        <div className="header-actions">
          <div className="market-status-chip">
            <span>CRON: 06:55 / 20:00 WIB</span>
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

      <section className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Success Rate</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched">{stats.successRate}%</div>
          </div>
          <div className="kpi-context">
            <span>{stats.successfulRuns} / {stats.totalRuns} runs completed</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Total Runs</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{stats.totalRuns}</div>
          </div>
          <div className="kpi-context">
            <span>{stats.runsToday} executed today</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Mean Latency</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{formatDuration(stats.avgDurationMs)}</div>
          </div>
          <div className="kpi-context">
            <span>End-to-end synthesis &amp; crawl</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Artifact Store</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched" style={{ fontSize: '22px' }}>
              SYNCED
            </div>
          </div>
          <div className="kpi-context">
            <span>Canonical JSON + SQLite WAL</span>
          </div>
        </div>
      </section>

      <section className="eval-section">
        <header className="eval-header">
          <div className="eval-header-title">Multi-Agent Pipeline Modules</div>
        </header>

        <div className="eval-body">
          <div className="eval-pane">
            <div className="eval-pane-header">
              <div className="eval-pane-header-left">
                <span className="eval-pane-title">Agent Directory</span>
              </div>
              <span className="eval-section-tag font-mono">6 Modules</span>
            </div>
            <div className="eval-pane-body" style={{ padding: 0 }}>
              <div className="mobile-cards-list">
                {AGENT_CATALOG.map((ag) => (
                  <div key={ag.name} className="mobile-agent-card">
                    <div className="mobile-card-top">
                      <span className="font-mono font-bold text-xs text-primary">{ag.name}</span>
                      <span className={`status-pill ${ag.status === 'HEALTHY' || ag.status === 'ACTIVE' ? 'status-matched' : 'status-pending'} status-sm font-mono`}>
                        {ag.status}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {ag.role}
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                      {ag.desc}
                    </p>
                  </div>
                ))}
              </div>

              <div className="table-wrapper desktop-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Module</th>
                      <th>Role</th>
                      <th>Layer</th>
                      <th>Latency</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {AGENT_CATALOG.map((ag) => (
                      <tr key={ag.name} className="table-row">
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span className="font-mono text-xs font-bold text-primary">{ag.name}</span>
                            <span className="font-mono text-tertiary" style={{ fontSize: '11px' }}>{ag.model}</span>
                          </div>
                        </td>
                        <td>
                          <span className="font-medium text-xs text-primary">{ag.role}</span>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-secondary">{ag.layer}</span>
                        </td>
                        <td className="font-mono text-xs font-semibold">{ag.latency}</td>
                        <td>
                          <span className={`status-pill ${ag.status === 'HEALTHY' || ag.status === 'ACTIVE' ? 'status-matched' : 'status-pending'} status-sm font-mono`}>
                            <span className="status-indicator-dot" />
                            <span className="status-text">{ag.status}</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Schedule &amp; Failover Topology</span>
                </div>
                <div className="loop-active-tag font-mono">
                  <span className="live-dot" style={{ width: 6, height: 6 }} />
                  Active
                </div>
              </div>

              <div className="eval-pane-body" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div className="telemetry-cadence-grid">
                  <div className="macro-strip-cell" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)' }}>
                    <div className="macro-cell-head font-mono">06:55 WIB</div>
                    <div className="macro-cell-val font-mono" style={{ fontSize: '13px' }}>Morning Brief</div>
                    <div className="macro-cell-sub font-mono text-matched">● Pre-Market Lock</div>
                  </div>
                  <div className="macro-strip-cell" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)' }}>
                    <div className="macro-cell-head font-mono">16:00 WIB</div>
                    <div className="macro-cell-val font-mono" style={{ fontSize: '13px' }}>IDX Close</div>
                    <div className="macro-cell-sub font-mono text-secondary">Official Tape</div>
                  </div>
                  <div className="macro-strip-cell" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)' }}>
                    <div className="macro-cell-head font-mono">20:00 WIB</div>
                    <div className="macro-cell-val font-mono" style={{ fontSize: '13px' }}>Evening Audit</div>
                    <div className="macro-cell-sub font-mono text-matched">● Score &amp; RCA</div>
                  </div>
                </div>

                <div className="rca-memory-terminal-block">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '4px' }}>
                      <span className="font-mono text-tertiary">PRIMARY LLM:</span>
                      <span className="font-mono font-bold text-primary">OpenRouter (gpt-oss-120b)</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '4px' }}>
                      <span className="font-mono text-tertiary">FAILOVER:</span>
                      <span className="font-mono font-bold text-matched">Gemini Fallback</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '4px' }}>
                      <span className="font-mono text-tertiary">MEMORY STORE:</span>
                      <span className="font-mono font-bold text-primary">Git Artifact Vault</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span className="font-mono text-tertiary">DISPATCH:</span>
                      <span className="font-mono font-bold text-primary">Telegram Bot + Web Dashboard</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="history-section">
        <header className="history-header">
          <div>
            <h2 className="history-title">Execution Log ({sessions.length})</h2>
          </div>
          <div className="filter-tabs">
            <button
              className={`filter-tab-btn font-mono ${filter === 'all' ? 'active' : ''}`}
              onClick={() => { setFilter('all'); setPage(1); }}
            >
              All ({sessions.length})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'success' ? 'active' : ''}`}
              onClick={() => { setFilter('success'); setPage(1); }}
            >
              Success ({successCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'failed' ? 'active' : ''}`}
              onClick={() => { setFilter('failed'); setPage(1); }}
            >
              Failed ({failedCount})
            </button>
          </div>
        </header>

        <div className="mobile-cards-list">
          {paginatedSessions.map((session) => {
            const isSuccess = Number(session.success) === 1;
            const isExpanded = expandedId === session.id;
            return (
              <div
                key={session.id}
                className="mobile-session-card"
                onClick={() => setExpandedId(isExpanded ? null : session.id)}
              >
                <div className="mobile-card-top">
                  <span className="font-mono font-bold text-xs text-primary">#{session.id}</span>
                  <span className="font-mono text-xs text-secondary">{formatTimestamp(session.timestamp)}</span>
                  <span className={`status-pill ${isSuccess ? 'status-matched' : 'status-missed'} status-sm font-mono`}>
                    {isSuccess ? 'PASS' : 'FAIL'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="font-mono font-bold text-xs text-primary">{session.agent}</span>
                  <span className="font-mono text-xs text-secondary font-semibold">{formatDuration(session.duration_ms)}</span>
                </div>
                {isExpanded && (
                  <div style={{ borderTop: '1px dashed var(--border-subtle)', paddingTop: '8px', marginTop: '4px' }}>
                    <button
                      className="brief-read-btn font-mono"
                      style={{ padding: '6px 12px', fontSize: '12px', minHeight: '36px', width: '100%', justifyContent: 'center', display: 'inline-flex', alignItems: 'center' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedRun(session);
                      }}
                    >
                      Inspect Trace ↗
                    </button>
                  </div>
                )}
              </div>
            );
          })}
          {paginatedSessions.length === 0 && (
            <div className="text-muted font-mono text-xs text-center py-4">
              No execution sessions match the selected filter.
            </div>
          )}
        </div>

        <div className="table-wrapper desktop-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '100px' }}>Run ID</th>
                <th style={{ width: '180px' }}>Timestamp</th>
                <th>Agent</th>
                <th style={{ width: '130px' }}>Duration</th>
                <th style={{ width: '130px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {paginatedSessions.map((session) => (
                <CompactSessionRow
                  key={session.id}
                  session={session}
                  expanded={expandedId === session.id}
                  onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)}
                  onDeepInspect={(run) => setSelectedRun(run)}
                />
              ))}
              {paginatedSessions.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '32px 0' }}>
                    No execution sessions match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {filteredSessions.length > PAGE_SIZE && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '12px 16px',
              borderTop: '1px solid var(--border-subtle)',
              background: 'var(--surface-subtle)',
              flexWrap: 'wrap',
              gap: '10px',
            }}
          >
            <span className="font-mono text-xs text-secondary">
              Showing {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filteredSessions.length)} of {filteredSessions.length} runs
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                className="filter-tab-btn font-mono"
                disabled={safePage <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{ opacity: safePage <= 1 ? 0.45 : 1, cursor: safePage <= 1 ? 'default' : 'pointer' }}
              >
                ← Prev
              </button>
              <span className="font-mono text-xs text-primary" style={{ padding: '0 8px' }}>
                Page {safePage} of {totalPages}
              </span>
              <button
                type="button"
                className="filter-tab-btn font-mono"
                disabled={safePage >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{ opacity: safePage >= totalPages ? 0.45 : 1, cursor: safePage >= totalPages ? 'default' : 'pointer' }}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </section>

      <RunDetailDrawer
        isOpen={!!selectedRun}
        onClose={() => setSelectedRun(null)}
        run={selectedRun}
      />
    </div>
  );
}
