import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';

export async function GET() {
  try {
    const nexusRoot = path.join(process.cwd(), '..');
    
    // 1. Get runs from the file system (Artifacts)
    const runsDir = path.join(nexusRoot, 'runs');
    let reviews = [];
    
    if (fs.existsSync(runsDir)) {
      const dates = fs.readdirSync(runsDir);
      for (const date of dates) {
        const reviewPath = path.join(runsDir, date, 'evening_review.json');
        if (fs.existsSync(reviewPath)) {
          const content = fs.readFileSync(reviewPath, 'utf8');
          try {
            const data = JSON.parse(content);
            reviews.push({ date, ...data });
          } catch (e) {
            console.error(`Failed to parse ${reviewPath}`, e);
          }
        }
      }
    }
    
    // Sort reviews by date descending
    reviews.sort((a, b) => b.date.localeCompare(a.date));

    // 2. Get DB stats
    const dbPath = path.join(nexusRoot, 'nexus_sessions.db');
    let totalRuns = 0;
    
    if (fs.existsSync(dbPath)) {
      const db = new Database(dbPath, { readonly: true });
      const row = db.prepare('SELECT COUNT(id) as total_runs FROM sessions').get();
      if (row) {
        totalRuns = row.total_runs || 0;
      }
      db.close();
    }
    
    // Calculate global accuracy
    let sumAccuracy = 0;
    let totalDays = reviews.length;
    let recentLessons = [];
    
    if (totalDays > 0) {
      reviews.forEach(r => {
        sumAccuracy += r.accuracy_score || 0;
        if (r.lessons && r.lessons.length > 0) {
          recentLessons.push(...r.lessons.map(l => ({ date: r.date, text: l })));
        }
      });
    }
    
    const avgAccuracy = totalDays > 0 ? (sumAccuracy / totalDays).toFixed(1) : 0;
    
    return NextResponse.json({
      success: true,
      stats: {
        totalDays,
        avgAccuracy,
        totalRuns
      },
      recentLessons: recentLessons.slice(0, 10), // Top 10 most recent
      reviews
    });
    
  } catch (error) {
    console.error("API Error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
