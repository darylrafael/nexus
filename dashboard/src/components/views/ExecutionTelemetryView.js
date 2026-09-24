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
                  style={{ padding: '4px 10px', fontSize: '11px' }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeepInspect(session);
                  }}
                >
                  Deep Inspection (Payload &amp; Trace) ↗
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// Multi-Agent Architecture Directory Data
const AGENT_CATALOG = [
  {
    name: 'market_agent',
    role: 'Executive Market Synthesis',
    layer: 'Orchestration & LLM Synthesis',
    model: 'OpenRouter (gpt-oss-120b)',
    latency: '115.8s',
    status: 'HEALTHY',
    desc: 'Coordinates morning brief flow, aggregates inputs, formulates directional IHSG thesis.'
  },
  {
    name: 'commodity_agent',
    role: 'Global Commodity Tapes',
    layer: 'Real-time Contract Ingestion',
    model: 'yfinance + Web Fallback',
    latency: '~1.2s',
    status: 'ACTIVE',
    desc: 'Ingests quotes for Brent Oil, Coal, CPO, Gold, Nickel, Tin, Copper, and Natural Gas.'
  },
  {
    name: 'web_agent',
    role: 'Macroeconomic News Radar',
    layer: 'Live News Discovery',
    model: 'Tavily Search API',
    latency: '~2.4s',
    status: 'ACTIVE',
    desc: 'Crawls Bank Indonesia announcements, Fed outlooks, and domestic financial news wires.'
  },
  {
    name: 'economics_engine',
    role: 'Deterministic Sector Impact',
    layer: 'Pure Rule-Based Logic',
    model: 'Zero-LLM Hardcoded Engine',
    latency: '<1ms',
    status: 'ACTIVE',
    desc: 'Determines sector directions purely from commodity moves to guarantee zero hallucination.'
  },
  {
    name: 'validator',
    role: 'Output Integrity & Sanity',
    layer: 'Post-LLM Cross-Check',
    model: 'Deterministic AST & Regex',
    latency: '~5ms',
    status: 'ACTIVE',
    desc: 'Enforces directional language consistency and verifies valid Indonesian stock tickers.'
  },
  {
    name: 'evening_reviewer',
    role: 'Closed-Loop RCA & Reflection',
    layer: 'Post-Market Evaluation',
    model: 'OpenRouter + Obsidian API',
    latency: '~85s',
    status: 'STANDBY',
    desc: 'Evaluates closing prices at 18:55 WIB, attributes errors, and injects lessons into memory.'
  }
];

export default function ExecutionTelemetryView({ theme, toggleTheme }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);

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
            <div className="breadcrumb">NEXUS / Execution Telemetry</div>
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
      {/* Page Header */}
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS / Execution Telemetry</div>
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
            <span>Autonomous Engine Active</span>
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
            {stats.totalRuns} Recorded
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
            nexus_sessions.db (WAL)
          </div>
        </div>
      </div>

      {/* 01 · KPI Header */}
      <div className="section-eyebrow font-mono">
        <span className="console-prompt">//</span> 01 · PIPELINE RELIABILITY &amp; RUNTIME PERFORMANCE
      </div>
      <section className="kpi-row">
        {/* Card 1: Pipeline Success Rate */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Pipeline Success Rate</span>
            <span className="kpi-target-tag font-mono">Critical Path</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched">{stats.successRate}%</div>
            <div className="outcome-pips font-mono">
              {sessions.slice(0, 8).map((s) => (
                <span
                  key={s.id}
                  className={`outcome-pip ${Number(s.success) === 1 ? 'pip-hit' : 'pip-miss'}`}
                  title={`Run #${s.id}: ${Number(s.success) === 1 ? 'Completed' : 'Error'}`}
                >
                  {Number(s.success) === 1 ? '● Pass' : '▲ Fail'}
                </span>
              ))}
            </div>
          </div>
          <div className="kpi-context">
            <span>{stats.successfulRuns} of {stats.totalRuns} runs completed without crash</span>
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
            <span className="kpi-target-tag font-mono">Session Ledger</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{stats.totalRuns} Runs</div>
            <span className="kpi-tag-visual font-mono text-xs">
              {stats.runsToday} Today
            </span>
          </div>
          <div className="kpi-context">
            <span>Indexed in local SQLite session database</span>
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
              LLM + Tool Calling
            </span>
          </div>
          <div className="kpi-context">
            <span>Averaged across multi-turn synthesis turns</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '75%' }} />
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
            <div className="kpi-value font-mono text-matched" style={{ fontSize: '24px', paddingTop: '4px' }}>
              ONLINE
            </div>
            <span className="kpi-tag-visual font-mono text-xs text-matched">
              <span className="live-dot" style={{ width: 5, height: 5 }} /> WAL Mode
            </span>
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
      <div className="section-eyebrow font-mono">
        <span className="console-prompt">//</span> 02 · MULTI-AGENT ARCHITECTURE &amp; EXECUTION STATE MACHINE
      </div>
      <section className="eval-section">
        <header className="eval-header">
          <div className="eval-header-title">
            Multi-Agent Topology &amp; Runtime State Machine
          </div>
          <div className="eval-header-right">
            <div className="eval-date-badge font-mono">Deterministic State</div>
          </div>
        </header>

        <div className="eval-body">
          {/* Left Column: Full Multi-Agent Directory Table */}
          <div className="eval-pane">
            <div className="eval-pane-header">
              <div className="eval-pane-header-left">
                <span className="eval-pane-title">Sub-Agent Operational Matrix</span>
                <span className="eval-section-tag font-mono">6 Pipeline Modules</span>
              </div>
              <span className="eval-section-tag font-mono">Orchestrator v2.4</span>
            </div>
            <div className="eval-pane-body" style={{ padding: 0 }}>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Module / Agent</th>
                      <th>Operational Role</th>
                      <th>Architecture Layer</th>
                      <th>Latency</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {AGENT_CATALOG.map((ag) => (
                      <tr key={ag.name} className="table-row">
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span className="font-mono text-xs font-bold text-primary">
                              {ag.name}
                            </span>
                            <span className="font-mono text-tertiary" style={{ fontSize: '10px' }}>
                              {ag.model}
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="font-medium text-xs text-primary">
                            {ag.role}
                          </span>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-secondary">
                            {ag.layer}
                          </span>
                        </td>
                        <td className="font-mono text-xs font-semibold">
                          {ag.latency}
                        </td>
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

          {/* Right Column: Execution Topology & Cadence */}
          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Automated Pipeline Cadence &amp; Resilience</span>
                  <span className="eval-section-tag font-mono">Autonomous Daemon</span>
                </div>
                <div className="loop-active-tag font-mono">
                  <span className="live-dot" style={{ width: 6, height: 6 }} />
                  Cron Active
                </div>
              </div>

              <div className="eval-pane-body" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Stage 1: Morning Brief */}
                <div className="macro-tape-strip" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', padding: 0, border: 'none', background: 'transparent' }}>
                  <div className="macro-strip-cell" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)' }}>
                    <div className="macro-cell-head font-mono">06:55 WIB CRON</div>
                    <div className="macro-cell-val font-mono" style={{ fontSize: '13px' }}>Morning Brief</div>
                    <div className="macro-cell-sub font-mono text-matched">● Automated Ingest</div>
                  </div>
                  <div className="macro-strip-cell" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)' }}>
                    <div className="macro-cell-head font-mono">16:00 WIB SETTLE</div>
                    <div className="macro-cell-val font-mono" style={{ fontSize: '13px' }}>IDX Close</div>
                    <div className="macro-cell-sub font-mono text-secondary">Exchange Official</div>
                  </div>
                  <div className="macro-strip-cell" style={{ background: 'var(--surface-subtle)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)' }}>
                    <div className="macro-cell-head font-mono">18:55 WIB CRON</div>
                    <div className="macro-cell-val font-mono" style={{ fontSize: '13px' }}>Evening Review</div>
                    <div className="macro-cell-sub font-mono text-matched">● Closed-Loop RCA</div>
                  </div>
                </div>

                {/* Infrastructure Terminal Block */}
                <div className="rca-memory-terminal-block">
                  <div className="memory-prefix font-mono">
                    <span className="memory-title">INFRASTRUCTURE &amp; RUNTIME TOPOLOGY</span>
                    <span className="memory-injected-pill font-mono">HIGH-AVAILABILITY</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', marginTop: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '4px' }}>
                      <span className="font-mono text-tertiary">PRIMARY LLM ENGINE:</span>
                      <span className="font-mono font-bold text-primary">OpenRouter (gpt-oss-120b)</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '4px' }}>
                      <span className="font-mono text-tertiary">FAILOVER ENGINE:</span>
                      <span className="font-mono font-bold text-matched">Gemini 2.5 Pro Fallback</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--border-subtle)', paddingBottom: '4px' }}>
                      <span className="font-mono text-tertiary">PERSISTENT KNOWLEDGE:</span>
                      <span className="font-mono font-bold text-primary">Obsidian Local REST (:27124)</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span className="font-mono text-tertiary">DELIVERY DISPATCH:</span>
                      <span className="font-mono font-bold text-primary">Telegram Bot API (Broadcaster)</span>
                    </div>
                  </div>
                  <div className="rca-lesson-meta font-mono">
                    <span>HOST: Local Daemon / GitHub Actions Workflow</span>
                    <span>PORT: 3002 (Web Telemetry)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 03 · Compact Historical Execution Ledger */}
      <div className="section-eyebrow font-mono">
        <span className="console-prompt">//</span> 03 · HISTORICAL EXECUTION LEDGER
      </div>
      <section className="history-section">
        <header className="history-header">
          <div>
            <h2 className="history-title">Historical Execution Ledger</h2>
            <div className="history-subtitle font-mono text-xs">
              Chronological SQLite transaction log of autonomous pipeline runs (click row to inspect compact summary)
            </div>
          </div>
          <div className="filter-tabs">
            <button
              className={`filter-tab-btn font-mono ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({sessions.length})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'success' ? 'active' : ''}`}
              onClick={() => setFilter('success')}
            >
              Success ({successCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'failed' ? 'active' : ''}`}
              onClick={() => setFilter('failed')}
            >
              Failed ({failedCount})
            </button>
          </div>
        </header>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '100px' }}>Run ID</th>
                <th style={{ width: '180px' }}>Timestamp</th>
                <th>Agent Name</th>
                <th style={{ width: '130px' }}>Wall Latency</th>
                <th style={{ width: '130px' }}>Execution Verdict</th>
              </tr>
            </thead>
            <tbody>
              {filteredSessions.map((session) => (
                <CompactSessionRow
                  key={session.id}
                  session={session}
                  expanded={expandedId === session.id}
                  onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)}
                  onDeepInspect={(run) => setSelectedRun(run)}
                />
              ))}
              {filteredSessions.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '32px 0' }}>
                    No execution sessions match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Level 3: Deep Inspection SideSheet for Run Audit */}
      <RunDetailDrawer
        isOpen={!!selectedRun}
        onClose={() => setSelectedRun(null)}
        run={selectedRun}
      />
    </div>
  );
}
