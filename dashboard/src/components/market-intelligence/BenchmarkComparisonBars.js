'use client';

export default function BenchmarkComparisonBars({ nStats = {} }) {
  const modelPct = Number(nStats.direction_accuracy_pct ?? 45.0);
  const correctCount = nStats.direction_correct_count ?? 9;
  const totalSessions = nStats.direction_scorable_sessions ?? 20;

  const baselines = nStats.baselines || {};
  const bearishPct = Number(baselines.always_bearish_pct ?? 65.0);
  const bearishCount = baselines.always_bearish_count ?? 13;
  const bearishTotal = baselines.always_bearish_total ?? 20;

  const persistencePct = Number(baselines.persistence_pct ?? 52.6);
  const persistenceCount = baselines.persistence_correct_count ?? 10;
  const persistenceTotal = baselines.persistence_scorable_sessions ?? 19;

  const bullishPct = Number(baselines.always_bullish_pct ?? 30.0);
  const bullishCount = baselines.always_bullish_count ?? 6;
  const bullishTotal = baselines.always_bullish_total ?? 20;

  const ci = nStats.direction_ci_95 || { lower_pct: 25.8, upper_pct: 65.8 };
  const lowerCI = Number(ci.lower_pct ?? 25.8);
  const upperCI = Number(ci.upper_pct ?? 65.8);

  const deltaBearish = (modelPct - bearishPct).toFixed(1);
  const deltaPersistence = (modelPct - persistencePct).toFixed(1);
  const deltaBullish = (modelPct - bullishPct).toFixed(1);

  const items = [
    {
      id: 'bearish',
      label: 'ALWAYS-BEARISH (DOWN ONLY)',
      score: bearishPct,
      count: `${bearishCount}/${bearishTotal}`,
      delta: `${deltaBearish}%`,
      deltaType: 'lag',
      explanation: 'Prevailing IDX downtrend favored short calls',
      barColor: '#ef4444',
      isModel: false,
    },
    {
      id: 'persistence',
      label: 'PERSISTENCE (REPEAT PRIOR DAY)',
      score: persistencePct,
      count: `${persistenceCount}/${persistenceTotal}`,
      delta: `${deltaPersistence}%`,
      deltaType: 'lag',
      explanation: 'Exploited 2-day consecutive directional momentum',
      barColor: '#f59e0b',
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
    {
      id: 'bullish',
      label: 'ALWAYS-BULLISH (UP ONLY)',
      score: bullishPct,
      count: `${bullishCount}/${bullishTotal}`,
      delta: `+${deltaBullish}%`,
      deltaType: 'lead',
      explanation: 'Model outperforms permanent retail long bias',
      barColor: '#3b82f6',
      isModel: false,
    },
  ];

  return (
    <div className="benchmark-comparison-module" style={{
      padding: '10px 0 0',
      marginTop: '6px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
        <div>
          <span className="font-mono text-xs font-bold" style={{ color: 'var(--accent-cyan)', letterSpacing: '0.05em' }}>
            EMPIRICAL NAIVE BASELINE BENCHMARKS
          </span>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Quantitative comparison against naive non-learning strategies across all {totalSessions} scored sessions.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <span className="font-mono text-xs font-bold" style={{
            background: 'var(--warning-bg)',
            border: '1px solid var(--warning-border)',
            color: 'var(--warning-text)',
            padding: '4px 8px',
            borderRadius: '4px',
          }}>
            Sample n={totalSessions} &lt; 30 (Wide Uncertainty Band)
          </span>
        </div>
      </div>

      {/* Benchmark Progress Bars */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {items.map((item) => {
          return (
            <div
              key={item.id}
              style={{
                background: item.isModel ? 'var(--surface-well)' : 'var(--surface-subtle)',
                border: item.isModel ? '1.5px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                borderRadius: '6px',
                padding: '10px 14px',
                position: 'relative',
                boxShadow: item.isModel ? '0 0 12px rgba(8, 145, 178, 0.12)' : 'none',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="font-mono text-xs font-bold" style={{ color: item.isModel ? 'var(--accent-cyan)' : 'var(--text-primary)' }}>
                    {item.label}
                  </span>
                  <span className="font-mono text-xs text-muted">
                    ({item.count} sessions)
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="font-mono text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                    {item.score}%
                  </span>
                  {item.deltaType === 'lag' && (
                    <span className="font-mono text-xs text-missed font-semibold">
                      Model lags by {item.delta}
                    </span>
                  )}
                  {item.deltaType === 'lead' && (
                    <span className="font-mono text-xs text-matched font-semibold">
                      Model leads by {item.delta}
                    </span>
                  )}
                </div>
              </div>

              {/* Progress Bar Track */}
              <div style={{
                position: 'relative',
                height: '10px',
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

              {/* Overlay CI on Model Bar */}
              {item.isModel && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {item.explanation}
                  </span>
                  <span style={{ color: 'var(--accent-cyan)' }}>
                    CI Span: {(upperCI - lowerCI).toFixed(1)}%
                  </span>
                </div>
              )}
              {!item.isModel && (
                <div style={{ marginTop: '4px', fontSize: '12px', color: 'var(--text-tertiary)' }}>
                  {item.explanation}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
