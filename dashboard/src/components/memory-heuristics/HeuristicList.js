'use client';
import { useState, useMemo } from 'react';
import { HeuristicStatusBadge } from '../common/Badges';
import { EmptyState } from '../common/StateViews';
import EvidenceDrawer from './EvidenceDrawer';

export default function HeuristicList({ heuristics = [] }) {
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedHeuristic, setSelectedHeuristic] = useState(null);

  const categories = useMemo(() => {
    const set = new Set(heuristics.map((h) => h.category).filter(Boolean));
    return ['ALL', ...Array.from(set)];
  }, [heuristics]);

  const filteredHeuristics = useMemo(() => {
    return heuristics.filter((h) => {
      const matchCat = selectedCategory === 'ALL' || h.category === selectedCategory;
      const matchQuery = !searchQuery || h.rule.toLowerCase().includes(searchQuery.toLowerCase());
      return matchCat && matchQuery;
    });
  }, [heuristics, selectedCategory, searchQuery]);

  return (
    <div className="heuristic-list-container">
      {/* Search & Filter Header */}
      <div className="heuristic-filter-bar">
        <div className="heuristic-category-tabs">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`filter-tab-btn font-mono ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
        <div className="heuristic-search-wrapper">
          <input
            type="text"
            className="heuristic-search-input font-mono text-xs"
            placeholder="Search heuristics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Heuristic Cards */}
      <div className="heuristic-cards-grid">
        {filteredHeuristics.map((item) => (
          <div className="heuristic-card" key={item.id}>
            <div className="heuristic-card-header">
              <span className="heuristic-cat-tag font-mono text-xs">{item.category}</span>
              <HeuristicStatusBadge status={item.status} />
            </div>

            <p className="heuristic-rule-text">“{item.rule}”</p>

            <div className="heuristic-card-footer">
              <div className="heuristic-metrics font-mono text-xs">
                <span>Obs: <strong>{item.observed}</strong></span>
                <span className="text-muted">·</span>
                <span className="text-matched">Val: <strong>{item.validated}</strong></span>
                <span className="text-muted">·</span>
                <span className="text-missed">Contra: <strong>{item.contradicted}</strong></span>
                {item.validationRate !== null && (
                  <>
                    <span className="text-muted">·</span>
                    <span className="font-bold">Rate: {item.validationRate}%</span>
                  </>
                )}
              </div>

              <button
                className="evidence-view-btn font-mono text-xs"
                onClick={() => setSelectedHeuristic(item)}
              >
                View Evidence →
              </button>
            </div>
          </div>
        ))}
      </div>

      {filteredHeuristics.length === 0 && (
        <div style={{ padding: '36px 0' }}>
          <EmptyState
            title="No Heuristics Found"
            message={searchQuery ? 'No heuristics match your search query.' : 'No heuristics recorded in this category.'}
          />
        </div>
      )}

      {/* Side-Sheet Evidence Drawer */}
      <EvidenceDrawer
        isOpen={Boolean(selectedHeuristic)}
        onClose={() => setSelectedHeuristic(null)}
        heuristic={selectedHeuristic}
      />
    </div>
  );
}
