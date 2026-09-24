'use client';
import { EmptyState } from '../common/StateViews';

export default function BlindSpotMatrix({ blindSpots = [] }) {
  if (!blindSpots || blindSpots.length === 0) {
    return (
      <div className="eval-pane" style={{ marginBottom: '24px' }}>
        <div className="eval-pane-header">
          <span className="eval-pane-title">Recurring Macro Blind Spots</span>
          <span className="eval-section-tag font-mono">Risk Frequency</span>
        </div>
        <div style={{ padding: '24px' }}>
          <EmptyState 
            title="No Recurring Blind Spots" 
            message="No repeated macro shock factors have been identified yet across historical RCA cycles."
          />
        </div>
      </div>
    );
  }

  const maxCount = Math.max(...blindSpots.map((b) => b.count), 1);

  return (
    <div className="eval-pane" style={{ marginBottom: '24px' }}>
      <div className="eval-pane-header">
        <div className="eval-pane-header-left">
          <span className="eval-pane-title">Recurring Macro Blind Spots</span>
          <span className="eval-section-tag font-mono">Error Attribution Frequency</span>
        </div>
        <span className="eval-section-tag font-mono">{blindSpots.length} Factors Identified</span>
      </div>

      <div className="eval-pane-body" style={{ padding: '18px 24px' }}>
        <div className="blindspot-matrix-list">
          {blindSpots.map((item, idx) => {
            const pct = Math.min(100, Math.max(10, (item.count / maxCount) * 100));
            return (
              <div className="blindspot-matrix-row" key={idx}>
                <div className="blindspot-info">
                  <span className="blindspot-name font-mono">{item.name}</span>
                  <span className="blindspot-count font-mono">{item.count} {item.count === 1 ? 'session' : 'sessions'}</span>
                </div>
                <div className="blindspot-bar-track">
                  <div 
                    className="blindspot-bar-fill" 
                    style={{ width: `${pct}%` }} 
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
