'use client';
import { useState, useEffect, useMemo } from 'react';
import SideSheet from '../common/SideSheet';
import EvidenceDrawer from '../memory-heuristics/EvidenceDrawer';

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
      <td style={{ width: '150px' }}>
        <span className="font-mono text-xs text-secondary font-medium">
          {item.category}
        </span>
      </td>
      <td style={{ maxWidth: '460px', padding: '12px 14px' }}>
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
        {item.validated !== undefined && item.validated !== null ? item.validated : '—'}
      </td>
      <td className="font-mono text-xs text-missed font-bold" style={{ width: '70px' }}>
        {item.contradicted !== undefined && item.contradicted !== null ? item.contradicted : '—'}
      </td>
      <td style={{ width: '100px' }}>
        <div className="delta-cell font-mono">
          <span className={item.validationRate !== null ? (isUp ? 'text-matched font-bold' : 'text-missed font-bold') : 'text-muted'}>
            {item.validationRate !== null ? `${item.validationRate}%` : (item.status === 'HYPOTHESIS' ? 'Hypothesis' : 'Untested')}
          </span>
        </div>
      </td>
      <td style={{ width: '90px' }}>
        <span className={`status-pill ${item.status === 'ACTIVE' ? 'status-matched' : (item.status === 'SUPERSEDED' ? 'status-missed' : 'status-pending')} status-sm font-mono`}>
          <span className="status-indicator-dot" />
          <span>{item.status}</span>
        </span>
      </td>
      <td style={{ width: '120px', textAlign: 'right' }}>
        <button
          className="brief-read-btn font-mono"
          style={{ padding: '6px 10px', fontSize: '12px', minHeight: '36px', display: 'inline-flex', alignItems: 'center' }}
          onClick={(e) => {
            e.stopPropagation();
            onInspect(item);
          }}
        >
          Inspect ↗
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
  const heuristics = useMemo(() => data?.heuristics || [], [data?.heuristics]);
  const quarantinedLessons = useMemo(() => data?.quarantinedLessons || [], [data?.quarantinedLessons]);
  const blindSpots = useMemo(() => data?.blindSpots || [], [data?.blindSpots]);

  const filteredHeuristics = useMemo(() => {
    if (filter === 'active') return heuristics.filter((h) => h.status === 'ACTIVE');
    if (filter === 'hypothesis') return heuristics.filter((h) => h.status === 'HYPOTHESIS');
    if (filter === 'superseded') return heuristics.filter((h) => h.status === 'SUPERSEDED');
    return heuristics;
  }, [heuristics, filter]);

  if (loading) {
    return <main className="center-state">Loading memory &amp; heuristics...</main>;
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
  const hypothesisCount = heuristics.filter((h) => h.status === 'HYPOTHESIS').length;
  const supersededCount = heuristics.filter((h) => h.status === 'SUPERSEDED').length;
  const quarantinedCount = quarantinedLessons.length;
  const displayValRate = stats.avgValidationRate != null ? `${stats.avgValidationRate}%` : (heuristics.length > 0 ? 'Tracking' : '—');

  return (
    <div className="content-container">
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS · Self-Learning Memory</div>
          <h1 className="page-title">Heuristics &amp; Hygiene Vault</h1>
        </div>
        <div className="header-actions">
          <div className="live-badge">
            <span className="live-dot" />
            <span>5-Stage Gate Active</span>
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
            <span className="kpi-label font-mono">Active In Prompt</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched">{stats.activeHeuristics || activeCount} Rules</div>
          </div>
          <div className="kpi-context">
            <span>Injected into 06:55 WIB morning brief</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Forward Validation</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{displayValRate}</div>
          </div>
          <div className="kpi-context">
            <span>{stats.validatedHeuristicsCount || 0} rules tested on subsequent sessions</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Macro Blind Spots</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-warning">{stats.blindSpotsCount || 0} Factors</div>
          </div>
          <div className="kpi-context">
            <span>Recurring variance drivers flagged by RCA</span>
          </div>
        </div>

        <div
          className="kpi-card interactive"
          onClick={() => setFilter('quarantined')}
          style={{ cursor: 'pointer' }}
          title="Click to inspect lessons blocked by the 5-stage hygiene filter"
        >
          <div className="kpi-top">
            <span className="kpi-label font-mono">Quarantine Gate</span>
            <span className="kpi-click-hint font-mono">Inspect ↗</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-warning">
              {quarantinedCount} Blocked
            </div>
          </div>
          <div className="kpi-context">
            <span>{heuristics.length} validated · {quarantinedCount} rejected</span>
          </div>
        </div>
      </section>

      <section className="history-section">
        <header className="history-header">
          <div>
            <h2 className="history-title">Heuristic Rules Ledger</h2>
          </div>
          <div className="filter-tabs">
            <button
              className={`filter-tab-btn font-mono ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              Validated ({heuristics.length})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'active' ? 'active' : ''}`}
              onClick={() => setFilter('active')}
            >
              Active ({activeCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'hypothesis' ? 'active' : ''}`}
              onClick={() => setFilter('hypothesis')}
            >
              Hypothesis ({hypothesisCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'superseded' ? 'active' : ''}`}
              onClick={() => setFilter('superseded')}
            >
              Superseded ({supersededCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'quarantined' ? 'active' : ''}`}
              onClick={() => setFilter('quarantined')}
            >
              Quarantined ({quarantinedCount})
            </button>
          </div>
        </header>

        {filter === 'quarantined' ? (
          <div className="table-wrapper">
            <div style={{ padding: '10px 16px', background: 'var(--warning-bg)', borderBottom: '1px solid var(--warning-border)', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--warning-text)' }}>5-Stage Hygiene Audit:</strong> {quarantinedCount} LLM-generated lessons were rejected by <code>validate_lesson()</code> (sign confusion, closing tape contradiction, unverified flow, boilerplate, or session cap).
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '110px' }}>Date</th>
                  <th style={{ width: '260px' }}>Rejection Reason</th>
                  <th>Quarantined Lesson</th>
                </tr>
              </thead>
              <tbody>
                {quarantinedLessons.map((q, idx) => (
                  <tr key={idx} className="table-row">
                    <td className="font-mono text-xs font-bold text-primary">{q.date}</td>
                    <td>
                      <span className="font-mono text-xs text-warning" style={{ background: 'var(--warning-bg)', border: '1px solid var(--warning-border)', padding: '2px 6px', borderRadius: '4px', display: 'inline-block' }}>
                        {q.reason}
                      </span>
                    </td>
                    <td className="text-xs text-secondary" style={{ padding: '10px 14px', lineHeight: 1.5 }}>
                      &ldquo;{q.lesson}&rdquo;
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <>
            <div className="mobile-cards-list">
              {filteredHeuristics.map((item) => (
                <div
                  key={item.id}
                  className="mobile-heuristic-card"
                  onClick={() => setSelectedHeuristic(item)}
                >
                  <div className="mobile-card-top">
                    <span className="font-mono font-bold text-xs text-primary">{item.id}</span>
                    <span className="font-mono text-xs text-secondary">{item.category}</span>
                    <span className={`status-pill ${item.status === 'ACTIVE' ? 'status-matched' : (item.status === 'SUPERSEDED' ? 'status-missed' : 'status-pending')} status-sm font-mono`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="mobile-card-rule">&ldquo;{item.rule}&rdquo;</p>
                  <div className="mobile-card-meta font-mono text-xs">
                    <span>Observed: {item.observed} runs</span>
                    <span className="text-matched">Val: {item.validated ?? 0}</span>
                    <span className="text-missed">Contr: {item.contradicted ?? 0}</span>
                    <span className="font-bold text-primary">
                      {item.validationRate !== null ? `${item.validationRate}%` : 'Hypothesis'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="table-wrapper desktop-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '90px' }}>ID</th>
                    <th style={{ width: '150px' }}>Domain</th>
                    <th>Heuristic Rule</th>
                    <th style={{ width: '80px' }}>Observed</th>
                    <th style={{ width: '70px' }}>Val</th>
                    <th style={{ width: '70px' }}>Contr</th>
                    <th style={{ width: '100px' }}>Win Rate</th>
                    <th style={{ width: '90px' }}>Status</th>
                    <th style={{ width: '120px', textAlign: 'right' }}>Evidence</th>
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
                        No rules match the selected filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="eval-section">
        <header className="eval-header">
          <div className="eval-header-title">Macro Blind Spots &amp; Prompt Injection</div>
        </header>

        <div className="eval-body">
          <div className="eval-column-left">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Top Recurring Blind Spots</span>
                </div>
                <span className="eval-section-tag font-mono">{blindSpots.length} Factors</span>
              </div>
              <div className="eval-pane-body" style={{ padding: '14px 16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {blindSpots.map((item, idx) => {
                    const pct = Math.min(100, Math.max(12, (item.count / maxBlindSpotCount) * 100));
                    return (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                          padding: '9px 12px',
                          background: 'var(--surface-subtle)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
                          <span className="font-mono text-primary font-semibold" style={{ fontSize: '12px', lineHeight: '1.4' }}>
                            #{String(idx + 1).padStart(2, '0')} · {item.name}
                          </span>
                          <span
                            className="font-mono text-warning font-semibold text-xs"
                            style={{
                              background: 'var(--warning-bg)',
                              border: '1px solid var(--warning-border)',
                              padding: '1px 6px',
                              borderRadius: '3px',
                              flexShrink: 0,
                            }}
                          >
                            {item.count}x
                          </span>
                        </div>
                        <div style={{ height: '4px', width: '100%', background: 'var(--surface-well)', borderRadius: '2px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: 'var(--warning-text)', borderRadius: '2px' }} />
                        </div>
                      </div>
                    );
                  })}
                  {blindSpots.length === 0 && (
                    <p className="rca-content-muted font-mono text-xs">No recurring blind spots identified.</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">06:55 Prompt Constraint Injection</span>
                </div>
                <div className="loop-active-tag font-mono">
                  <span className="live-dot" style={{ width: 6, height: 6 }} />
                  Active
                </div>
              </div>
              <div className="eval-pane-body" style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ background: 'var(--surface-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="font-mono text-xs font-bold text-primary">
                      {activeCount} Active Constraints
                    </span>
                    <span className="font-mono text-xs text-matched font-semibold">
                      Top 5 Injected Daily
                    </span>
                  </div>
                  <p className="text-secondary text-xs" style={{ margin: 0, lineHeight: 1.45 }}>
                    Forward-validated lessons are injected into the 06:55 WIB pre-market prompt via <code>build_learning_context()</code>.
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: '6px' }}>
                    <button
                      className="brief-read-btn font-mono"
                      onClick={() => setShowPromptDrawer(true)}
                    >
                      Inspect Injected Prompt ↗
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <EvidenceDrawer
        isOpen={!!selectedHeuristic}
        onClose={() => setSelectedHeuristic(null)}
        heuristic={selectedHeuristic}
      />

      <SideSheet
        isOpen={showPromptDrawer}
        onClose={() => setShowPromptDrawer(false)}
        title="Prompt Constraint Injection"
        subtitle="Ingested into 06:55 WIB Morning Brief"
        tag="Prompt"
        maxWidth="680px"
      >
        <div className="evidence-panel-root">
          <div className="evidence-ledger-header">
            <span className="eval-section-heading">Active Injected Rules ({activeCount})</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {heuristics.filter((h) => h.status === 'ACTIVE').map((h, i) => (
              <div key={h.id} style={{ background: 'var(--surface-subtle)', padding: '12px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="font-mono text-xs font-bold text-primary">#{i + 1} · {h.category}</span>
                  <span className="font-mono text-xs text-matched font-bold">n={h.observed || 1} ({h.validationRate ?? 100}%)</span>
                </div>
                <p className="font-mono text-xs text-secondary" style={{ lineHeight: 1.5, margin: 0 }}>
                  “{h.rule}”
                </p>
              </div>
            ))}
          </div>
        </div>
      </SideSheet>
    </div>
  );
}
