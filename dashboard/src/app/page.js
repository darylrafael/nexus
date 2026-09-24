'use client';
import { useState, useEffect, useMemo } from 'react';
import Sidebar from '../components/Sidebar';
import MarketIntelligence from '../components/market-intelligence';
import MemoryHeuristics from '../components/memory-heuristics';
import ExecutionTelemetry from '../components/execution-telemetry';
import { LoadingSkeleton, ErrorState } from '../components/common/StateViews';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('intel');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    const saved = localStorage.getItem('nexus-theme');
    if (saved) {
      setTheme(saved);
      document.documentElement.setAttribute('data-theme', saved);
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }

    fetchStats();
  }, []);

  const fetchStats = () => {
    setLoading(true);
    setError(null);
    fetch('/api/stats')
      .then((res) => {
        if (!res.ok) throw new Error(`API returned HTTP ${res.status}`);
        return res.json();
      })
      .then((json) => {
        if (!json.success) throw new Error(json.error || 'Failed to load intelligence feeds');
        setData(json);
      })
      .catch((err) => {
        console.error(err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    localStorage.setItem('nexus-theme', nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
  };

  const dashboard = useMemo(() => {
    if (!data) return null;
    const reviews = data.reviews || [];
    const latest = reviews[0];
    const evaluatedReviews = reviews.filter((r) => !r.isPendingReview);
    const wins = evaluatedReviews.filter((review) => review.ihsg_correct).length;
    const winRate = evaluatedReviews.length ? ((wins / evaluatedReviews.length) * 100).toFixed(1) : '0.0';
    const avgAccuracy = Number(data.stats?.avgAccuracy || 0).toFixed(1);

    return {
      stats: data.stats || {},
      reviews,
      latest,
      evaluatedReviews,
      avgAccuracy,
      winRate,
      wins,
      evaluatedCount: evaluatedReviews.length,
      isDemo: Boolean(data.isDemo),
    };
  }, [data]);

  const activeReview = useMemo(() => {
    if (!dashboard) return null;
    if (!selectedDate) return dashboard.latest;
    return dashboard.reviews.find((r) => r.date === selectedDate) || dashboard.latest;
  }, [dashboard, selectedDate]);

  const isHistorical = Boolean(activeReview && dashboard?.latest && activeReview.date !== dashboard.latest.date);

  const pillarDescriptions = {
    intel: 'What is happening in the market? — Multi-factor signals, variance attribution, and pre-market research.',
    memory: 'What has Nexus learned? — Reflection heuristics, recurring macro blind spots, and auditable evidence.',
    telemetry: 'Is Nexus operating correctly? — Pipeline health, deterministic agent performance, and execution audit.',
  };

  return (
    <div className="layout-root">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (tab === 'intel' && !selectedDate && dashboard?.latest) {
            setSelectedDate(dashboard.latest.date);
          }
        }}
        reviews={dashboard?.reviews || []}
        selectedDate={selectedDate}
        onSelectDate={(d) => {
          setSelectedDate(d);
          setActiveTab('intel');
        }}
      />

      <main className="main-viewport">
        <header className="header-meta">
          <div className="header-left">
            <h1 className="header-title">
              {activeTab === 'intel' && 'Market Intelligence & Evaluation'}
              {activeTab === 'memory' && 'Memory & Heuristics Vault'}
              {activeTab === 'telemetry' && 'Execution Telemetry & Audit'}
            </h1>
            <p className="header-pillar-desc font-mono text-xs text-muted">
              {pillarDescriptions[activeTab]}
            </p>
          </div>

          <div className="header-actions">
            {dashboard?.isDemo && (
              <span className="market-status-chip font-mono text-warning" style={{ borderColor: 'var(--warning-border)' }}>
                ● Demo Dataset
              </span>
            )}
            <div className="market-status-chip font-mono">
              <span className="live-dot" />
              <span>IDX Session</span>
            </div>
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? '☼' : '☾'}
            </button>
          </div>
        </header>

        <div className="main-content">
          {loading && <LoadingSkeleton message="Initializing institutional multi-agent telemetry..." />}

          {error && !loading && (
            <ErrorState title="System Ingestion Fault" message={error} onRetry={fetchStats} />
          )}

          {!loading && !error && (
            <>
              {activeTab === 'intel' && (
                <MarketIntelligence
                  dashboard={dashboard}
                  activeReview={activeReview}
                  isHistorical={isHistorical}
                  onSelectSession={(d) => setSelectedDate(d)}
                  onResetSelectedDate={() => setSelectedDate(null)}
                />
              )}

              {activeTab === 'memory' && <MemoryHeuristics />}

              {activeTab === 'telemetry' && <ExecutionTelemetry />}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
