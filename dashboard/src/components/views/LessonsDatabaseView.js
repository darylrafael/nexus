'use client';
import { useState, useEffect, useMemo } from 'react';
import SideSheet from '../common/SideSheet';
import EvidenceDrawer from '../memory-heuristics/EvidenceDrawer';

const DOMAIN_STYLES = {
  'Monetary Policy': { color: 'var(--accent-cyan)', bg: 'rgba(8, 145, 178, 0.1)', border: 'rgba(8, 145, 178, 0.28)' },
  'Foreign Exchange': { color: 'var(--warning-text)', bg: 'var(--warning-bg)', border: 'var(--warning-border)' },
  'Commodities': { color: 'var(--matched-text)', bg: 'var(--matched-bg)', border: 'var(--matched-border)' },
  'Liquidity & Flows': { color: '#a78bfa', bg: 'rgba(167, 139, 250, 0.1)', border: 'rgba(167, 139, 250, 0.28)' },
  'Sector Causality': { color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.1)', border: 'rgba(56, 189, 248, 0.28)' },
  'Macro & Geopolitics': { color: 'var(--missed-text)', bg: 'var(--missed-bg)', border: 'var(--missed-border)' },
};

function DomainBadge({ category }) {
  const style = DOMAIN_STYLES[category] || {
    color: 'var(--text-secondary)',
    bg: 'var(--surface-subtle)',
    border: 'var(--border-default)',
  };
  return (
    <span
      className="font-mono text-xs font-semibold"
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        color: style.color,
        background: style.bg,
        border: `1px solid ${style.border}`,
        whiteSpace: 'nowrap',
        fontSize: '11px',
      }}
    >
      {category}
    </span>
  );
}

function formatQuarantineReason(reason = '') {
  if (reason.startsWith('unreliable_source_data:')) {
    return { tag: 'UNVERIFIED SOURCE', detail: reason.replace('unreliable_source_data:', '').trim() };
  }
  if (reason.startsWith('session_limit_exceeded:')) {
    return { tag: 'SESSION CAP (>2)', detail: 'Exceeded maximum 2 high-conviction lessons per session' };
  }
  if (reason.startsWith('duplicate_tail:')) {
    return { tag: 'DUPLICATE OUTCOME', detail: 'Redundant conclusion already captured by primary session rule' };
  }
  if (reason.startsWith('numeric_contradiction:')) {
    return { tag: 'TAPE CONTRADICTION', detail: reason.replace('numeric_contradiction:', '').trim() };
  }
  if (reason.startsWith('boilerplate_generic:')) {
    return { tag: 'GENERIC BOILERPLATE', detail: 'Non-falsifiable trading advice filtered out' };
  }
  if (reason.startsWith('invalid_unit:')) {
    return { tag: 'MALFORMED METRIC', detail: reason.replace('invalid_unit:', '').trim() };
  }
  return { tag: 'HYGIENE GATE', detail: reason };
}

export default function LessonsDatabaseView({ theme, toggleTheme }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all' | 'active' | 'hypothesis' | 'superseded' | 'quarantined'
  const [domainFilter, setDomainFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [selectedHeuristic, setSelectedHeuristic] = useState(null);
  const [showPromptDrawer, setShowPromptDrawer] = useState(false);
  const [expandedCluster, setExpandedCluster] = useState(null);

  const PAGE_SIZE = 8;

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

  const activeRules = useMemo(() => heuristics.filter((h) => h.status === 'ACTIVE'), [heuristics]);
  const categories = useMemo(() => {
    const set = new Set(heuristics.map((h) => h.category).filter(Boolean));
    return ['ALL', ...Array.from(set)];
  }, [heuristics]);

  const filteredItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (filter === 'quarantined') {
      return quarantinedLessons.filter((item) => {
        if (!q) return true;
        return (
          (item.lesson || '').toLowerCase().includes(q) ||
          (item.reason || '').toLowerCase().includes(q) ||
          (item.date || '').toLowerCase().includes(q)
        );
      });
    }

    return heuristics.filter((h) => {
      if (filter === 'active' && h.status !== 'ACTIVE') return false;
      if (filter === 'hypothesis' && h.status !== 'HYPOTHESIS') return false;
      if (filter === 'superseded' && h.status !== 'SUPERSEDED') return false;
      if (domainFilter !== 'ALL' && h.category !== domainFilter) return false;
      if (q) {
        const hay = `${h.id} ${h.category} ${h.rule} ${h.originDate || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [heuristics, quarantinedLessons, filter, domainFilter, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paginatedItems = useMemo(() => {
    const start = (safePage - 1) * PAGE_SIZE;
    return filteredItems.slice(start, start + PAGE_SIZE);
  }, [filteredItems, safePage]);

  const handleFilterChange = (nextFilter) => {
    setFilter(nextFilter);
    setPage(1);
  };

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
  const activeCount = activeRules.length;
  const hypothesisCount = heuristics.filter((h) => h.status === 'HYPOTHESIS').length;
  const supersededCount = heuristics.filter((h) => h.status === 'SUPERSEDED').length;
  const quarantinedCount = quarantinedLessons.length;
  const totalExtractedCount = heuristics.length + quarantinedCount;
  const displayValRate = stats.avgValidationRate != null ? `${stats.avgValidationRate}%` : '—';

  return (
    <div className="content-container">
      {/* Page Header */}
      <header className="page-header">
        <div>
          <div className="breadcrumb">NEXUS · Self-Learning Memory</div>
          <h1 className="page-title">Heuristics &amp; Hygiene Vault</h1>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="header-pill-btn"
            onClick={() => setShowPromptDrawer(true)}
            title="Inspect Active Prompt Constraints"
          >
            Injected Prompt ({activeCount}) ↗
          </button>
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

      {/* Row 1: 4 Interactive KPI Cards */}
      <section className="kpi-row">
        <div
          className="kpi-card interactive"
          onClick={() => handleFilterChange('active')}
          title="Filter by Active Rules"
        >
          <div className="kpi-top">
            <span className="kpi-label font-mono">Active In Prompt</span>
            <span className="kpi-click-hint font-mono">Filter ↗</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-matched">{activeCount} Rules</div>
            <span className="memory-active-pill font-mono">Top 5 Injected</span>
          </div>
          <div className="kpi-context">
            <span>Forward-validated rules governing 06:55 brief</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-top">
            <span className="kpi-label font-mono">Forward Win Rate</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{displayValRate}</div>
            <span className="font-mono text-xs text-muted">
              {stats.validatedHeuristicsCount || 0} proven
            </span>
          </div>
          <div className="kpi-context">
            <span>Empirical accuracy on subsequent sessions</span>
          </div>
        </div>

        <div
          className="kpi-card interactive"
          onClick={() => handleFilterChange('all')}
          title="View All Validated Rules"
        >
          <div className="kpi-top">
            <span className="kpi-label font-mono">Validated Corpus</span>
            <span className="kpi-click-hint font-mono">View All ↗</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono">{heuristics.length} Rules</div>
            <span className="font-mono text-xs text-secondary">{hypothesisCount} Hypothesis</span>
          </div>
          <div className="kpi-context">
            <span>Passed 5-stage deterministic hygiene check</span>
          </div>
        </div>

        <div
          className="kpi-card interactive"
          onClick={() => handleFilterChange('quarantined')}
          title="Inspect Quarantined Rules"
        >
          <div className="kpi-top">
            <span className="kpi-label font-mono">Quarantine Gate</span>
            <span className="kpi-click-hint font-mono">Inspect ↗</span>
          </div>
          <div className="kpi-val-row">
            <div className="kpi-value font-mono text-warning">{quarantinedCount} Blocked</div>
            <span className="font-mono text-xs text-muted">
              {Math.round((quarantinedCount / Math.max(1, totalExtractedCount)) * 100)}% rejected
            </span>
          </div>
          <div className="kpi-context">
            <span>Prevented from corrupting morning prompts</span>
          </div>
        </div>
      </section>

      {/* Row 2: Balanced Twin Executive Overview (Compact, Equal Height) */}
      <section className="eval-section" style={{ marginBottom: '24px' }}>
        <div className="eval-body">
          {/* Left Pane: Active Rules Currently Injected into 06:55 Brief */}
          <div className="eval-pane">
            <div className="eval-pane-header">
              <div className="eval-pane-header-left">
                <span className="eval-pane-title">Active Prompt Constraints (06:55 WIB)</span>
              </div>
              <button
                type="button"
                className="font-mono"
                onClick={() => setShowPromptDrawer(true)}
                style={{
                  background: 'var(--surface-hover)',
                  border: '1px solid var(--border-strong)',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  color: 'var(--accent-cyan)',
                  cursor: 'pointer',
                  fontSize: '11px',
                }}
              >
                View Full Prompt ({activeCount}) →
              </button>
            </div>
            <div className="eval-pane-body" style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {activeRules.slice(0, 4).map((h) => (
                <div
                  key={h.id}
                  onClick={() => setSelectedHeuristic(h)}
                  style={{
                    padding: '10px 12px',
                    background: 'var(--surface-subtle)',
                    border: '1px solid var(--border-subtle)',
                    borderLeft: '3px solid var(--matched-text)',
                    borderRadius: 'var(--radius-sm)',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="font-mono text-xs font-bold text-primary">{h.id}</span>
                      <DomainBadge category={h.category} />
                      <span className="font-mono text-xs text-muted">{h.originDate}</span>
                    </div>
                    <span className="font-mono text-xs text-matched font-bold">
                      ✓ {h.validationRate}% ({h.validated}/{h.observed} runs)
                    </span>
                  </div>
                  {h.trigger && h.outcome ? (
                    <div style={{ fontSize: '12px', lineHeight: 1.45, color: 'var(--text-secondary)' }}>
                      <strong style={{ color: 'var(--text-primary)' }}>WHEN:</strong> {h.trigger}{' '}
                      <strong style={{ color: 'var(--matched-text)' }}>→ THEN:</strong> {h.outcome}
                    </div>
                  ) : (
                    <div style={{ fontSize: '12px', lineHeight: 1.45, color: 'var(--text-secondary)' }}>
                      {h.rule}
                    </div>
                  )}
                </div>
              ))}

              {/* Compact 5-Stage Hygiene Pipeline Funnel */}
              <div
                style={{
                  marginTop: 'auto',
                  padding: '10px 12px',
                  background: 'var(--surface-well)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <span className="font-mono text-xs text-muted">HYGIENE FUNNEL:</span>
                <div className="font-mono text-xs" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span className="text-secondary"><strong>{totalExtractedCount}</strong> Extracted</span>
                  <span className="text-muted">→</span>
                  <span className="text-warning"><strong>{quarantinedCount}</strong> Blocked</span>
                  <span className="text-muted">→</span>
                  <span className="text-primary"><strong>{heuristics.length}</strong> Valid</span>
                  <span className="text-muted">→</span>
                  <span className="text-matched font-bold"><strong>{activeCount}</strong> Active</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Pane: Clustered Macro Blind Spots (7 Thematic Categories) */}
          <div className="eval-column-right">
            <div className="eval-pane">
              <div className="eval-pane-header">
                <div className="eval-pane-header-left">
                  <span className="eval-pane-title">Recurring Macro Blind Spots (Clustered)</span>
                </div>
                <span className="eval-section-tag font-mono">
                  {stats.rawBlindSpotsCount || 106} RCA Citations → {blindSpots.length} Themes
                </span>
              </div>
              <div className="eval-pane-body" style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '9px' }}>
                {blindSpots.map((cluster) => {
                  const pct = Math.min(100, Math.max(10, (cluster.count / maxBlindSpotCount) * 100));
                  const isExp = expandedCluster === cluster.id;
                  return (
                    <div
                      key={cluster.id}
                      onClick={() => setExpandedCluster(isExp ? null : cluster.id)}
                      style={{
                        padding: '9px 12px',
                        background: 'var(--surface-subtle)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid var(--border-subtle)',
                        cursor: 'pointer',
                      }}
                      title="Click to toggle sample RCA citations"
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                        <span className="font-mono text-xs font-semibold text-primary">
                          {cluster.name}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                          <span className="font-mono text-xs text-muted">{cluster.sharePct}%</span>
                          <span
                            className="font-mono text-warning font-bold text-xs"
                            style={{
                              background: 'var(--warning-bg)',
                              border: '1px solid var(--warning-border)',
                              padding: '1px 6px',
                              borderRadius: '3px',
                            }}
                          >
                            {cluster.count}x
                          </span>
                        </div>
                      </div>
                      <div style={{ height: '4px', width: '100%', background: 'var(--surface-well)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${pct}%`, background: 'var(--warning-text)', borderRadius: '2px' }} />
                      </div>
                      {isExp && cluster.examples?.length > 0 && (
                        <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px dashed var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {cluster.examples.map((ex, i) => (
                            <div key={i} style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                              • {ex}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Row 3: Clean, Searchable, Paginated Heuristic & Quarantine Ledger */}
      <section className="history-section">
        <header className="history-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <h2 className="history-title" style={{ margin: 0 }}>Knowledge Base Ledger</h2>
            {filter !== 'quarantined' && (
              <select
                value={domainFilter}
                onChange={(e) => {
                  setDomainFilter(e.target.value);
                  setPage(1);
                }}
                aria-label="Filter by domain"
                className="font-mono text-xs"
                style={{
                  background: 'var(--surface-subtle)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: '4px',
                  padding: '5px 8px',
                  cursor: 'pointer',
                }}
              >
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat === 'ALL' ? 'All Domains' : cat}
                  </option>
                ))}
              </select>
            )}
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Search keyword, sector, or date..."
              aria-label="Search heuristic rules"
              className="font-mono text-xs"
              style={{
                background: 'var(--surface-subtle)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-default)',
                borderRadius: '4px',
                padding: '5px 10px',
                minWidth: '210px',
              }}
            />
          </div>

          <div className="filter-tabs">
            <button
              className={`filter-tab-btn font-mono ${filter === 'all' ? 'active' : ''}`}
              onClick={() => handleFilterChange('all')}
            >
              Validated ({heuristics.length})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'active' ? 'active' : ''}`}
              onClick={() => handleFilterChange('active')}
            >
              Active ({activeCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'hypothesis' ? 'active' : ''}`}
              onClick={() => handleFilterChange('hypothesis')}
            >
              Hypothesis ({hypothesisCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'superseded' ? 'active' : ''}`}
              onClick={() => handleFilterChange('superseded')}
            >
              Superseded ({supersededCount})
            </button>
            <button
              className={`filter-tab-btn font-mono ${filter === 'quarantined' ? 'active' : ''}`}
              onClick={() => handleFilterChange('quarantined')}
            >
              Quarantined ({quarantinedCount})
            </button>
          </div>
        </header>

        {filter === 'quarantined' ? (
          <div className="table-wrapper">
            <div style={{ padding: '10px 16px', background: 'var(--warning-bg)', borderBottom: '1px solid var(--warning-border)', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--warning-text)' }}>5-Stage Hygiene Gate:</strong> {quarantinedCount} LLM-generated rules were blocked by <code>validate_lesson()</code> before prompt injection.
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '110px' }}>Date</th>
                  <th style={{ width: '210px' }}>Gate Filter</th>
                  <th>Quarantined Lesson &amp; Audit Note</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.map((q, idx) => {
                  const parsed = formatQuarantineReason(q.reason);
                  return (
                    <tr key={idx} className="table-row">
                      <td className="font-mono text-xs font-bold text-primary">{q.date}</td>
                      <td>
                        <span
                          className="font-mono text-xs text-warning font-semibold"
                          style={{
                            background: 'var(--warning-bg)',
                            border: '1px solid var(--warning-border)',
                            padding: '2px 7px',
                            borderRadius: '4px',
                            display: 'inline-block',
                          }}
                        >
                          {parsed.tag}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <div className="text-xs text-primary" style={{ lineHeight: 1.45, marginBottom: '3px' }}>
                          {q.lesson}
                        </div>
                        <div className="font-mono text-xs text-muted">{parsed.detail}</div>
                      </td>
                    </tr>
                  );
                })}
                {paginatedItems.length === 0 && (
                  <tr>
                    <td colSpan="3" className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '24px 0' }}>
                      No quarantined rules match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <>
            {/* Mobile Cards */}
            <div className="mobile-cards-list">
              {paginatedItems.map((item) => (
                <div
                  key={item.id}
                  className="mobile-heuristic-card"
                  onClick={() => setSelectedHeuristic(item)}
                >
                  <div className="mobile-card-top">
                    <span className="font-mono font-bold text-xs text-primary">{item.id} · {item.originDate}</span>
                    <DomainBadge category={item.category} />
                    <span className={`status-pill ${item.status === 'ACTIVE' ? 'status-matched' : (item.status === 'SUPERSEDED' ? 'status-missed' : 'status-pending')} status-sm font-mono`}>
                      {item.status}
                    </span>
                  </div>
                  <p className="mobile-card-rule" style={{ margin: '6px 0' }}>{item.rule}</p>
                  <div className="mobile-card-meta font-mono text-xs">
                    <span>Tested: {item.observed} runs</span>
                    <span className="text-matched">Val: {item.validated ?? 0}</span>
                    <span className="text-missed">Contr: {item.contradicted ?? 0}</span>
                    <span className="font-bold text-primary">
                      {item.validationRate !== null ? `${item.validationRate}%` : 'Pending Trigger'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop Clean 5-Column Table (No Horizontal Scroll) */}
            <div className="table-wrapper desktop-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th style={{ width: '105px' }}>Rule / Date</th>
                    <th style={{ width: '150px' }}>Domain</th>
                    <th>Causal Rule (WHEN → THEN)</th>
                    <th style={{ width: '140px' }}>Track Record</th>
                    <th style={{ width: '140px', textAlign: 'right' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedItems.map((item) => {
                    const isUp = item.validationRate >= 50;
                    return (
                      <tr
                        key={item.id}
                        className="table-row"
                        onClick={() => setSelectedHeuristic(item)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td>
                          <div className="font-mono text-xs font-bold text-primary">{item.id}</div>
                          <div className="font-mono text-xs text-muted" style={{ fontSize: '11px' }}>
                            {item.originDate || '—'}
                          </div>
                        </td>
                        <td>
                          <DomainBadge category={item.category} />
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          {item.trigger && item.outcome ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '12px', lineHeight: 1.4 }}>
                              <div style={{ color: 'var(--text-secondary)' }}>
                                <strong className="font-mono text-xs" style={{ color: 'var(--accent-cyan)' }}>WHEN: </strong>
                                {item.trigger}
                              </div>
                              <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                                <strong className="font-mono text-xs" style={{ color: 'var(--matched-text)' }}>THEN: </strong>
                                {item.outcome}
                              </div>
                            </div>
                          ) : (
                            <div className="text-xs text-primary" style={{ lineHeight: 1.45 }}>
                              {item.rule}
                            </div>
                          )}
                        </td>
                        <td>
                          {item.observed > 0 ? (
                            <div className="font-mono text-xs">
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                                <span className={isUp ? 'text-matched font-bold' : 'text-missed font-bold'}>
                                  {item.validationRate}%
                                </span>
                                <span className="text-muted">
                                  {item.validated}/{item.observed} runs
                                </span>
                              </div>
                              <div style={{ height: '4px', width: '100%', background: 'var(--surface-well)', borderRadius: '2px', overflow: 'hidden' }}>
                                <div
                                  style={{
                                    height: '100%',
                                    width: `${item.validationRate}%`,
                                    background: isUp ? 'var(--matched-text)' : 'var(--missed-text)',
                                  }}
                                />
                              </div>
                            </div>
                          ) : (
                            <span className="font-mono text-xs text-muted">Awaiting Trigger</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                            <span className={`status-pill ${item.status === 'ACTIVE' ? 'status-matched' : (item.status === 'SUPERSEDED' ? 'status-missed' : 'status-pending')} status-sm font-mono`}>
                              <span className="status-indicator-dot" />
                              <span>{item.status}</span>
                            </span>
                            <span className="font-mono text-xs" style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                              ↗
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {paginatedItems.length === 0 && (
                    <tr>
                      <td colSpan="5" className="text-muted font-mono text-xs" style={{ textAlign: 'center', padding: '24px 0' }}>
                        No heuristic rules match the selected filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* Pagination Footer */}
        {filteredItems.length > PAGE_SIZE && (
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
              Showing {(safePage - 1) * PAGE_SIZE + 1}–{Math.min(safePage * PAGE_SIZE, filteredItems.length)} of {filteredItems.length} rules
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

      <EvidenceDrawer
        isOpen={!!selectedHeuristic}
        onClose={() => setSelectedHeuristic(null)}
        heuristic={selectedHeuristic}
      />

      <SideSheet
        isOpen={showPromptDrawer}
        onClose={() => setShowPromptDrawer(false)}
        title="06:55 WIB Prompt Constraint Injection"
        subtitle="Forward-validated rules dynamically injected via build_learning_context()"
        tag="Active Prompt"
        maxWidth="680px"
      >
        <div className="evidence-panel-root">
          <div className="evidence-ledger-header">
            <span className="eval-section-heading">Active Injected Rules ({activeCount})</span>
            <span className="eval-section-tag font-mono">Top 5 Injected Daily</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {activeRules.map((h) => (
              <div
                key={h.id}
                style={{
                  background: 'var(--surface-subtle)',
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-default)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="font-mono text-xs font-bold text-primary">{h.id}</span>
                    <DomainBadge category={h.category} />
                  </div>
                  <span className="font-mono text-xs text-matched font-bold">
                    {h.validationRate ?? 100}% ({h.validated}/{h.observed} runs)
                  </span>
                </div>
                {h.trigger && h.outcome ? (
                  <div style={{ fontSize: '12px', lineHeight: 1.45, color: 'var(--text-secondary)' }}>
                    <strong style={{ color: 'var(--text-primary)' }}>WHEN:</strong> {h.trigger}{' '}
                    <strong style={{ color: 'var(--matched-text)' }}>→ THEN:</strong> {h.outcome}
                  </div>
                ) : (
                  <p className="font-mono text-xs text-secondary" style={{ lineHeight: 1.5, margin: 0 }}>
                    {h.rule}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </SideSheet>
    </div>
  );
}
