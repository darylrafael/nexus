'use client';

function formatHeaderDate(d) {
  if (!d) return '—';
  const parts = d.split('-');
  if (parts.length === 3) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const m = months[parseInt(parts[1], 10) - 1];
    return `${m} ${parts[2]}, ${parts[0]}`;
  }
  return d;
}

export default function MemoryKPIs({ stats }) {
  if (!stats) return null;

  const {
    totalLessons = 0,
    activeHeuristics = 0,
    supersededHeuristics = 0,
    blindSpotsCount = 0,
    lastCycle = ''
  } = stats;

  return (
    <section className="kpi-row">
      {/* Card 1: Lessons Accumulated */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Total Lessons</span>
          <span className="kpi-target-tag font-mono">Knowledge Store</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono">{totalLessons}</div>
          <span className="kpi-tag-visual font-mono text-xs">Accumulated</span>
        </div>
        <div className="kpi-context">
          <span>Formulated across closed-loop evening RCAs</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '100%' }} />
          </div>
        </div>
      </div>

      {/* Card 2: Active Heuristics */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Active Heuristics</span>
          <span className="kpi-target-tag font-mono">Prompt Injected</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono text-matched">{activeHeuristics}</div>
          <span className="kpi-tag-visual font-mono text-xs">
            {supersededHeuristics} Superseded
          </span>
        </div>
        <div className="kpi-context">
          <span>Validated rules actively constraining morning briefs</span>
          <div className="kpi-mini-bar">
            <div 
              className="kpi-mini-fill" 
              style={{ width: `${totalLessons > 0 ? (activeHeuristics / totalLessons) * 100 : 50}%` }} 
            />
          </div>
        </div>
      </div>

      {/* Card 3: Recurring Blind Spots */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Blind Spots</span>
          <span className="kpi-target-tag font-mono">Recurring Risks</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono text-warning">{blindSpotsCount}</div>
          <span className="kpi-tag-visual font-mono text-xs">Monitored</span>
        </div>
        <div className="kpi-context">
          <span>Macro shock categories with historical error spikes</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '60%' }} />
          </div>
        </div>
      </div>

      {/* Card 4: Last Learning Cycle */}
      <div className="kpi-card">
        <div className="kpi-top">
          <span className="kpi-label font-mono">Learning Cycle</span>
          <span className="kpi-target-tag font-mono">Reflection Run</span>
        </div>
        <div className="kpi-val-row">
          <div className="kpi-value font-mono text-sm" style={{ fontSize: '18px', paddingTop: '6px' }}>
            {formatHeaderDate(lastCycle)}
          </div>
          <span className="kpi-tag-visual font-mono text-xs text-matched">Synced</span>
        </div>
        <div className="kpi-context">
          <span>Latest post-market attribution run date</span>
          <div className="kpi-mini-bar">
            <div className="kpi-mini-fill" style={{ width: '100%' }} />
          </div>
        </div>
      </div>
    </section>
  );
}
