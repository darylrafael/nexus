'use client';

export default function ConfidenceCalibrationVisual({ calibration = {} }) {
  const statedConf = calibration.average_stated_confidence_pct != null ? Number(calibration.average_stated_confidence_pct) : null;
  const realizedHit = calibration.realized_hit_rate_pct != null ? Number(calibration.realized_hit_rate_pct) : null;
  const calibratedConf = calibration.calibrated_confidence_pct != null ? Number(calibration.calibrated_confidence_pct) : null;
  const brierScore = calibration.brier_score != null ? Number(calibration.brier_score) : null;
  const sampleN = calibration.sample_size_n ?? 0;
  const empWeight = Number(calibration.empirical_weight ?? Math.min(sampleN / 30, 1.0)).toFixed(2);
  const priorN0 = calibration.prior_strength_n0 ?? 30;
  const priorCap = Number(calibration.prior_pct ?? 55.0).toFixed(1);

  const brierColor = brierScore !== null && brierScore <= 0.25 ? 'var(--matched-text)' : 'var(--warning-text)';

  return (
    <div className="confidence-calibration-module" style={{ padding: '8px 0 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
        <span className="font-mono text-xs font-bold" style={{ color: 'var(--accent-cyan)', letterSpacing: '0.05em' }}>
          CONFIDENCE CALIBRATION &amp; BRIER SCORE
        </span>
        <span className="font-mono text-xs font-bold" style={{
          background: 'var(--surface-well)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-primary)',
          padding: '3px 8px',
          borderRadius: '4px',
        }}>
          Prior N₀={priorN0} · Cap {priorCap}% · w={empWeight}
        </span>
      </div>

      <div className="scorecard-kpi-grid">
        <div style={{
          background: 'var(--surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '10px 12px',
        }}>
          <div className="font-mono text-xs text-muted font-bold">RAW LLM CONFIDENCE</div>
          <div className="font-mono text-xl font-bold" style={{ color: 'var(--text-tertiary)', margin: '4px 0 2px' }}>
            {statedConf !== null ? `${statedConf}%` : '—'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
            Uncalibrated average across n={sampleN} sessions.
          </div>
        </div>

        <div style={{
          background: 'var(--surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '10px 12px',
        }}>
          <div className="font-mono text-xs text-muted font-bold">REALIZED HIT RATE</div>
          <div className="font-mono text-xl font-bold" style={{ color: 'var(--text-primary)', margin: '4px 0 2px' }}>
            {realizedHit !== null ? `${realizedHit}%` : '—'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
            Actual IHSG direction accuracy on IDX close.
          </div>
        </div>

        <div style={{
          background: 'var(--surface-well)',
          border: '1.5px solid var(--matched-text)',
          borderRadius: '6px',
          padding: '10px 12px',
        }}>
          <div className="font-mono text-xs font-bold" style={{ color: 'var(--matched-text)' }}>
            CALIBRATED CONFIDENCE
          </div>
          <div className="font-mono text-xl font-bold" style={{ color: 'var(--matched-text)', margin: '4px 0 2px' }}>
            {calibratedConf !== null ? `${calibratedConf}%` : '—'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
            Shrinkage blend (w={empWeight} empirical, {(1 - Number(empWeight)).toFixed(2)} prior).
          </div>
        </div>

        <div style={{
          background: 'var(--surface-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '6px',
          padding: '10px 12px',
        }}>
          <div className="font-mono text-xs text-muted font-bold">BRIER SCORE</div>
          <div className="font-mono text-xl font-bold" style={{ color: brierColor, margin: '4px 0 2px' }}>
            {brierScore !== null ? brierScore.toFixed(4) : '—'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
            0.00 = perfect · 0.25 = random · {brierScore !== null && brierScore > 0.25 ? 'Overconfident (>0.25)' : 'Calibrated'}
          </div>
        </div>
      </div>
    </div>
  );
}
