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
