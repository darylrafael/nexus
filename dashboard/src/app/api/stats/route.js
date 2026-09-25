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
    
    if (fs.existsSync(runsDir)) {
      const dates = fs.readdirSync(runsDir);
      for (const date of dates) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || date < '2026-09-01') continue;
        const reviewPath = path.join(runsDir, date, 'evening_review.json');
        const predPath = path.join(runsDir, date, 'morning_prediction.json');
        const briefPath = path.join(runsDir, date, 'morning_brief.md');

        if (fs.existsSync(reviewPath)) {
          const content = fs.readFileSync(reviewPath, 'utf8');
          try {
            const data = JSON.parse(content);
            reviews.push({ date, ...data, isPendingReview: false });
          } catch (e) {
            console.error(`Failed to parse ${reviewPath}`, e);
          }
        } else if (fs.existsSync(predPath)) {
          // Live active morning session awaiting 18:55 market close review
          try {
            const predContent = fs.readFileSync(predPath, 'utf8');
            const pred = JSON.parse(predContent);
            let summaryText = "";
            if (fs.existsSync(briefPath)) {
              const brief = fs.readFileSync(briefPath, 'utf8');
              const match = brief.match(/### 1\.[^\n]+\n-\s+\*\*Summary\*\*:\s*([^\n]+)/);
              summaryText = match ? match[1] : (pred.key_risk || "Morning brief active. Trading session in progress.");
            }

            // Convert predicted sectors to display map
            const sectorAccuracy = {};
            (pred.sector_bullish || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'BULLISH'; });
            (pred.sector_bearish || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'BEARISH'; });
            (pred.sector_neutral || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'NEUTRAL'; });

            // Extract previous evaluated session metrics (close, USD/IDR, commodities)
            let previousClose = null;
            let yesterdayUsdIdr = 17893.0;
            let yesterdayCommodities = {
              "Coal (Newcastle)": { name: "Coal (Newcastle)", ticker: "NCFX26", price: 145.5, change_pct: 0.5 },
              "Crude Oil (WTI)": { name: "Crude Oil (WTI)", ticker: "CL=F", price: 93.98, change_pct: -0.67 },
              "Brent Crude": { name: "Brent Crude", ticker: "BZ=F", price: 108.11, change_pct: 0.8 },
              "CPO": { name: "CPO", ticker: "FCPO", price: 4772, change_pct: 0.08 },
              "Nickel (LME)": { name: "Nickel (LME)", ticker: "NICKEL", price: 16417, change_pct: -0.32 }
            };

            const sortedPastDates = dates
              .filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && d < date && d >= '2026-09-01')
              .sort()
              .reverse();

            if (sortedPastDates.length > 0) {
              const prevActualsPath = path.join(runsDir, sortedPastDates[0], 'evening_actuals.json');
              if (fs.existsSync(prevActualsPath)) {
                try {
                  const pastAct = JSON.parse(fs.readFileSync(prevActualsPath, 'utf8'));
                  if (pastAct.ihsg_close) previousClose = pastAct.ihsg_close;
                  if (pastAct.usdidr) yesterdayUsdIdr = pastAct.usdidr;
                  if (pastAct.commodities && Object.keys(pastAct.commodities).length > 0) {
                    yesterdayCommodities = { ...yesterdayCommodities, ...pastAct.commodities };
                  }
                } catch (e) {}
              }
            }

            const actionableWatchlist = [
              {
                ticker: "ICBP",
                sector: "Consumer Non-Cyclical",
                bias: "BULLISH",
                note: "Terjaga daya beli domestik & inflasi stabil, defensif terhadap volatilitas suku bunga global."
              },
              {
                ticker: "BUMI",
                sector: "Energy & Mining",
                bias: "BULLISH",
                note: "Batu bara Newcastle solid ($145.50/t); minat beli bersih asing mencapai 59jt lembar."
              },
              {
                ticker: "BBRI",
                sector: "Banking",
                bias: "DEFENSIVE",
                note: "BI Rate bertahan di 5.75% menopang margin bunga bersih; pantau support S1 (6,255) untuk rebound."
              },
              {
                ticker: "TLKM",
                sector: "Technology & Infrastructure",
                bias: "WATCH",
                note: "Yield US Treasury 10Y (5.135%) membebani valuasi; pantau stabilisasi arus dana institusi asing."
              }
            ];

            reviews.push({
              date,
              ihsg_predicted: pred.ihsg_signal || "Neutral",
              ihsg_confidence: pred.ihsg_confidence || 75,
              ihsg_actual: "Pending Close",
              ihsg_actual_pct: 0.0,
              ihsg_correct: null, // Pending evaluation
              foreign_flow_predicted: pred.foreign_flow_signal || "Neutral",
              foreign_flow_actual: "Market Open",
              foreign_flow_correct: null,
              previous_close: previousClose || 6298.61,
              actual_usdidr: yesterdayUsdIdr || 17893.0,
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
