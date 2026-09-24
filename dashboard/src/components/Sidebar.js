'use client';

function formatHeaderDate(d) {
  if (!d) return '';
  const parts = d.split('-');
  if (parts.length === 3) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const m = months[parseInt(parts[1], 10) - 1];
    return `${m} ${parts[2]}`;
  }
  return d;
}

export default function Sidebar({ 
  activeTab, 
  onSelectTab, 
  reviews = [], 
  selectedDate, 
  onSelectDate 
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo-icon">N</div>
        <div>
          <span className="sidebar-brand">NEXUS</span>
          <span className="sidebar-sub-brand">MARKET INTEL</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-group">
          <div className="nav-section-title font-mono">Platform Pillars</div>
          
          <button 
            className={`nav-item ${activeTab === 'intel' ? 'active' : ''}`}
            onClick={() => onSelectTab('intel')}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            Market Intelligence
          </button>

          <button 
            className={`nav-item ${activeTab === 'memory' ? 'active' : ''}`}
            onClick={() => onSelectTab('memory')}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            Memory & Heuristics
          </button>

          <button 
            className={`nav-item ${activeTab === 'telemetry' ? 'active' : ''}`}
            onClick={() => onSelectTab('telemetry')}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Execution Telemetry
          </button>
        </div>
      </nav>

      {/* Interactive Quick Session Switcher (useful across intelligence views) */}
      {reviews.length > 0 && (
        <div className="sidebar-sessions">
          <div className="sidebar-session-title font-mono">Audit Sessions</div>
          {reviews.slice(0, 7).map((r) => {
            const isSel = (!selectedDate && r.date === reviews[0]?.date) || selectedDate === r.date;
            return (
              <button
                key={r.date}
                className={`sidebar-session-item ${isSel ? 'active' : ''}`}
                onClick={() => {
                  if (activeTab !== 'intel') onSelectTab('intel');
                  if (onSelectDate) onSelectDate(r.date);
                }}
              >
                <span className="font-mono">{formatHeaderDate(r.date)}</span>
                <span className={`font-mono text-xs ${r.isPendingReview ? 'text-warning' : (r.ihsg_correct ? 'text-matched' : 'text-missed')}`}>
                  {r.isPendingReview ? '⏳ Live' : (r.ihsg_correct ? '● Hit' : '▲ Miss')}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Minimal Footer Only (Clean institutional status) */}
      <div className="sidebar-footer">
        <div className="vault-status">
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
          <span className="font-mono text-xs">v2.4 Core Online</span>
        </div>
      </div>
    </aside>
  );
}
