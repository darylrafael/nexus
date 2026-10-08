import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getRunsDirectory } from '@/lib/nexusData';

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const demoParam = url.searchParams.get('demo');
    
    // Default to LIVE runs if available, unless demo is explicitly requested
    const isDemo = demoParam === 'true' || (demoParam !== 'false' && process.env.NEXUS_DEMO_MODE === 'true');
    const runsDir = getRunsDirectory(isDemo);
    let reviews = [];
    
    const minDate = process.env.NEXUS_MIN_DATE || null;

    if (fs.existsSync(runsDir)) {
      const dates = fs.readdirSync(runsDir);
      for (const date of dates) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
        if (minDate && date < minDate) continue;
        const reviewPath = path.join(runsDir, date, 'evening_review.json');
        const predPath = path.join(runsDir, date, 'morning_prediction.json');
        const briefPath = path.join(runsDir, date, 'morning_brief.md');
        const sourcesPath = path.join(runsDir, date, 'sources.json');

        let sourcesMap = {};
        if (fs.existsSync(sourcesPath)) {
          try {
            sourcesMap = JSON.parse(fs.readFileSync(sourcesPath, 'utf8'));
          } catch (e) {}
        }

        if (fs.existsSync(reviewPath)) {
          const content = fs.readFileSync(reviewPath, 'utf8');
          try {
            const data = JSON.parse(content);
            reviews.push({ date, ...data, sources: sourcesMap, isPendingReview: false });
          } catch (e) {
            console.error(`Failed to parse ${reviewPath}`, e);
          }
        } else if (fs.existsSync(predPath)) {
          // Live active morning session awaiting market close review
          try {
            const predContent = fs.readFileSync(predPath, 'utf8');
            const pred = JSON.parse(predContent);
            let summaryText = "";
            let briefText = "";
            if (fs.existsSync(briefPath)) {
              briefText = fs.readFileSync(briefPath, 'utf8');
              const match = briefText.match(/### 1\.[^\n]+\n-\s+\*\*Summary\*\*:\s*([^\n]+)/);
              summaryText = match ? match[1] : (pred.key_risk || "Morning brief active. Trading session in progress.");
            }

            // Convert predicted sectors to display map
            const sectorAccuracy = {};
            (pred.sector_bullish || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'BULLISH'; });
            (pred.sector_bearish || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'BEARISH'; });
            (pred.sector_neutral || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'NEUTRAL'; });

            // Extract previous evaluated session metrics (close, USD/IDR, commodities) without hardcoded fallbacks
            let previousClose = null;
            let yesterdayUsdIdr = null;
            let yesterdayCommodities = null;

            const sortedPastDates = dates
              .filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && d < date && (!minDate || d >= minDate))
              .sort()
              .reverse();

            if (sortedPastDates.length > 0) {
              const prevActualsPath = path.join(runsDir, sortedPastDates[0], 'evening_actuals.json');
              if (fs.existsSync(prevActualsPath)) {
                try {
                  const pastAct = JSON.parse(fs.readFileSync(prevActualsPath, 'utf8'));
                  if (pastAct.ihsg_close != null) previousClose = pastAct.ihsg_close;
                  if (pastAct.usdidr != null) yesterdayUsdIdr = pastAct.usdidr;
                  if (pastAct.commodities && Object.keys(pastAct.commodities).length > 0) {
                    yesterdayCommodities = pastAct.commodities;
                  }
                } catch (e) {}
              }
            }

            // Watchlist derived strictly from morning_prediction.json / morning_brief.md
            let actionableWatchlist = [];
            if (Array.isArray(pred.recommended_tickers) && pred.recommended_tickers.length > 0) {
              actionableWatchlist = pred.recommended_tickers.map(ticker => {
                let note = "from morning brief — not advice";
                if (briefText) {
                  const lines = briefText.split('\n');
                  const matchLine = lines.find(l => l.includes(ticker));
                  if (matchLine) {
                    note = `${matchLine.replace(/^[#*\s-]+/, '').trim().slice(0, 140)} (from morning brief — not advice)`;
                  }
                }
                return {
                  ticker,
                  sector: "Sector Outlook",
                  bias: pred.ihsg_signal === "Bullish" ? "BULLISH" : "OBSERVE",
                  note
                };
              });
            }

            reviews.push({
              date,
              ihsg_predicted: pred.ihsg_signal || "Neutral",
              ihsg_confidence: pred.ihsg_confidence || null,
              ihsg_actual: "Pending Close",
              ihsg_actual_pct: null,
              ihsg_correct: null, // Pending evaluation
              foreign_flow_predicted: pred.foreign_flow_signal || "Neutral",
              foreign_flow_actual: "Market Open",
              foreign_flow_correct: null,
              previous_close: previousClose,
              actual_usdidr: yesterdayUsdIdr,
              actual_commodities: yesterdayCommodities,
              actionable_watchlist: actionableWatchlist,
              sector_accuracy: sectorAccuracy,
              accuracy_score: 0,
              rca_unanticipated: [],
              rca_underestimated: [],
              rca_overestimated: [],
              lessons: [],
              summary: summaryText,
              key_risk: pred.key_risk || "",
              recommended_tickers: pred.recommended_tickers || [],
              sources: sourcesMap,
              isPendingReview: true
            });
          } catch (e) {
            console.error(`Failed to parse ${predPath}`, e);
          }
        }
      }
    }
    
    // Sort reviews by date descending
    reviews.sort((a, b) => b.date.localeCompare(a.date));

    // 2. Get total runs from telemetry JSON artifact
    let totalRuns = 0;
    const telemetryPath = path.join(runsDir, 'global', 'telemetry.json');
    if (fs.existsSync(telemetryPath)) {
      try {
        const telemetry = JSON.parse(fs.readFileSync(telemetryPath, 'utf8'));
        totalRuns = telemetry?.stats?.totalRuns || 0;
      } catch (e) {
        console.error('Failed to parse telemetry.json in stats route', e);
      }
    }
    if (!totalRuns) {
      totalRuns = reviews.length * 2;
    }
    
    // Calculate global accuracy (only for evaluated sessions)
    let sumAccuracy = 0;
    let evaluatedDays = 0;
    let recentLessons = [];
    
    if (reviews.length > 0) {
      reviews.forEach(r => {
        if (!r.isPendingReview) {
          sumAccuracy += r.accuracy_score || 0;
          evaluatedDays += 1;
        }
        if (r.lessons && r.lessons.length > 0) {
          recentLessons.push(...r.lessons.map(l => ({ date: r.date, text: l })));
        }
      });
    }
    
    const avgAccuracy = evaluatedDays > 0 ? (sumAccuracy / evaluatedDays).toFixed(1) : 0;
    
    // Calculate deterministic sector breadth from latest session
    let sectorBreadth = { bullish: 0, bearish: 0, neutral: 0, total: 0 };
    if (reviews.length > 0) {
      const latestSec = reviews[0].sector_accuracy || {};
      for (const [_, val] of Object.entries(latestSec)) {
        sectorBreadth.total += 1;
        const v = String(val).toUpperCase();
        if (v === 'BULLISH' || val === true) sectorBreadth.bullish += 1;
        else if (v === 'BEARISH' || val === false) sectorBreadth.bearish += 1;
        else sectorBreadth.neutral += 1;
      }
    }

    return NextResponse.json({
      success: true,
      isDemo,
      stats: {
        totalDays: evaluatedDays,
        avgAccuracy,
        totalRuns: isDemo ? reviews.length * 2 : totalRuns,
        sectorBreadth
      },
      recentLessons: recentLessons.slice(0, 10), // Top 10 most recent
      reviews
    });
    
  } catch (error) {
    console.error("API Error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
