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
      let lastObserved = '';

      dailyReviews.forEach(rev => {
        const hasLesson = (rev.lessons || []).some(l => l.includes(ruleText) || ruleText.includes(l));
        if (hasLesson) {
          if (!lastObserved) lastObserved = rev.date;
          evidence.push({
            date: rev.date,
            outcome: rev.ihsg_correct ? 'CORRECT_PREDICTION' : 'INCORRECT_PREDICTION',
            ihsg_actual: rev.ihsg_actual || 'Flat',
            ihsg_actual_pct: rev.ihsg_actual_pct || 0.0,
            summary: rev.summary || 'Post-market evaluation completed.'
          });
        }
      });

      const observed = evidence.length;
      const status = observed > 0 ? 'ACTIVE' : 'UNTESTED';

      // Categorize rule deterministically
      let category = 'Market Sentiment';
      const rLower = ruleText.toLowerCase();
      if (rLower.includes('bi rate') || rLower.includes('bunga') || rLower.includes('fed')) {
        category = 'Monetary Policy';
      } else if (rLower.includes('rupiah') || rLower.includes('usd') || rLower.includes('kurs') || rLower.includes('valas')) {
        category = 'Foreign Exchange';
      } else if (rLower.includes('minyak') || rLower.includes('oil') || rLower.includes('cpo') || rLower.includes('komoditas') || rLower.includes('energi')) {
        category = 'Commodities';
      } else if (rLower.includes('asing') || rLower.includes('outflow') || rLower.includes('inflow') || rLower.includes('flow')) {
        category = 'Liquidity & Flows';
      }

      return {
        id: `rule-${idx + 1}`,
        rule: ruleText,
        category,
        observed,
        status,
        lastObserved: lastObserved || lastUpdated,
        evidence
      };
    });

    const activeRulesCount = heuristics.filter(h => h.status === 'ACTIVE').length;
    const unprovenRulesCount = heuristics.filter(h => h.status === 'UNTESTED').length;

    const response = NextResponse.json({
      success: true,
      stats: {
        totalLessons: allLessons.length,
        activeHeuristics: activeRulesCount,
        unprovenHeuristics: unprovenRulesCount,
        blindSpotsCount: blindSpots.length,
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
