'use client';

export default function BenchmarkComparisonBars({ nStats = {} }) {
  const modelPct = Number(nStats.direction_accuracy_pct ?? 0);
  const correctCount = nStats.direction_correct_count ?? 0;
  const totalSessions = nStats.direction_scorable_sessions ?? 0;

  const baselines = nStats.baselines || {};
  const bearishPct = Number(baselines.always_bearish_pct ?? 0);
  const bearishCount = baselines.always_bearish_count ?? 0;
  const bearishTotal = baselines.always_bearish_total ?? totalSessions;

  const persistencePct = Number(baselines.persistence_pct ?? 0);
  const persistenceCount = baselines.persistence_correct_count ?? 0;
  const persistenceTotal = baselines.persistence_scorable_sessions ?? Math.max(0, totalSessions - 1);

  const bullishPct = Number(baselines.always_bullish_pct ?? 0);
  const bullishCount = baselines.always_bullish_count ?? 0;
  const bullishTotal = baselines.always_bullish_total ?? totalSessions;

  const ci = nStats.direction_ci_95 || { lower_pct: 0, upper_pct: 0 };
  const lowerCI = Number(ci.lower_pct ?? 0);
  const upperCI = Number(ci.upper_pct ?? 0);

  const makeDelta = (basePct, leadNote, lagNote) => {
    const diff = Number((modelPct - basePct).toFixed(1));
    const isLead = diff >= 0;
    return {
      delta: isLead ? `+${diff.toFixed(1)}%` : `${diff.toFixed(1)}%`,
      deltaType: isLead ? 'lead' : 'lag',
      explanation: isLead ? leadNote : lagNote,
    };
  };

  const bearishMeta = makeDelta(
    bearishPct,
    'Model outperforms permanent short bias',
    'Prevailing IDX downtrend favored passive short calls'
  );
  const persistenceMeta = makeDelta(
    persistencePct,
    'Model outperforms prior-day momentum',
    'Consecutive 2-day directional momentum led in sample'
  );
  const bullishMeta = makeDelta(
    bullishPct,
    'Model outperforms permanent long bias',
    'Passive long bias led model in current sample'
  );

  const items = [
    {
      id: 'persistence',
      label: 'PERSISTENCE (REPEAT PRIOR DAY)',
      score: persistencePct,
      count: `${persistenceCount}/${persistenceTotal}`,
      ...persistenceMeta,
      barColor: '#f59e0b',
      isModel: false,
    },
    {
      id: 'bearish',
      label: 'ALWAYS-BEARISH (DOWN ONLY)',
      score: bearishPct,
      count: `${bearishCount}/${bearishTotal}`,
      ...bearishMeta,
      barColor: '#ef4444',
      isModel: false,
    },
    {
      id: 'bullish',
      label: 'ALWAYS-BULLISH (UP ONLY)',
      score: bullishPct,
      count: `${bullishCount}/${bullishTotal}`,
      ...bullishMeta,
      barColor: '#3b82f6',
      isModel: false,
    },
    {
      id: 'model',
      label: 'NEXUS ACTIVE MODEL (HEADLINE CALL)',
      score: modelPct,
      count: `${correctCount}/${totalSessions}`,
      delta: 'Active Model',
      deltaType: 'neutral',
      explanation: `95% Wilson CI: [${lowerCI}%, ${upperCI}%]`,
      barColor: 'var(--accent-cyan)',
      isModel: true,
    },
  ];

  return (
    <div className="benchmark-comparison-module" style={{ padding: '8px 0 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
        <span className="font-mono text-xs font-bold" style={{ color: 'var(--accent-cyan)', letterSpacing: '0.05em' }}>
          NAIVE BASELINE BENCHMARKS (n={totalSessions})
        </span>
        {totalSessions < 30 && (
          <span className="font-mono text-xs font-bold" style={{
            background: 'var(--warning-bg)',
            border: '1px solid var(--warning-border)',
            color: 'var(--warning-text)',
            padding: '3px 8px',
            borderRadius: '4px',
          }}>
            n={totalSessions} &lt; 30 (Wide CI Band)
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {items.map((item) => (
          <div
            key={item.id}
            style={{
              background: item.isModel ? 'var(--surface-well)' : 'var(--surface-subtle)',
              border: item.isModel ? '1.5px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '9px 12px',
              position: 'relative',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px', flexWrap: 'wrap', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="font-mono text-xs font-bold" style={{ color: item.isModel ? 'var(--accent-cyan)' : 'var(--text-primary)' }}>
                  {item.label}
                </span>
                <span className="font-mono text-xs text-muted">
                  ({item.count})
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="font-mono text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                  {item.score}%
                </span>
                {item.deltaType === 'lag' && (
                  <span className="font-mono text-xs text-missed font-semibold">
                    Model {item.delta}
                  </span>
                )}
                {item.deltaType === 'lead' && (
                  <span className="font-mono text-xs text-matched font-semibold">
                    Model {item.delta}
                  </span>
                )}
              </div>
            </div>

            <div style={{
              position: 'relative',
              height: '8px',
              background: 'var(--canvas)',
              borderRadius: '999px',
              overflow: 'hidden',
              border: '1px solid var(--border-subtle)',
            }}>
              <div
                style={{
                  height: '100%',
                  width: `${Math.min(100, Math.max(0, item.score))}%`,
                  background: item.barColor,
                  borderRadius: '999px',
                  transition: 'width 0.4s ease',
                }}
              />
            </div>

            {item.isModel ? (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '5px', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{item.explanation}</span>
                <span style={{ color: 'var(--accent-cyan)' }}>CI Span: {(upperCI - lowerCI).toFixed(1)}%</span>
              </div>
            ) : (
              <div style={{ marginTop: '4px', fontSize: '11px', color: 'var(--text-tertiary)' }}>
                {item.explanation}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
