import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { checkRunDirProvenance } from '../src/lib/nexusData.js';

/**
 * Generates pre-computed runs/index.json for fast O(1) query performance in API routes,
 * rejecting any mock-provenance session directories.
 */
export function buildRunsIndex(targetDir) {
  if (!fs.existsSync(targetDir)) return null;
  const entries = fs.readdirSync(targetDir);
  const rawDates = entries
    .filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d))
    .sort()
    .reverse();

  const sessionDates = [];
  const evaluated = [];
  const pending = [];
  const rejectedMock = [];

  for (const d of rawDates) {
    const runDir = path.join(targetDir, d);
    const { isMock, reasons } = checkRunDirProvenance(runDir);
    if (isMock) {
      rejectedMock.push({ date: d, reasons });
      console.warn(`[sync-runs] REJECTED mock run ${d} from index (${reasons.join(', ')})`);
      continue;
    }

    const hasReview = fs.existsSync(path.join(runDir, 'evening_review.json'));
    const hasPred = fs.existsSync(path.join(runDir, 'morning_prediction.json'));
    if (hasReview || hasPred) {
      sessionDates.push(d);
      if (hasReview) evaluated.push(d);
      else if (hasPred) pending.push(d);
    }
  }

  const diskPayload = {
    generated_at: new Date().toISOString(),
    total_dates: sessionDates.length,
    latest_date: sessionDates[0] || null,
    evaluated_dates: evaluated,
    pending_dates: pending,
    all_dates: sessionDates,
  };
  if (rejectedMock.length > 0) {
    diskPayload.rejected_mock_dates = rejectedMock;
  }

  const indexPath = path.join(targetDir, 'index.json');
  fs.writeFileSync(indexPath, JSON.stringify(diskPayload, null, 2), 'utf8');
  console.log(`[sync-runs] Generated index at ${indexPath} (${sessionDates.length} genuine sessions, ${rejectedMock.length} mock rejected)`);
  return {
    ...diskPayload,
    rejected_mock_dates: rejectedMock,
  };
}

export function syncRunsDirectory(sourceRuns, destRuns) {
  if (!fs.existsSync(sourceRuns)) return { synced: 0, rejectedMock: [] };
  fs.mkdirSync(destRuns, { recursive: true });

  const entries = fs.readdirSync(sourceRuns);
  let synced = 0;
  const rejectedMock = [];

  for (const entry of entries) {
    const srcPath = path.join(sourceRuns, entry);
    const destPath = path.join(destRuns, entry);
    if (/^\d{4}-\d{2}-\d{2}$/.test(entry) && fs.statSync(srcPath).isDirectory()) {
      const { isMock, reasons } = checkRunDirProvenance(srcPath);
      if (isMock) {
        rejectedMock.push({ date: entry, reasons });
        console.warn(`[sync-runs] Skipping mock run directory ${entry}: ${reasons.join(', ')}`);
        if (fs.existsSync(destPath)) {
          fs.rmSync(destPath, { recursive: true, force: true });
        }
        continue;
      }
    }
    fs.cpSync(srcPath, destPath, { recursive: true });
    synced += 1;
  }

  return { synced, rejectedMock };
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url));
if (isMain) {
  const dashboardRoot = process.cwd();
  const parentRuns = path.join(dashboardRoot, '..', 'runs');
  const localRuns = path.join(dashboardRoot, 'data', 'runs');

  const parentDemo = path.join(dashboardRoot, '..', 'demo_data', 'runs');
  const localDemo = path.join(dashboardRoot, 'data', 'demo_runs');

  if (fs.existsSync(parentRuns)) {
    syncRunsDirectory(parentRuns, localRuns);
    console.log(`[sync-runs] Synchronized ${parentRuns} -> ${localRuns}`);
  }

  if (fs.existsSync(parentDemo)) {
    fs.mkdirSync(path.dirname(localDemo), { recursive: true });
    fs.cpSync(parentDemo, localDemo, { recursive: true });
    console.log(`[sync-runs] Synchronized ${parentDemo} -> ${localDemo}`);
  }

  const parentHolidays = path.join(dashboardRoot, '..', 'data', 'idx_holidays.json');
  const localHolidays = path.join(dashboardRoot, 'data', 'idx_holidays.json');
  if (fs.existsSync(parentHolidays)) {
    fs.mkdirSync(path.dirname(localHolidays), { recursive: true });
    fs.cpSync(parentHolidays, localHolidays);
  }

  buildRunsIndex(localRuns);
  if (fs.existsSync(parentRuns)) buildRunsIndex(parentRuns);
  if (fs.existsSync(localDemo)) buildRunsIndex(localDemo);
}
