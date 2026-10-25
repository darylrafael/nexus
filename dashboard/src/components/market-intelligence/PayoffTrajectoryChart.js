'use client';

import { useMemo, useState } from 'react';

export default function PayoffTrajectoryChart({ reviews = [], payoffStats = {}, onSelectDate }) {
  const [selectedStrategy, setSelectedStrategy] = useState('combined'); // 'combined' | 'short' | 'long'
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // Compute chronological cumulative trajectories
  const trajectoryData = useMemo(() => {
    const chronological = [...reviews]
      .filter((r) => !r.isPendingReview && r.ihsg_actual_pct !== null && r.ihsg_actual_pct !== undefined)
      .sort((a, b) => a.date.localeCompare(b.date));

    let cumLong = 0;
    let cumShort = 0;
    let cumCombined = 0;
    const points = [];

    for (let idx = 0; idx < chronological.length; idx++) {
      const r = chronological[idx];
      const returnPct = Number(r.ihsg_actual_pct) || 0;
      const returnBps = Math.round(returnPct * 100); // 1% = 100 bps
      const pred = (r.ihsg_predicted || '').toLowerCase();

      let tradeType = 'none';
      let dailyBps = 0;

      if (pred.includes('bullish') || pred.includes('up')) {
        tradeType = 'long';
        dailyBps = returnBps;
        cumLong += dailyBps;
        cumCombined += dailyBps;
      } else if (pred.includes('bearish') || pred.includes('down')) {
        tradeType = 'short';
        dailyBps = -returnBps;
        cumShort += dailyBps;
        cumCombined += dailyBps;
      }

      points.push({
        date: r.date,
        shortDate: r.date.slice(5),
        tradeType,
        pred: r.ihsg_predicted,
        actual: r.ihsg_actual,
        actualPct: returnPct,
        dailyBps,
        cumLong,
        cumShort,
        cumCombined,
        correct: r.ihsg_correct,
        stepIndex: idx + 1,
      });
    }

    return points;
  }, [reviews]);

  if (trajectoryData.length < 2) {
    return null;
  }

  const width = 760;
  const height = 180;
  const padding = { top: 18, right: 26, bottom: 30, left: 54 };

  const activeKey = selectedStrategy === 'combined' ? 'cumCombined' : selectedStrategy === 'short' ? 'cumShort' : 'cumLong';

  const values = trajectoryData.map((d) => d[activeKey]);
  const minVal = Math.min(0, ...values);
  const maxVal = Math.max(0, ...values);
  const range = maxVal - minVal || 100;
  const yPadding = range * 0.12;
  const yMin = minVal - yPadding;
  const yMax = maxVal + yPadding;

  const getX = (index) => {
    return padding.left + (index / (trajectoryData.length - 1)) * (width - padding.left - padding.right);
  };

  const getY = (val) => {
    return height - padding.bottom - ((val - yMin) / (yMax - yMin)) * (height - padding.top - padding.bottom);
  };

  const zeroY = getY(0);

  const pointsString = trajectoryData
    .map((d, i) => `${getX(i).toFixed(1)},${getY(d[activeKey]).toFixed(1)}`)
    .join(' ');

  const areaString = `${getX(0).toFixed(1)},${zeroY.toFixed(1)} ${pointsString} ${getX(trajectoryData.length - 1).toFixed(1)},${zeroY.toFixed(1)}`;

  const latestVal = values[values.length - 1] || 0;
  const isPositive = latestVal >= 0;

  const yTicks = [yMin, yMin + (yMax - yMin) * 0.33, yMin + (yMax - yMin) * 0.66, yMax];

  const lastPt = trajectoryData[trajectoryData.length - 1] || {};
  const combinedBps = Number(payoffStats?.long_short_total_bps ?? lastPt.cumCombined ?? 0);
  const shortBps = Number(payoffStats?.short_only_total_bps ?? lastPt.cumShort ?? 0);
  const longBps = Number(payoffStats?.long_only_total_bps ?? lastPt.cumLong ?? 0);
  const fmtPct = (bps) => `${bps >= 0 ? '+' : ''}${(bps / 100).toFixed(1)}%`;
  const fmtBps = (bps) => `${bps >= 0 ? '+' : ''}${bps} bps`;

  return (
    <div className="payoff-trajectory-module" style={{ padding: '8px 0 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="font-mono text-xs font-bold" style={{ color: 'var(--accent-cyan)', letterSpacing: '0.04em' }}>
            CUMULATIVE PAYOFF CURVE
          </span>
          <span className="font-mono text-xs" style={{ background: 'var(--surface-well)', padding: '2px 6px', borderRadius: '3px' }}>
            {trajectoryData.length} Sessions · 100 bps = 1%
          </span>
        </div>

        <div style={{ display: 'flex', gap: '4px', background: 'var(--surface-well)', padding: '3px', borderRadius: '6px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => setSelectedStrategy('combined')}
            title={`Combined Long/Short: ${fmtBps(combinedBps)} (${fmtPct(combinedBps)})`}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              minHeight: '36px',
              background: selectedStrategy === 'combined' ? 'var(--surface)' : 'transparent',
              color: selectedStrategy === 'combined' ? 'var(--text-primary)' : 'var(--text-tertiary)',
              boxShadow: selectedStrategy === 'combined' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            Combined ({fmtPct(combinedBps)})
          </button>
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => setSelectedStrategy('short')}
            title={`Theoretical Short-Only: ${fmtBps(shortBps)} (${fmtPct(shortBps)})`}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              minHeight: '36px',
              background: selectedStrategy === 'short' ? 'var(--surface)' : 'transparent',
              color: selectedStrategy === 'short' ? 'var(--text-primary)' : 'var(--text-tertiary)',
              boxShadow: selectedStrategy === 'short' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            Short ({fmtPct(shortBps)})
          </button>
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => setSelectedStrategy('long')}
            title={`Long-Only: ${fmtBps(longBps)} (${fmtPct(longBps)})`}
            style={{
              padding: '6px 10px',
              borderRadius: '4px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              minHeight: '36px',
              background: selectedStrategy === 'long' ? 'var(--surface)' : 'transparent',
              color: selectedStrategy === 'long' ? 'var(--text-primary)' : 'var(--text-tertiary)',
              boxShadow: selectedStrategy === 'long' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            Long ({fmtPct(longBps)})
          </button>
        </div>
      </div>

      <div
        tabIndex={0}
        role="region"
        aria-label="Interactive performance trajectory chart"
        style={{ position: 'relative', width: '100%', overflowX: 'auto' }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', minWidth: '540px', display: 'block', overflow: 'visible' }}
        >
          <defs>
            <linearGradient id="payoffPositiveGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--matched-text)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--matched-text)" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="payoffNegativeGrad" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="var(--missed-text)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--missed-text)" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {yTicks.map((tickVal, i) => {
            const yPos = getY(tickVal);
            return (
              <g key={i}>
                <line
                  x1={padding.left}
                  y1={yPos}
                  x2={width - padding.right}
                  y2={yPos}
                  stroke="var(--border-subtle)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 8}
                  y={yPos + 4}
                  fill="var(--text-tertiary)"
                  fontSize="12"
                  fontFamily="var(--font-mono)"
                  textAnchor="end"
                >
                  {tickVal > 0 ? `+${(tickVal / 100).toFixed(1)}%` : `${(tickVal / 100).toFixed(1)}%`}
                </text>
              </g>
            );
          })}

          <line
            x1={padding.left}
            y1={zeroY}
            x2={width - padding.right}
            y2={zeroY}
            stroke="var(--border-strong)"
            strokeWidth="1.5"
            strokeDasharray="4 2"
          />

          <polygon
            points={areaString}
            fill={isPositive ? 'url(#payoffPositiveGrad)' : 'url(#payoffNegativeGrad)'}
          />

          <polyline
            fill="none"
            stroke={isPositive ? 'var(--matched-text)' : 'var(--missed-text)'}
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={pointsString}
          />

          {trajectoryData.map((d, i) => {
            const cx = getX(i);
            const cy = getY(d[activeKey]);
            const isHovered = hoveredPoint?.date === d.date;

            return (
              <g
                key={d.date}
                onMouseEnter={() => setHoveredPoint(d)}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 6 : 3.5}
                  fill={d.correct ? 'var(--matched-text)' : 'var(--missed-text)'}
                  stroke="var(--surface)"
                  strokeWidth="1.5"
                  style={{ transition: 'r 0.15s ease' }}
                />
                {(i % 4 === 0 || i === trajectoryData.length - 1) && (
                  <text
                    x={cx}
                    y={height - 10}
                    fill="var(--text-tertiary)"
                    fontSize="12"
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                  >
                    {d.shortDate}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {hoveredPoint && (
          <div
            style={{
              position: 'absolute',
              top: '10px',
              right: '16px',
              background: 'var(--surface-well)',
              border: '1px solid var(--border-strong)',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              boxShadow: 'var(--shadow-raised)',
              pointerEvents: 'none',
              zIndex: 20,
            }}
          >
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '3px' }}>
              Sesi: {hoveredPoint.date}
            </div>
            <div>
              Prediksi: <strong style={{ color: hoveredPoint.pred === 'Bullish' ? 'var(--matched-text)' : 'var(--missed-text)' }}>{hoveredPoint.pred}</strong>
              {' · '}Realisasi: <strong>{hoveredPoint.actualPct > 0 ? `+${hoveredPoint.actualPct}%` : `${hoveredPoint.actualPct}%`}</strong>
            </div>
            <div>
              Hasil Hari Ini: <strong style={{ color: hoveredPoint.dailyBps >= 0 ? 'var(--matched-text)' : 'var(--missed-text)' }}>
                {hoveredPoint.dailyBps >= 0 ? `+${(hoveredPoint.dailyBps / 100).toFixed(2)}%` : `${(hoveredPoint.dailyBps / 100).toFixed(2)}%`} ({hoveredPoint.dailyBps >= 0 ? `+${hoveredPoint.dailyBps}` : hoveredPoint.dailyBps} bps)
              </strong>
            </div>
            <div style={{ borderTop: '1px solid var(--border-subtle)', marginTop: '4px', paddingTop: '4px' }}>
              Total Akumulasi: <strong style={{ color: hoveredPoint[activeKey] >= 0 ? 'var(--matched-text)' : 'var(--missed-text)' }}>
                {hoveredPoint[activeKey] >= 0 ? `+${(hoveredPoint[activeKey] / 100).toFixed(2)}%` : `${(hoveredPoint[activeKey] / 100).toFixed(2)}%`} ({hoveredPoint[activeKey] >= 0 ? `+${hoveredPoint[activeKey]}` : hoveredPoint[activeKey]} bps)
              </strong>
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px', color: 'var(--text-tertiary)', marginTop: '8px', flexWrap: 'wrap', gap: '6px' }}>
        <span>● Hijau = Hit · ● Merah = Miss · <strong>100 bps = 1.00%</strong></span>
        <span>* Cash index simulation sebelum biaya transaksi</span>
      </div>
    </div>
  );
}
