import path from 'path';
import fs from 'fs';

/**
 * Resolves the appropriate runs directory across local dev, build time, and Vercel serverless functions.
 * Priority:
 * 1. Bundled local data: <dashboardRoot>/data/runs (or demo_runs)
 * 2. Monorepo root runs: <dashboardRoot>/../runs
 * 3. Sibling runs: <dashboardRoot>/runs
 */
export function getRunsDirectory(isDemo = false) {
  const cwd = process.cwd();

  if (isDemo) {
    const candidateDirs = [
      path.join(cwd, 'data', 'demo_runs'),
      path.join(cwd, 'data', 'runs'),
      path.join(cwd, 'demo_data', 'runs'),
      path.join(cwd, '..', 'demo_data', 'runs')
    ];
    for (const dir of candidateDirs) {
      if (fs.existsSync(dir)) return dir;
    }
    return path.join(cwd, 'data', 'demo_runs');
  }

  const candidateDirs = [
    path.join(cwd, 'data', 'runs'),
    path.join(cwd, '..', 'runs'),
    path.join(cwd, 'runs')
  ];

  for (const dir of candidateDirs) {
    if (fs.existsSync(dir)) return dir;
  }

  return path.join(cwd, 'data', 'runs');
}
