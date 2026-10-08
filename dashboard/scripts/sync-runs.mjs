import fs from 'fs';
import path from 'path';

const dashboardRoot = process.cwd();
const parentRuns = path.join(dashboardRoot, '..', 'runs');
const localRuns = path.join(dashboardRoot, 'data', 'runs');

const parentDemo = path.join(dashboardRoot, '..', 'demo_data', 'runs');
const localDemo = path.join(dashboardRoot, 'data', 'demo_runs');

if (fs.existsSync(parentRuns)) {
  fs.mkdirSync(path.dirname(localRuns), { recursive: true });
  fs.cpSync(parentRuns, localRuns, { recursive: true });
  console.log(`[sync-runs] Synchronized ${parentRuns} -> ${localRuns}`);
}

if (fs.existsSync(parentDemo)) {
  fs.mkdirSync(path.dirname(localDemo), { recursive: true });
  fs.cpSync(parentDemo, localDemo, { recursive: true });
  console.log(`[sync-runs] Synchronized ${parentDemo} -> ${localDemo}`);
}

// Generate pre-computed runs/index.json for fast O(1) query performance in API routes
function buildRunsIndex(targetDir) {
  if (!fs.existsSync(targetDir)) return;
  const entries = fs.readdirSync(targetDir);
  const sessionDates = entries
    .filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d))
    .sort()
    .reverse();

  const evaluated = [];
  const pending = [];

  for (const d of sessionDates) {
    const hasReview = fs.existsSync(path.join(targetDir, d, 'evening_review.json'));
    const hasPred = fs.existsSync(path.join(targetDir, d, 'morning_prediction.json'));
    if (hasReview) evaluated.push(d);
    else if (hasPred) pending.push(d);
  }

  const indexPayload = {
    generated_at: new Date().toISOString(),
    total_dates: sessionDates.length,
    latest_date: sessionDates[0] || null,
    evaluated_dates: evaluated,
    pending_dates: pending,
    all_dates: sessionDates,
  };

  const indexPath = path.join(targetDir, 'index.json');
  fs.writeFileSync(indexPath, JSON.stringify(indexPayload, null, 2), 'utf8');
  console.log(`[sync-runs] Generated index at ${indexPath} (${sessionDates.length} sessions)`);
}

buildRunsIndex(localRuns);
if (fs.existsSync(parentRuns)) buildRunsIndex(parentRuns);
if (fs.existsSync(localDemo)) buildRunsIndex(localDemo);
