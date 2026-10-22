'use client';

export default function ConfidenceCalibrationVisual({ calibration = {} }) {
  const statedConf = Number(calibration.average_stated_confidence_pct ?? 80.5);
  const realizedHit = Number(calibration.realized_hit_rate_pct ?? 45.0);
  const calibratedConf = Number(calibration.calibrated_confidence_pct ?? 48.3);
  const brierScore = Number(calibration.brier_score ?? 0.3798);
  const sampleN = calibration.sample_size_n ?? 20;

  // Brier score gauge indicator (0.00 is perfect, 0.25 is random coin flip, >0.25 is overconfident)
  const brierColor = brierScore <= 0.25 ? 'var(--matched-text)' : 'var(--warning-text)';

  return (
    <div className="confidence-calibration-module" style={{
      padding: '10px 0 0',
      marginTop: '6px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
        <div>
          <span className="font-mono text-xs font-bold" style={{ color: 'var(--accent-cyan)', letterSpacing: '0.05em' }}>
            PROBABILISTIC CALIBRATION &amp; BRIER SCORE
          </span>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Shrinkage model dampens LLM overconfidence into empirical risk-adjusted probabilities.
          </div>
        </div>
        <span className="font-mono text-xs font-bold" style={{
          background: 'var(--surface-well)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-primary)',
          padding: '4px 8px',
          borderRadius: '4px',
        }}>
          Prior N₀=30 · Cap 55.0%
        </span>
      </div>

      {/* 3-Tier Comparison Cards */}
      <div className="scorecard-kpi-grid">
        {/* Stated Confidence Card */}
        <div style={{
          background: 'var(--surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '12px 14px',
        }}>
          <div className="font-mono text-xs text-muted font-bold">MODEL STATED CONFIDENCE</div>
          <div className="font-mono text-xl font-bold" style={{ color: 'var(--text-tertiary)', margin: '4px 0 2px' }}>
            {statedConf}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Raw uncalibrated LLM output across n={sampleN} sessions. Tends toward systemic overconfidence.
          </div>
        </div>

        {/* Realized Hit Rate Card */}
        <div style={{
          background: 'var(--surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '12px 14px',
        }}>
          <div className="font-mono text-xs text-muted font-bold">REALIZED DIRECTION ACCURACY</div>
          <div className="font-mono text-xl font-bold" style={{ color: 'var(--text-primary)', margin: '4px 0 2px' }}>
            {realizedHit}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Empirical ground truth hit rate realized on the Jakarta Composite Index.
          </div>
        </div>

        {/* Calibrated Confidence Card */}
        <div style={{
          background: 'var(--surface-well)',
          border: '1.5px solid var(--matched-text)',
          borderRadius: '6px',
          padding: '12px 14px',
          boxShadow: '0 0 10px rgba(0, 230, 118, 0.1)',
        }}>
          <div className="font-mono text-xs font-bold" style={{ color: 'var(--matched-text)' }}>
            CALIBRATED OPERATING CONFIDENCE
          </div>
          <div className="font-mono text-xl font-bold" style={{ color: 'var(--matched-text)', margin: '4px 0 2px' }}>
            {calibratedConf}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            Bayesian shrinkage: weights empirical hit rate (w=0.67) against conservative prior (55%).
          </div>
        </div>

        {/* Brier Score Card */}
        <div style={{
          background: 'var(--surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '12px 14px',
        }}>
          <div className="font-mono text-xs text-muted font-bold">BRIER SCORE (PROBABILISTIC ERROR)</div>
          <div className="font-mono text-xl font-bold" style={{ color: brierColor, margin: '4px 0 2px' }}>
            {brierScore.toFixed(4)}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            0.00 = perfect clairvoyance, 0.25 = 50/50 coin toss. {brierScore > 0.25 ? 'High score indicates overconfidence penalty.' : 'Well-calibrated.'}
          </div>
        </div>
      </div>
    </div>
  );
}
