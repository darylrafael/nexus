import path from 'path';
import fs from 'fs';

function startsWithMock(val) {
  if (typeof val !== 'string') return false;
  const v = val.trim().toLowerCase();
  return v.startsWith('mock') || v.startsWith('src_mock') || v.startsWith('synthetic');
}

/**
 * Inspects one or more JSON artifact objects (evening_actuals, evening_review, morning_prediction, sources)
 * and returns { isMock: boolean, reasons: string[] }.
 */
export function isMockProvenance(...artifacts) {
  const reasons = [];

  for (const art of artifacts) {
    if (!art || typeof art !== 'object') continue;

    if (art.is_mock === true || art.synthetic === true) {
      reasons.push('artifact flagged synthetic/mock');
    }

    const dq = art.data_quality;
    if (dq && typeof dq === 'object') {
      if (dq.is_mock === true || dq.synthetic === true) {
        reasons.push('data_quality flagged synthetic/mock');
      }
      const fields = dq.fields;
      if (fields && typeof fields === 'object') {
        for (const [fName, fMeta] of Object.entries(fields)) {
          if (fMeta && typeof fMeta === 'object') {
            if (startsWithMock(fMeta.source)) {
              reasons.push(`data_quality.fields.${fName}.source=${fMeta.source}`);
            }
            if (fMeta.synthetic === true || fMeta.is_mock === true) {
              reasons.push(`data_quality.fields.${fName} flagged synthetic`);
            }
          } else if (startsWithMock(fMeta)) {
            reasons.push(`data_quality.fields.${fName}=${fMeta}`);
          }
        }
      }
    }

    for (const key of ['source', 'ihsg_source', 'usdidr_source', 'foreign_flow_source', 'sector_source']) {
      if (startsWithMock(art[key])) {
        reasons.push(`${key}=${art[key]}`);
      }
    }

    for (const subKey of ['ihsg', 'usdidr', 'foreign_flow']) {
      const sub = art[subKey];
      if (sub && typeof sub === 'object') {
        if (startsWithMock(sub.source)) {
          reasons.push(`${subKey}.source=${sub.source}`);
        }
        if (sub.synthetic === true || sub.is_mock === true) {
          reasons.push(`${subKey} flagged synthetic`);
        }
      }
    }

    const comms = art.commodities || art.actual_commodities;
    if (comms && typeof comms === 'object') {
      for (const [cName, cMeta] of Object.entries(comms)) {
        if (cMeta && typeof cMeta === 'object') {
          if (startsWithMock(cMeta.source)) {
            reasons.push(`commodities.${cName}.source=${cMeta.source}`);
          }
          if (cMeta.synthetic === true || cMeta.is_mock === true) {
            reasons.push(`commodities.${cName} flagged synthetic`);
          }
        }
      }
    }

    for (const evKey of ['evidence_ids', 'source_ids', 'evidence']) {
      const evList = art[evKey];
      if (Array.isArray(evList)) {
        for (const item of evList) {
          if (startsWithMock(item)) {
            reasons.push(`${evKey} contains ${item}`);
          } else if (item && typeof item === 'object') {
            for (const idField of ['id', 'source_id', 'source']) {
              if (startsWithMock(item[idField])) {
                reasons.push(`${evKey}.${idField}=${item[idField]}`);
              }
            }
          }
        }
      }
    }

    const sourcesField = art.sources;
    if (sourcesField && typeof sourcesField === 'object' && !Array.isArray(sourcesField)) {
      for (const [sId, sMeta] of Object.entries(sourcesField)) {
        if (startsWithMock(sId)) {
          reasons.push(`sources key=${sId}`);
        }
        if (sMeta && typeof sMeta === 'object') {
          for (const k of ['id', 'source_id', 'source', 'provider']) {
            if (startsWithMock(sMeta[k])) {
              reasons.push(`sources.${sId}.${k}=${sMeta[k]}`);
            }
          }
        }
      }
    }

    // Check if art itself is a sources.json map
    for (const [k, v] of Object.entries(art)) {
      if (startsWithMock(k)) {
        reasons.push(`key=${k}`);
      }
      if (v && typeof v === 'object' && !Array.isArray(v)) {
        if (startsWithMock(v.source) && !['ihsg', 'usdidr', 'foreign_flow', 'data_quality'].includes(k)) {
          reasons.push(`${k}.source=${v.source}`);
        }
      }
    }
  }

  return {
    isMock: reasons.length > 0,
    reasons: Array.from(new Set(reasons)),
  };
}

/**
 * Checks all JSON artifacts in a run directory (<runsDir>/<YYYY-MM-DD>) for mock provenance.
 */
export function checkRunDirProvenance(runDir) {
  if (!fs.existsSync(runDir)) return { isMock: false, reasons: [] };
  const artifacts = [];
  for (const fname of ['evening_actuals.json', 'evening_review.json', 'morning_prediction.json', 'sources.json']) {
    const fpath = path.join(runDir, fname);
    if (fs.existsSync(fpath)) {
      try {
        artifacts.push(JSON.parse(fs.readFileSync(fpath, 'utf8')));
      } catch (e) {
        // Ignore parse error here
      }
    }
  }
  return isMockProvenance(...artifacts);
}

/**
 * Resolves the appropriate runs directory across local dev, build time, and Vercel serverless functions.
 * Priority:
 * 0. Explicit env override: process.env.NEXUS_RUNS_DIR (when not demo)
 * 1. Bundled local data: <dashboardRoot>/data/runs (or demo_runs)
 * 2. Monorepo root runs: <dashboardRoot>/../runs
 * 3. Sibling runs: <dashboardRoot>/runs
 */
export function getRunsDirectory(isDemo = false) {
  const cwd = process.cwd();

  if (!isDemo && process.env.NEXUS_RUNS_DIR) {
    return path.resolve(process.env.NEXUS_RUNS_DIR);
  }

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
