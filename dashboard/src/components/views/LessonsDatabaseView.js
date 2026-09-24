'use client';
import { useState, useEffect, useMemo } from 'react';

function formatPct(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = Number(val);
  if (Number.isNaN(num)) return String(val);
  return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
}

function HeuristicRow({ item, expanded, onToggle }) {
  const tested = item.validated + item.contradicted;
  const isUp = item.validationRate >= 50;

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
            <span>{item.id}</span>
          </div>
        </td>
        <td>
          <span className="font-mono text-xs text-secondary font-medium">
            {item.category}
          </span>
        </td>
        <td style={{ maxWidth: '420px', whiteSpace: 'normal', padding: '12px 14px' }}>
          <span className="font-medium text-xs leading-relaxed">
            “{item.rule}”
          </span>
        </td>
        <td className="font-mono text-xs">
          {item.observed} {item.observed === 1 ? 'run' : 'runs'}
        </td>
        <td className="font-mono text-xs text-matched font-bold">
          {item.validated}
        </td>
        <td className="font-mono text-xs text-missed font-bold">
          {item.contradicted}
        </td>
        <td>
          <div className="delta-cell font-mono">
            <span className={isUp ? 'text-matched' : 'text-missed'}>
              {item.validationRate !== null ? `${item.validationRate}%` : 'Unresolved'}
            </span>
          </div>
        </td>
        <td>
          <span className={`status-pill ${item.status === 'ACTIVE' ? 'status-matched' : 'status-missed'} status-sm font-mono`}>
            <span className="status-indicator-dot" />
            <span>{item.status}</span>
          </span>
        </td>
      </tr>
      {expanded && (
        <tr className="expanded-row">
          <td colSpan="8" className="expanded-cell">
            <div className="expanded-panel">
              <div className="expanded-grid">
                <div className="detail-item">
                  <div className="detail-label font-mono">Categorical Classification</div>
                  <div className="detail-value">{item.category}</div>
                  <div className="detail-sub font-mono">Active prompt constraint</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label font-mono">Empirical Validation Rate</div>
                  <div className="detail-value font-mono">
                    {item.validated} of {tested} tested sessions ({item.validationRate !== null ? `${item.validationRate}%` : 'Pending tests'})
                  </div>
                  <div className="detail-sub font-mono">Unresolved cases excluded</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label font-mono">Last Observed In Market</div>
                  <div className="detail-value font-mono">{item.lastObserved || 'Historical'}</div>
                  <div className="detail-sub font-mono">{item.evidence?.length || 0} historical trace logs</div>
                </div>
              </div>

              {/* Historical Provenance Trace */}
              <div className="expanded-lesson">
                <div className="detail-label font-mono" style={{ marginBottom: '8px' }}>
                  Auditable Evidence &amp; Observation Provenance
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {(item.evidence || []).map((ev, i) => (
                    <div 
                      key={i} 
                      style={{ 
                        background: 'var(--surface)', 
                        padding: '10px 14px', 
                        borderRadius: 'var(--radius-sm)', 
                        border: '1px solid var(--border-subtle)',
                        fontSize: '12px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span className="font-mono font-bold text-primary">{ev.date}</span>
                        <span className={`font-mono text-xs font-bold ${ev.outcome === 'VALIDATED' ? 'text-matched' : 'text-missed'}`}>
                          [{ev.outcome}] · IHSG: {ev.ihsg_actual} {ev.ihsg_actual_pct ? `(${formatPct(ev.ihsg_actual_pct)})` : ''}
                        </span>
                      </div>
                      <p className="text-secondary" style={{ lineHeight: 1.45 }}>{ev.summary}</p>
                    </div>
                  ))}
                  {(!item.evidence || item.evidence.length === 0) && (
                    <p className="expanded-lesson-text">No direct transaction log linked.</p>
                  )}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function LessonsDatabaseView({ theme, toggleTheme }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [expandedId, setExpandedId] = useState(null);

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

  return (
    <div className="content-container">
      {/* Page Header (Exact baseline layout) */}
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS / System Operations</div>
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
      <div className="section-eyebrow font-mono">01 · AUTONOMOUS REFLECTION &amp; KNOWLEDGE OVERVIEW</div>
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
      <div className="section-eyebrow font-mono">02 · RECURRING FACTOR ATTRIBUTION &amp; SELF-CORRECTION</div>
      <section className="eval-section">
        <header className="eval-header">
          <div className="eval-header-title">Macro Risk Factor Attribution &amp; Feedback Cycle</div>
          <div className="eval-header-right">
            <div className="eval-date-badge font-mono">Continuous Feedback</div>
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

          {/* Right Column: Prompt Constraints Logic */}
          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Closed-Loop Learning Architecture</span>
                  <span className="eval-section-tag font-mono">Deterministic Store</span>
                </div>
              </div>
              <div className="eval-pane-body" style={{ padding: '20px' }}>
                <div className="rca-lesson-card" style={{ marginBottom: '16px' }}>
                  <p className="rca-lesson-text">
                    “Kesalahan prediksi pada sesi sore diekstrak menjadi aturan korektif dalam format kausalitas ekonomi, disimpan ke vault Obsidian &amp; file JSON, kemudian diinjeksikan secara otomatis ke prompt Morning Brief sesi berikutnya.”
                  </p>
                  <div className="rca-lesson-meta font-mono">
                    <span>Injection Constraint Cap: Top 5 Active Lessons</span>
                    <span className="text-matched">Heuristic Feedback Loop Active</span>
                  </div>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  <p style={{ marginBottom: '8px' }}>
                    <strong>Validation Rule:</strong> Aturan dianggap <code>ACTIVE</code> bila rasio validasi &ge; 50% terhadap arah pasar sesungguhnya.
                  </p>
                  <p>
                    <strong>Obsidian Memory Sync:</strong> Catatan evaluasi diintegrasikan ke vault via REST API port 27124.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 03 · Table: Heuristic Rules & Provenance Ledger */}
      <div className="section-eyebrow font-mono">03 · AUDITABLE HEURISTICS REPOSITORY</div>
      <section className="history-section">
        <header className="history-header">
          <div>
            <h2 className="history-title">Heuristic Rules &amp; Provenance Ledger</h2>
            <div className="history-subtitle font-mono text-xs">
              Repository of autonomous market rules and verifiable evidence traces (click row to inspect)
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
              Active ({heuristics.filter((h) => h.status === 'ACTIVE').length})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'superseded' ? 'active' : ''}`}
              onClick={() => setFilter('superseded')}
            >
              Superseded ({heuristics.filter((h) => h.status !== 'ACTIVE').length})
            </button>
          </div>
        </header>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Category</th>
                <th>Formulated Rule</th>
                <th>Observed</th>
                <th>Validated</th>
                <th>Contradicted</th>
                <th>Validation Rate</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredHeuristics.map((item) => (
                <HeuristicRow
                  key={item.id}
                  item={item}
                  expanded={expandedId === item.id}
                  onToggle={() => setExpandedId(expandedId === item.id ? null : item.id)}
                />
              ))}
              {filteredHeuristics.length === 0 && (
                <tr>
                  <td colSpan="8" className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '24px 0' }}>
                    No heuristic rules match the selected filter.
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
