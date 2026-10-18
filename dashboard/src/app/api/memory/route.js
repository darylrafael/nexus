import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getRunsDirectory } from '@/lib/nexusData';

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const demoParam = url.searchParams.get('demo');
    const isDemo = demoParam === 'true' || (demoParam !== 'false' && process.env.NEXUS_DEMO_MODE === 'true');
    const runsDir = getRunsDirectory(isDemo);

    let allLessons = [];
    let missedFactorCounts = {};
    let lastUpdated = '';

    // 1. Read global stats artifact if present
    const globalStatsPath = path.join(runsDir, 'global', 'nexus_stats.json');
    if (fs.existsSync(globalStatsPath)) {
      try {
        const globalData = JSON.parse(fs.readFileSync(globalStatsPath, 'utf8'));
        allLessons = globalData.all_lessons || [];
        missedFactorCounts = globalData.missed_factor_counts || {};
        lastUpdated = globalData.last_updated || '';
      } catch (e) {
        console.error('Failed to parse nexus_stats.json', e);
      }
    }

    // 2. Scan daily runs to extract lessons, outcomes, and build evidence provenance
    const dailyReviews = [];
    if (fs.existsSync(runsDir)) {
      const minDate = process.env.NEXUS_MIN_DATE || null;
      const dates = fs.readdirSync(runsDir).filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && (!minDate || d >= minDate));
      dates.sort((a, b) => b.localeCompare(a)); // Newest first

      for (const date of dates) {
        const reviewFile = path.join(runsDir, date, 'evening_review.json');
        if (fs.existsSync(reviewFile)) {
          try {
            const data = JSON.parse(fs.readFileSync(reviewFile, 'utf8'));
            dailyReviews.push({ date, ...data });

            // If global stats was empty, accumulate lessons directly
            if (allLessons.length === 0 && Array.isArray(data.lessons)) {
              data.lessons.forEach(l => {
                if (l && !allLessons.includes(l)) allLessons.push(l);
              });
            }

            // Accumulate RCA factors if missedFactorCounts empty
            if (Object.keys(missedFactorCounts).length === 0) {
              const factors = [
                ...(data.rca_unanticipated || []),
                ...(data.rca_underestimated || [])
              ];
              factors.forEach(f => {
                if (f) missedFactorCounts[f] = (missedFactorCounts[f] || 0) + 1;
              });
            }

            if (!lastUpdated) lastUpdated = date;
          } catch (e) {
            console.error(`Failed parsing ${reviewFile}`, e);
          }
        }
      }
    }

    // 3. Format Recurring Blind Spots (sorted descending by count)
    const blindSpots = Object.entries(missedFactorCounts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);

    // 4. Trace Provenance & Ground Heuristics in Verified Artifact Evidence
    const heuristics = allLessons.map((ruleText, idx) => {
      const evidence = [];
      let originDate = '';
      let lastObserved = '';

      // Find all sessions mentioning this rule (dailyReviews is newest-first)
      const matchingReviews = dailyReviews.filter(rev =>
        (rev.lessons || []).some(l => l.includes(ruleText) || ruleText.includes(l))
      );
      if (matchingReviews.length > 0) {
        originDate = matchingReviews[matchingReviews.length - 1].date; // earliest session = when rule was formulated
        lastObserved = matchingReviews[0].date;
      }

      // Categorize rule deterministically
      let category = 'Market Sentiment';
      const rLower = ruleText.toLowerCase();
      if (rLower.includes('bi rate') || rLower.includes('bunga') || rLower.includes('fed') || rLower.includes('treasury') || rLower.includes('yield')) {
        category = 'Monetary Policy';
      } else if (rLower.includes('rupiah') || rLower.includes('usd') || rLower.includes('kurs') || rLower.includes('valas')) {
        category = 'Foreign Exchange';
      } else if (rLower.includes('minyak') || rLower.includes('oil') || rLower.includes('cpo') || rLower.includes('komoditas') || rLower.includes('energi') || rLower.includes('batu bara') || rLower.includes('coal') || rLower.includes('nikel')) {
        category = 'Commodities';
      } else if (rLower.includes('asing') || rLower.includes('outflow') || rLower.includes('inflow') || rLower.includes('flow') || rLower.includes('akumulasi') || rLower.includes('distribusi')) {
        category = 'Liquidity & Flows';
      } else if (rLower.includes('pe') || rLower.includes('p/e') || rLower.includes('valuasi') || rLower.includes('demo') || rLower.includes('buruh') || rLower.includes('resesi')) {
        category = 'Valuation & Macro Sentiment';
      } else if (rLower.includes('sektor') || rLower.includes('banking') || rLower.includes('teknologi') || rLower.includes('kesehatan') || rLower.includes('transportasi')) {
        category = 'Sector Causality';
      }

      // Origin session provenance
      if (originDate) {
        const origRev = dailyReviews.find(r => r.date === originDate);
        evidence.push({
          date: originDate,
          outcome: 'FORMULATED',
          ihsg_actual: origRev?.ihsg_actual || 'Formulated',
          ihsg_actual_pct: origRev?.ihsg_actual_pct || 0.0,
          summary: origRev?.summary || 'Causal heuristic rule formulated from post-market root cause analysis.'
        });
      }

      // Evaluate rule on subsequent sessions (date > originDate) where rule was actively injected
      const subsequentSessions = dailyReviews.filter(rev => originDate && rev.date > originDate);

      let validated = 0;
      let contradicted = 0;

      const sectorKeywords = {
        'Keuangan': ['keuangan', 'banking', 'bank'],
        'Teknologi': ['teknologi', 'technology', 'goto'],
        'Energi': ['energi', 'energy', 'oil', 'coal', 'batubara'],
        'Kesehatan': ['kesehatan', 'health'],
        'Transportasi dan Logistik': ['transportasi', 'transportation', 'logistik'],
        'Properti': ['properti', 'property', 'real estate'],
        'Barang Baku': ['barang baku', 'materials', 'nikel', 'tambang'],
        'Konsumsi': ['konsumsi', 'consumer', 'cpo', 'food']
      };

      subsequentSessions.forEach(rev => {
        if (rev.ihsg_correct === null || rev.isUnscorable) return;

        const revSummaryLower = (rev.summary || '').toLowerCase();
        const revRiskLower = (rev.key_risk || '').toLowerCase();
        const revTextCombined = revSummaryLower + ' ' + revRiskLower + ' ' + (rev.rca_unanticipated || []).join(' ').toLowerCase() + ' ' + (rev.rca_underestimated || []).join(' ').toLowerCase();

        let isRelevant = false;
        let isSuccess = false;
        let explanation = '';

        // Domain-specific causality check:
        let matchedSectorKey = null;
        for (const [secKey, kws] of Object.entries(sectorKeywords)) {
          if (kws.some(kw => rLower.includes(kw))) {
            matchedSectorKey = secKey;
            break;
          }
        }

        if (matchedSectorKey && rev.sector_accuracy && rev.sector_accuracy[matchedSectorKey] !== undefined) {
          isRelevant = true;
          isSuccess = Boolean(rev.sector_accuracy[matchedSectorKey]);
          explanation = isSuccess 
            ? `Rule-constrained sector ${matchedSectorKey} matched actual market tape.`
            : `Sector ${matchedSectorKey} diverged from causal constraint.`;
        } else if (category === 'Liquidity & Flows') {
          isRelevant = rev.foreign_flow_correct !== null && rev.foreign_flow_correct !== undefined;
          isSuccess = rev.foreign_flow_correct === true;
          explanation = isSuccess
            ? 'Foreign capital flow dynamic aligned with heuristic model.'
            : 'Foreign flow diverged from heuristic model expectation.';
        } else if (category === 'Foreign Exchange' && (rev.actual_usdidr || revTextCombined.includes('rupiah') || revTextCombined.includes('usd'))) {
          isRelevant = true;
          isSuccess = rev.ihsg_correct === true;
          explanation = isSuccess
            ? 'FX transmission mechanism confirmed in session close.'
            : 'FX transmission diverged due to unexpected external factors.';
        } else if (category === 'Commodities' && (revTextCombined.includes('komoditas') || revTextCombined.includes('oil') || revTextCombined.includes('coal') || revTextCombined.includes('cpo') || revTextCombined.includes('minyak') || revTextCombined.includes('batu bara'))) {
          isRelevant = true;
          isSuccess = rev.ihsg_correct === true;
          explanation = isSuccess
            ? 'Commodity impact transmission aligned with sector performance.'
            : 'Commodity transmission divergence documented in post-market review.';
        } else if (rLower.split(' ').slice(0, 4).some(word => word.length > 4 && revTextCombined.includes(word))) {
          isRelevant = true;
          isSuccess = rev.ihsg_correct === true;
          explanation = isSuccess
            ? 'Injected constraint prevented thesis error in active session.'
            : 'Session diverged despite heuristic prompt injection.';
        }

        if (isRelevant) {
          if (isSuccess) {
            validated += 1;
            evidence.push({
              date: rev.date,
              outcome: 'VALIDATED',
              ihsg_actual: rev.ihsg_actual || 'Aligned',
              ihsg_actual_pct: rev.ihsg_actual_pct || 0.0,
              summary: explanation || rev.summary || 'Injected heuristic successfully aligned with market close.'
            });
          } else {
            contradicted += 1;
            evidence.push({
              date: rev.date,
              outcome: 'CONTRADICTED',
              ihsg_actual: rev.ihsg_actual || 'Diverged',
              ihsg_actual_pct: rev.ihsg_actual_pct || 0.0,
              summary: explanation || rev.summary || 'Subsequent session diverged despite heuristic prompt injection.'
            });
          }
        }
      });

      const totalTested = validated + contradicted;
      const validationRate = totalTested > 0 ? Math.round((validated / totalTested) * 100) : null;

      let status = 'HYPOTHESIS';
      if (totalTested >= 2 && validationRate !== null && validationRate >= 50) {
        status = 'ACTIVE';
      } else if (totalTested >= 2 && validationRate !== null && validationRate < 50) {
        status = 'SUPERSEDED';
      } else if (totalTested === 1) {
        status = validated === 1 ? 'ACTIVE' : 'HYPOTHESIS';
      } else if (totalTested === 0) {
        status = 'HYPOTHESIS';
      }

      return {
        id: `rule-${idx + 1}`,
        rule: ruleText,
        category,
        observed: totalTested,
        validated,
        contradicted,
        validationRate,
        status,
        lastObserved: lastObserved || lastUpdated,
        evidence
      };
    });

    const activeRulesCount = heuristics.filter(h => h.status === 'ACTIVE').length;
    const unprovenRulesCount = heuristics.filter(h => h.status === 'HYPOTHESIS').length;
    const testedHeuristics = heuristics.filter(h => h.validationRate !== null);
    const avgValidationRate = testedHeuristics.length > 0
      ? (testedHeuristics.reduce((acc, h) => acc + h.validationRate, 0) / testedHeuristics.length).toFixed(1)
      : null;

    const response = NextResponse.json({
      success: true,
      stats: {
        totalLessons: allLessons.length,
        activeHeuristics: activeRulesCount,
        unprovenHeuristics: unprovenRulesCount,
        blindSpotsCount: blindSpots.length,
        avgValidationRate,
        validatedHeuristicsCount: heuristics.filter(h => h.validated > 0).length,
        lastCycle: lastUpdated
      },
      blindSpots,
      heuristics
    });
    response.headers.set('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');
    return response;
  } catch (error) {
    console.error('Memory API Error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
