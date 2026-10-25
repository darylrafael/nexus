import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getRunsDirectory, checkRunDirProvenance, isMockProvenance } from '@/lib/nexusData';

function cleanRuleString(str) {
  if (!str || typeof str !== 'string') return '';
  return str
    .replace(/\[([^\]]+)\]/g, '$1')
    .replace(/^["'“”]+|["'“”]+$/g, '')
    .replace(/\s{2,}/g, ' ')
    .trim();
}

function parseTriggerOutcome(cleanText) {
  let trigger = '';
  let outcome = '';
  if (/^Ketika\s+/i.test(cleanText) && /\bmaka\s+/i.test(cleanText)) {
    const withoutKetika = cleanText.replace(/^Ketika\s+/i, '');
    const parts = withoutKetika.split(/\bmaka\s+/i);
    trigger = (parts[0] || '').replace(/,?\s*terjadi\s*$/i, '').trim();
    outcome = parts.slice(1).join(' ').trim();
  } else if (cleanText.includes('–') || cleanText.includes(' - ')) {
    const parts = cleanText.split(/\s+[-–]\s+/);
    trigger = (parts[0] || '').trim();
    outcome = parts.slice(1).join(' - ').trim();
  }
  return { trigger, outcome };
}

function clusterBlindSpots(missedFactorCounts) {
  const clusters = [
    {
      id: 'global-macro',
      name: 'Global Market & US Yield / Inflation Shock',
      keywords: ['fed', 'treasury', 'inflasi as', 'global market shock', 'dow jones', 's&p', 'nasdaq', 'recession', 'resesi', 'tariffs', 'trade war', 'global macroeconomic'],
      count: 0,
      examples: [],
    },
    {
      id: 'commodities',
      name: 'Energy & Commodity Price Reversal',
      keywords: ['oil', 'brent', 'wti', 'coal', 'batu bara', 'newcastle', 'cpo', 'natural gas', 'nickel', 'komoditas', 'energi'],
      count: 0,
      examples: [],
    },
    {
      id: 'foreign-flow',
      name: 'Foreign Institutional Flow Divergence',
      keywords: ['foreign', 'asing', 'net sell', 'net buy', 'accumulation', 'distribution', 'akumulasi', 'distribusi', 'outflow', 'inflow', 'msci'],
      count: 0,
      examples: [],
    },
    {
      id: 'monetary-policy',
      name: 'BI Rate & Domestic Policy Catalyst',
      keywords: ['bi rate', 'bi-rate', 'bank indonesia', 'bi policy', 'makroprudensial', 'dp 0', 'pinisi', 'pemangkasan', 'regulator', 'ipo', 'reformasi'],
      count: 0,
      examples: [],
    },
    {
      id: 'fx-rupiah',
      name: 'USD/IDR Exchange Rate Volatility',
      keywords: ['rupiah', 'usd/idr', 'currency', 'depresiasi', 'nilai tukar', '17.', '18.'],
      count: 0,
      examples: [],
    },
    {
      id: 'geopolitics',
      name: 'Geopolitical & Asian Regional Contagion',
      keywords: ['geopolit', 'middle east', 'timur tengah', 'iran', 'ukraina', 'rusia', 'bursa asia', 'kospi', 'nikkei', 'asian markets'],
      count: 0,
      examples: [],
    },
    {
      id: 'domestic-sector',
      name: 'Domestic Sector & Labor / Social Dynamics',
      keywords: ['buruh', 'demo', 'strike', 'unjuk rasa', 'sektor', 'sector', 'rebound', 'oversold', 'lq45', 'valuasi', 'p/e'],
      count: 0,
      examples: [],
    },
  ];

  let totalMentions = 0;

  for (const [rawFactor, rawCount] of Object.entries(missedFactorCounts || {})) {
    const c = Number(rawCount) || 1;
    totalMentions += c;
    const lower = rawFactor.toLowerCase();

    let matched = clusters.find((cl) => cl.keywords.some((kw) => lower.includes(kw)));
    if (!matched) {
      matched = clusters[clusters.length - 1];
    }
    matched.count += c;
    if (matched.examples.length < 3) {
      matched.examples.push(cleanRuleString(rawFactor));
    }
  }

  return clusters
    .filter((cl) => cl.count > 0)
    .map((cl) => ({
      ...cl,
      sharePct: totalMentions > 0 ? Math.round((cl.count / totalMentions) * 100) : 0,
    }))
    .sort((a, b) => b.count - a.count);
}

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const demoParam = url.searchParams.get('demo');
    const isDemo = demoParam === 'true' || (demoParam !== 'false' && process.env.NEXUS_DEMO_MODE === 'true');
    const runsDir = getRunsDirectory(isDemo);

    let allLessons = [];
    let rejectedLessons = [];
    let missedFactorCounts = {};
    let lastUpdated = '';

    // 1. Read global stats artifact if present
    const globalStatsPath = path.join(runsDir, 'global', 'nexus_stats.json');
    if (fs.existsSync(globalStatsPath)) {
      try {
        const globalData = JSON.parse(fs.readFileSync(globalStatsPath, 'utf8'));
        allLessons = globalData.all_lessons || [];
        rejectedLessons = globalData.rejected_lessons || [];
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
        const runDirPath = path.join(runsDir, date);
        if (checkRunDirProvenance(runDirPath).isMock) continue;
        const reviewFile = path.join(runDirPath, 'evening_review.json');
        if (fs.existsSync(reviewFile)) {
          try {
            const data = JSON.parse(fs.readFileSync(reviewFile, 'utf8'));
            if (isMockProvenance(data).isMock) continue;
            dailyReviews.push({ date, ...data });

            if (allLessons.length === 0 && Array.isArray(data.lessons)) {
              data.lessons.forEach(l => {
                if (l && !allLessons.includes(l)) allLessons.push(l);
              });
            }

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

    // 3. Cluster Recurring Blind Spots into clean thematic categories
    const blindSpots = clusterBlindSpots(missedFactorCounts);
    const rawBlindSpotsCount = Object.keys(missedFactorCounts).length;

    // 4. Trace Provenance & Ground Heuristics in Verified Artifact Evidence
    const rawHeuristics = allLessons.map((rawRuleText, idx) => {
      const ruleText = cleanRuleString(rawRuleText);
      const { trigger, outcome } = parseTriggerOutcome(ruleText);
      const evidence = [];
      let originDate = '';
      let lastObserved = '';

      const matchingReviews = dailyReviews.filter(rev =>
        (rev.lessons || []).some(l => {
          const cl = cleanRuleString(l);
          return cl.includes(ruleText) || ruleText.includes(cl);
        })
      );
      if (matchingReviews.length > 0) {
        originDate = matchingReviews[matchingReviews.length - 1].date;
        lastObserved = matchingReviews[0].date;
      }

      let category = 'Market Sentiment';
      const rLower = ruleText.toLowerCase();
      if (rLower.includes('bi rate') || rLower.includes('bunga') || rLower.includes('fed') || rLower.includes('treasury') || rLower.includes('yield') || rLower.includes('dp 0')) {
        category = 'Monetary Policy';
      } else if (rLower.includes('rupiah') || rLower.includes('usd') || rLower.includes('kurs') || rLower.includes('valas')) {
        category = 'Foreign Exchange';
      } else if (rLower.includes('minyak') || rLower.includes('oil') || rLower.includes('cpo') || rLower.includes('komoditas') || rLower.includes('energi') || rLower.includes('batu bara') || rLower.includes('coal') || rLower.includes('nikel')) {
        category = 'Commodities';
      } else if (rLower.includes('asing') || rLower.includes('outflow') || rLower.includes('inflow') || rLower.includes('flow') || rLower.includes('akumulasi') || rLower.includes('distribusi')) {
        category = 'Liquidity & Flows';
      } else if (rLower.includes('pe') || rLower.includes('p/e') || rLower.includes('valuasi') || rLower.includes('demo') || rLower.includes('buruh') || rLower.includes('resesi') || rLower.includes('geopolitik')) {
        category = 'Macro & Geopolitics';
      } else if (rLower.includes('sektor') || rLower.includes('banking') || rLower.includes('teknologi') || rLower.includes('kesehatan') || rLower.includes('transportasi') || rLower.includes('industri')) {
        category = 'Sector Causality';
      }

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

        let matchedSectorKey = null;
        for (const [secKey, kws] of Object.entries(sectorKeywords)) {
          if (kws.some(kw => rLower.includes(kw))) {
            matchedSectorKey = secKey;
            break;
          }
        }

        if (matchedSectorKey && rev.sector_accuracy && rev.sector_accuracy[matchedSectorKey] !== undefined && rev.sector_accuracy[matchedSectorKey] !== null) {
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
      }

      return {
        id: `R-${String(idx + 1).padStart(2, '0')}`,
        rule: ruleText,
        trigger,
        outcome,
        category,
        originDate: originDate || lastUpdated,
        observed: totalTested,
        validated,
        contradicted,
        validationRate,
        status,
        lastObserved: lastObserved || originDate || lastUpdated,
        evidence
      };
    });

    // Sort heuristics: ACTIVE first (by validationRate desc, observed desc), then HYPOTHESIS (newest originDate first), then SUPERSEDED
    const statusPriority = { ACTIVE: 0, HYPOTHESIS: 1, SUPERSEDED: 2 };
    const heuristics = [...rawHeuristics].sort((a, b) => {
      const pa = statusPriority[a.status] ?? 9;
      const pb = statusPriority[b.status] ?? 9;
      if (pa !== pb) return pa - pb;
      if ((b.validationRate ?? -1) !== (a.validationRate ?? -1)) {
        return (b.validationRate ?? -1) - (a.validationRate ?? -1);
      }
      if (b.observed !== a.observed) return b.observed - a.observed;
      return String(b.originDate || '').localeCompare(String(a.originDate || ''));
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
        supersededHeuristics: heuristics.filter(h => h.status === 'SUPERSEDED').length,
        quarantinedCount: rejectedLessons.length,
        blindSpotsCount: blindSpots.length,
        rawBlindSpotsCount,
        avgValidationRate,
        validatedHeuristicsCount: heuristics.filter(h => h.validated > 0).length,
        lastCycle: lastUpdated
      },
      blindSpots,
      quarantinedLessons: rejectedLessons.map(q => ({
        ...q,
        lesson: cleanRuleString(q.lesson),
      })),
      heuristics
    });
    response.headers.set('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');
    return response;
  } catch (error) {
    console.error('Memory API Error:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
