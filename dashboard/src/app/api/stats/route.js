import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';

export async function GET(request) {
  try {
    const nexusRoot = path.join(process.cwd(), '..');
    const url = new URL(request.url);
    const demoParam = url.searchParams.get('demo');
    
    // Default to LIVE runs if available, unless demo is explicitly requested
    const isDemo = demoParam === 'true' || (demoParam !== 'false' && process.env.NEXUS_DEMO_MODE === 'true');
    
    const runsDir = isDemo
      ? path.join(nexusRoot, 'demo_data', 'runs')
      : path.join(nexusRoot, 'runs');
    let reviews = [];
    
    if (fs.existsSync(runsDir)) {
      const dates = fs.readdirSync(runsDir);
      for (const date of dates) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
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

    // 2. Get DB stats
    const dbPath = path.join(nexusRoot, 'nexus_sessions.db');
    let totalRuns = 0;
    
    if (!isDemo && fs.existsSync(dbPath)) {
      const db = new Database(dbPath, { readonly: true });
      const row = db.prepare('SELECT COUNT(id) as total_runs FROM sessions').get();
      if (row) {
        totalRuns = row.total_runs || 0;
      }
      db.close();
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
    
    return NextResponse.json({
      success: true,
      isDemo,
      stats: {
        totalDays: evaluatedDays,
        avgAccuracy,
        totalRuns: isDemo ? reviews.length * 2 : totalRuns
      },
      recentLessons: recentLessons.slice(0, 10), // Top 10 most recent
      reviews
    });
    
  } catch (error) {
    console.error("API Error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
