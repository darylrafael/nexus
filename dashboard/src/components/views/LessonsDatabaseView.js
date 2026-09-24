'use client';
import { useState, useEffect, useMemo } from 'react';
import SideSheet from '../common/SideSheet';
import EvidenceDrawer from '../memory-heuristics/EvidenceDrawer';
import { HeuristicStatusBadge } from '../common/Badges';

function formatPct(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
}

function CompactHeuristicRow({ item, onInspect }) {
  const isUp = item.validationRate >= 50;

  return (
    <tr 
      className="table-row"
      onClick={() => onInspect(item)}
      style={{ cursor: 'pointer' }}
    >
      <td className="font-mono font-bold text-xs" style={{ width: '90px' }}>
        <span className="text-primary">{item.id}</span>
      </td>
      <td style={{ width: '140px' }}>
        <span className="font-mono text-xs text-secondary font-medium">
          {item.category}
        </span>
      </td>
      <td style={{ maxWidth: '440px', padding: '10px 14px' }}>
        <span 
          className="font-medium text-xs leading-normal text-primary"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
          title={item.rule}
        >
          “{item.rule}”
        </span>
      </td>
      <td className="font-mono text-xs" style={{ width: '80px' }}>
        {item.observed} {item.observed === 1 ? 'run' : 'runs'}
      </td>
      <td className="font-mono text-xs text-matched font-bold" style={{ width: '70px' }}>
        {item.validated}
      </td>
      <td className="font-mono text-xs text-missed font-bold" style={{ width: '70px' }}>
        {item.contradicted}
      </td>
      <td style={{ width: '100px' }}>
        <div className="delta-cell font-mono">
          <span className={isUp ? 'text-matched font-bold' : 'text-missed font-bold'}>
            {item.validationRate !== null ? `${item.validationRate}%` : 'Unresolved'}
          </span>
        </div>
      </td>
      <td style={{ width: '90px' }}>
        <span className={`status-pill ${item.status === 'ACTIVE' ? 'status-matched' : 'status-missed'} status-sm font-mono`}>
          <span className="status-indicator-dot" />
          <span>{item.status}</span>
        </span>
      </td>
      <td style={{ width: '130px', textAlign: 'right' }}>
        <button
          className="brief-read-btn font-mono"
          style={{ padding: '3px 8px', fontSize: '10px' }}
          onClick={(e) => {
            e.stopPropagation();
            onInspect(item);
          }}
        >
          Deep Inspect ↗
        </button>
      </td>
    </tr>
  );
}

export default function LessonsDatabaseView({ theme, toggleTheme }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [selectedHeuristic, setSelectedHeuristic] = useState(null);
  const [showPromptDrawer, setShowPromptDrawer] = useState(false);

  useEffect(() => {
    fetch('/api/memory')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (!json.success) throw new Error(json.error || 'Failed parsing memory data');
        setData(json);
      })
      .catch((err) => {
        console.error(err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  const stats = data?.stats || {};
  const heuristics = data?.heuristics || [];
  const blindSpots = data?.blindSpots || [];

  const filteredHeuristics = useMemo(() => {
    if (filter === 'active') return heuristics.filter((h) => h.status === 'ACTIVE');
    if (filter === 'superseded') return heuristics.filter((h) => h.status !== 'ACTIVE');
    return heuristics;
  }, [heuristics, filter]);

  if (loading) {
    return <main className="center-state">Loading lessons &amp; heuristics database...</main>;
  }

  if (error) {
    return (
      <main className="center-state">
        <span className="text-missed font-medium">Failed to load memory store: {error}</span>
      </main>
    );
  }

  const maxBlindSpotCount = Math.max(...blindSpots.map((b) => b.count), 1);
  const activeCount = heuristics.filter((h) => h.status === 'ACTIVE').length;
  const supersededCount = heuristics.filter((h) => h.status !== 'ACTIVE').length;

  return (
    <div className="content-container">
      {/* Page Header */}
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS / Memory &amp; Heuristics</div>
          <h1 className="page-title">Heuristics &amp; Lessons Database</h1>
        </div>
        <div className="header-actions">
          <div className="market-status-chip">
            <span>CLOSED-LOOP RCA</span>
          </div>
          <div className="live-badge">
            <span className="live-dot" />
            <span>Memory Sync</span>
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
          <span className="context-label font-mono">MEMORY STATUS</span>
          <div className="context-value">
            <span className="live-dot" style={{ width: 6, height: 6 }} />
            <span>Closed-Loop Active</span>
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">TOTAL RULES</span>
          <div className="context-value font-mono font-medium">{stats.totalLessons || 0} Lessons</div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">ACTIVE IN PROMPT</span>
          <div className="context-value font-mono font-semibold text-matched">
            {stats.activeHeuristics || 0} Validated
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">BLIND SPOTS</span>
          <div className="context-value font-mono font-medium text-warning">
            {stats.blindSpotsCount || 0} Factors Tracked
          </div>
        </div>
        <div className="context-divider" />
        <div className="context-item">
          <span className="context-label font-mono">HEURISTIC STORE</span>
          <div className="context-value font-mono text-matched">
            Obsidian :27124
          </div>
        </div>
      </div>

      {/* 01 · KPI Header */}
      <div className="section-eyebrow font-mono">
        <span className="console-prompt">//</span> 01 · AUTONOMOUS REFLECTION &amp; KNOWLEDGE OVERVIEW
      </div>
      <section className="kpi-row">
        {/* Card 1: Total Lessons */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Total Lessons</span>
            <span className="kpi-target-tag font-mono">Knowledge Base</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{stats.totalLessons || 0}</div>
            <span className="kpi-tag-visual font-mono text-xs">Accumulated</span>
          </div>
          <div className="kpi-context">
            <span>Formulated across historical evening reviews</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '100%' }} />
            </div>
          </div>
        </div>

        {/* Card 2: Active Heuristics */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Active Heuristics</span>
            <span className="kpi-target-tag font-mono">Constraining</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched">{stats.activeHeuristics || 0}</div>
            <span className="kpi-tag-visual font-mono text-xs">
              {stats.supersededHeuristics || 0} Superseded
            </span>
          </div>
          <div className="kpi-context">
            <span>Validated rules actively injected into morning brief</span>
            <div className="kpi-mini-bar">
              <div
                className="kpi-mini-fill"
                style={{
                  width: `${stats.totalLessons > 0 ? (stats.activeHeuristics / stats.totalLessons) * 100 : 50}%`
                }}
              />
            </div>
          </div>
        </div>

        {/* Card 3: Recurring Blind Spots */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Blind Spots</span>
            <span className="kpi-target-tag font-mono">Error Catalysts</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-warning">{stats.blindSpotsCount || 0}</div>
            <span className="kpi-tag-visual font-mono text-xs">Monitored</span>
          </div>
          <div className="kpi-context">
            <span>Macro shock factors with repeated forecasting misses</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '65%' }} />
            </div>
          </div>
        </div>

        {/* Card 4: Last Learning Cycle */}
        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Last Learning Run</span>
            <span className="kpi-target-tag font-mono">Obsidian Sync</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-base" style={{ fontSize: '18px', paddingTop: '6px' }}>
              {stats.lastCycle || '2026-09-23'}
            </div>
            <span className="kpi-tag-visual font-mono text-xs text-matched">Synced</span>
          </div>
          <div className="kpi-context">
            <span>Post-market evaluation cycle timestamp</span>
            <div className="kpi-mini-bar">
              <div className="kpi-mini-fill" style={{ width: '100%' }} />
            </div>
          </div>
        </div>
      </section>

      {/* 02 · Twin Panes: Blind Spots & Operational Logic */}
      <div className="section-eyebrow font-mono">
        <span className="console-prompt">//</span> 02 · RECURRING FACTOR ATTRIBUTION &amp; SELF-CORRECTION
      </div>
      <section className="eval-section">
        <header className="eval-header">
          <div className="eval-header-title">Macro Risk Factor Attribution &amp; Prompt Ingestion</div>
          <div className="eval-header-right">
            <div className="eval-date-badge font-mono">Closed-Loop Memory</div>
          </div>
        </header>

        <div className="eval-body">
          {/* Left Column: Recurring Blind Spots Frequency Bar */}
          <div className="eval-column-left">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Recurring Macro Blind Spots</span>
                  <span className="eval-section-tag font-mono">Attribution Frequency</span>
                </div>
                <span className="eval-section-tag font-mono">{blindSpots.length} Factors</span>
              </div>
              <div className="eval-pane-body" style={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  {blindSpots.map((item, idx) => {
                    const pct = Math.min(100, Math.max(15, (item.count / maxBlindSpotCount) * 100));
                    return (
                      <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                          <span className="font-mono text-primary font-medium">{item.name}</span>
                          <span className="font-mono text-warning font-semibold">{item.count} {item.count === 1 ? 'hit' : 'hits'}</span>
                        </div>
                        <div style={{ height: '4px', width: '100%', background: 'var(--surface-well)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--warning-text)', borderRadius: '2px' }} />
                        </div>
                      </div>
                    );
                  })}
                  {blindSpots.length === 0 && (
                    <p className="rca-content-muted font-mono text-xs">No recurring blind spots identified yet.</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Minimized Prompt Constraint Injection Section */}
          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Closed-Loop Prompt Constraint Injection</span>
                  <span className="eval-section-tag font-mono">Dynamic Prompt</span>
                </div>
                <div className="loop-active-tag font-mono">
                  <span className="live-dot" style={{ width: 6, height: 6 }} />
                  Loop Active
                </div>
              </div>
              <div className="eval-pane-body" style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {/* Minimized Compact Summary Card */}
                <div style={{ background: 'var(--surface-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="font-mono text-xs font-bold text-primary">
                      {activeCount} Active Constraints Injected
                    </span>
                    <span className="font-mono text-xs text-matched font-semibold">
                      Cap: Top 5 Rules
                    </span>
                  </div>
                  <p className="text-secondary text-xs" style={{ margin: 0, lineHeight: 1.45 }}>
                    Validated rules from post-market reviews are injected as prompt constraints into the 07:00 WIB brief to prevent recurring forecasting biases.
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '6px', borderTop: '1px dashed var(--border-subtle)' }}>
                    <span className="font-mono text-xs text-tertiary">
                      SOURCE: vault/nexus/learning_store.md (:27124)
                    </span>
                    <button
                      className="brief-read-btn font-mono"
                      onClick={() => setShowPromptDrawer(true)}
                    >
                      Deep Inspect Injected Prompt ↗
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 03 · Compact Heuristics Repository Table */}
      <div className="section-eyebrow font-mono">
        <span className="console-prompt">//</span> 03 · AUDITABLE HEURISTICS REPOSITORY
      </div>
      <section className="history-section">
        <header className="history-header">
          <div>
            <h2 className="history-title">Heuristic Rules &amp; Provenance Ledger</h2>
            <div className="history-subtitle font-mono text-xs">
              Repository of autonomous market rules and verifiable evidence traces (click row to inspect full provenance)
            </div>
          </div>
          <div className="filter-tabs">
            <button
              className={`filter-tab-btn font-mono ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({heuristics.length})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'active' ? 'active' : ''}`}
              onClick={() => setFilter('active')}
            >
              Active ({activeCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'superseded' ? 'active' : ''}`}
              onClick={() => setFilter('superseded')}
            >
              Superseded ({supersededCount})
            </button>
          </div>
        </header>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '90px' }}>Rule ID</th>
                <th style={{ width: '140px' }}>Domain</th>
                <th>Formulated Heuristic Rule</th>
                <th style={{ width: '80px' }}>Observed</th>
                <th style={{ width: '70px' }}>Validated</th>
                <th style={{ width: '70px' }}>Contradicted</th>
                <th style={{ width: '100px' }}>Validation Rate</th>
                <th style={{ width: '90px' }}>Status</th>
                <th style={{ width: '130px', textAlign: 'right' }}>Audit</th>
              </tr>
            </thead>
            <tbody>
              {filteredHeuristics.map((item) => (
                <CompactHeuristicRow
                  key={item.id}
                  item={item}
                  onInspect={(h) => setSelectedHeuristic(h)}
                />
              ))}
              {filteredHeuristics.length === 0 && (
                <tr>
                  <td colSpan="9" className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '24px 0' }}>
                    No heuristic rules match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Level 3: Deep Inspection SideSheet for Rule Evidence */}
      <EvidenceDrawer
        isOpen={!!selectedHeuristic}
        onClose={() => setSelectedHeuristic(null)}
        heuristic={selectedHeuristic}
      />

      {/* Level 3: Deep Inspection SideSheet for Full Prompt Injection */}
      <SideSheet
        isOpen={showPromptDrawer}
        onClose={() => setShowPromptDrawer(false)}
        title="Prompt Constraint Injection Audit"
        subtitle="Ingested dynamically into 07:00 WIB Morning Brief"
        tag="Active Injection"
        maxWidth="680px"
      >
        <div className="evidence-panel-root">
          <div className="evidence-rule-card">
            <div className="evidence-rule-header">
              <span className="detail-label font-mono">System Prompt Constraint Preamble</span>
              <span className="status-pill status-matched status-sm font-mono">
                <span className="status-indicator-dot" />
                <span>INJECTED</span>
              </span>
            </div>
            <p className="evidence-rule-text font-mono" style={{ fontSize: '12px', lineHeight: 1.6 }}>
              “Prior session reflection has formulated the following empirical constraints. When analyzing pre-market catalysts, prioritize these causal conditions over raw narrative bias:”
            </p>
          </div>

          <div className="evidence-ledger-header">
            <span className="eval-section-heading">Active Injected Constraints</span>
            <span className="eval-section-tag font-mono">{activeCount} Rules Active</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {heuristics.filter((h) => h.status === 'ACTIVE').map((h, i) => (
              <div key={h.id} style={{ background: 'var(--surface-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="font-mono text-xs font-bold text-primary">#{i + 1} · {h.category}</span>
                  <span className="font-mono text-xs text-matched font-bold">100% Validated</span>
                </div>
                <p className="font-mono text-xs text-secondary" style={{ lineHeight: 1.5, margin: 0 }}>
                  “{h.rule}”
                </p>
              </div>
            ))}
          </div>

          <div className="rca-memory-terminal-block" style={{ marginTop: '16px' }}>
            <div className="memory-prefix font-mono">
              <span className="memory-title">OBSIDIAN PERSISTENCE PROVENANCE</span>
              <span className="memory-injected-pill font-mono">READ-ONLY SYNC</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', marginTop: '6px' }}>
              <div><span className="font-mono text-tertiary">VAULT NOTE:</span> <span className="font-mono text-primary">vault/nexus/learning_store.md</span></div>
              <div><span className="font-mono text-tertiary">REST PORT:</span> <span className="font-mono text-matched">27124 (Local HTTPS)</span></div>
              <div><span className="font-mono text-tertiary">INJECTION POINT:</span> <span className="font-mono text-primary">orchestrator/gemini.py · build_prompt()</span></div>
            </div>
          </div>
        </div>
      </SideSheet>
    </div>
  );
}
