'use client';
import MarketOverviewKPIs from './MarketOverviewKPIs';
import MorningBriefEntry from './MorningBriefEntry';
import VarianceBridge from './VarianceBridge';
import SectorAssetTape from './SectorAssetTape';
import HistoricalLedger from './HistoricalLedger';

export default function MarketIntelligence({ 
  dashboard, 
  activeReview, 
  isHistorical, 
  onSelectSession, 
  onResetSelectedDate 
}) {
  if (!dashboard) return null;

  return (
    <div className="tab-pane-root">
      <div className="section-eyebrow font-mono">01 · MARKET OVERVIEW &amp; TELEMETRY</div>
      <MarketOverviewKPIs dashboard={dashboard} />

      <MorningBriefEntry activeReview={activeReview} />

      <div className="section-eyebrow font-mono" style={{ marginTop: '28px' }}>
        02 · {isHistorical ? 'HISTORICAL SESSION AUDIT' : 'POST-MARKET EVALUATION & ATTRIBUTION'}
      </div>
      <VarianceBridge 
        activeReview={activeReview} 
        isHistorical={isHistorical} 
        onResetSelectedDate={onResetSelectedDate}
        latestDate={dashboard.latest?.date}
      />

      <SectorAssetTape review={activeReview} />

      <div className="section-eyebrow font-mono" style={{ marginTop: '36px' }}>
        03 · AUDITABLE EXECUTION ARCHIVE
      </div>
      <HistoricalLedger 
        reviews={dashboard.reviews}
        activeReview={activeReview}
        onSelectSession={onSelectSession}
        wins={dashboard.wins}
        evaluatedCount={dashboard.evaluatedCount}
      />
    </div>
  );
}
