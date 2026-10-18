import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { isMockProvenance, checkRunDirProvenance } from '../src/lib/nexusData.js';
import { buildRunsIndex, syncRunsDirectory } from '../scripts/sync-runs.mjs';
import { GET } from '../src/app/api/stats/route.js';

test('isMockProvenance detects mock and synthetic sources across artifact fields', () => {
  const mockActuals = {
    date: '2026-10-16',
    data_quality: {
      fields: {
        ihsg: { source: 'mock_yfinance', confidence: 'high' },
        usdidr: { source: 'mock_fx' },
      },
    },
  };
  const r1 = isMockProvenance(mockActuals);
  assert.equal(r1.isMock, true);
  assert.ok(r1.reasons.some((r) => r.includes('mock_yfinance')));

  const mockPred = {
    date: '2026-10-16',
    evidence_ids: ['src_mock_1'],
  };
  const r2 = isMockProvenance(mockPred);
  assert.equal(r2.isMock, true);

  const genuine = {
    date: '2026-10-07',
    ihsg_source: 'yfinance',
    data_quality: { ohlc_valid: true, flow_verified: true },
  };
  const r3 = isMockProvenance(genuine);
  assert.equal(r3.isMock, false);
});

test('syncRunsDirectory and buildRunsIndex reject mock run directories', () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'nexus-sync-test-'));
  try {
    const srcRuns = path.join(tmpRoot, 'src_runs');
    const dstRuns = path.join(tmpRoot, 'dst_runs');

    // Genuine run
    const genDir = path.join(srcRuns, '2026-10-08');
    fs.mkdirSync(genDir, { recursive: true });
    fs.writeFileSync(
      path.join(genDir, 'morning_prediction.json'),
      JSON.stringify({ date: '2026-10-08', ihsg_signal: 'Bullish', ihsg_confidence: 70 }),
      'utf8'
    );

    // Mock run
    const mockDir = path.join(srcRuns, '2026-10-16');
    fs.mkdirSync(mockDir, { recursive: true });
    fs.writeFileSync(
      path.join(mockDir, 'evening_actuals.json'),
      JSON.stringify({
        date: '2026-10-16',
        ihsg_close: 7230.0,
        data_quality: { fields: { ihsg: { source: 'mock_yfinance' } } },
      }),
      'utf8'
    );
    fs.writeFileSync(
      path.join(mockDir, 'evening_review.json'),
      JSON.stringify({ date: '2026-10-16', ihsg_predicted: 'Bullish', ihsg_actual: 'Bearish', ihsg_correct: false }),
      'utf8'
    );

    assert.equal(checkRunDirProvenance(genDir).isMock, false);
    assert.equal(checkRunDirProvenance(mockDir).isMock, true);

    // buildRunsIndex on srcRuns rejects 2026-10-16
    const srcIndex = buildRunsIndex(srcRuns);
    assert.deepEqual(srcIndex.all_dates, ['2026-10-08']);
    assert.equal(srcIndex.latest_date, '2026-10-08');
    assert.equal(srcIndex.rejected_mock_dates.length, 1);
    assert.equal(srcIndex.rejected_mock_dates[0].date, '2026-10-16');

    // syncRunsDirectory skips copying 2026-10-16 to dstRuns
    const syncRes = syncRunsDirectory(srcRuns, dstRuns);
    assert.equal(syncRes.rejectedMock.length, 1);
    assert.equal(fs.existsSync(path.join(dstRuns, '2026-10-08')), true);
    assert.equal(fs.existsSync(path.join(dstRuns, '2026-10-16')), false);
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test('/api/stats rejects mock artifacts, surfaces mockDataDetected, and computes holiday-aware staleness', async () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'nexus-api-test-'));
  const origRunsDir = process.env.NEXUS_RUNS_DIR;
  const origHolidaysPath = process.env.NEXUS_HOLIDAYS_PATH;

  try {
    const runsDir = path.join(tmpRoot, 'runs');
    fs.mkdirSync(runsDir, { recursive: true });

    // Custom holiday calendar with 2026-10-12 as a statutory holiday
    const holidaysFile = path.join(tmpRoot, 'idx_holidays.json');
    fs.writeFileSync(
      holidaysFile,
      JSON.stringify({
        holidays: {
          '2026': [{ date: '2026-10-12', name: 'Test Exchange Holiday' }],
        },
      }),
      'utf8'
    );

    // Genuine run on 2026-10-08
    const genDir = path.join(runsDir, '2026-10-08');
    fs.mkdirSync(genDir, { recursive: true });
    fs.writeFileSync(
      path.join(genDir, 'morning_prediction.json'),
      JSON.stringify({
        date: '2026-10-08',
        ihsg_signal: 'Bullish',
        ihsg_confidence: 80,
        lock_status: 'retroactive',
        hash_computed_at: '2026-10-15',
      }),
      'utf8'
    );

    // Contaminated mock run on 2026-10-16
    const mockDir = path.join(runsDir, '2026-10-16');
    fs.mkdirSync(mockDir, { recursive: true });
    fs.writeFileSync(
      path.join(mockDir, 'evening_actuals.json'),
      JSON.stringify({
        date: '2026-10-16',
        ihsg_close: 7230.0,
        data_quality: { fields: { ihsg: { source: 'mock_yfinance' } } },
      }),
      'utf8'
    );
    fs.writeFileSync(
      path.join(mockDir, 'evening_review.json'),
      JSON.stringify({
        date: '2026-10-16',
        ihsg_predicted: 'Bullish',
        ihsg_actual: 'Bearish',
        ihsg_correct: false,
      }),
      'utf8'
    );

    process.env.NEXUS_RUNS_DIR = runsDir;
    process.env.NEXUS_HOLIDAYS_PATH = holidaysFile;

    const req = new Request('http://localhost:3002/api/stats?today=2026-10-16');
    const res = await GET(req);
    const json = await res.json();

    assert.equal(json.success, true);
    // Mock date 2026-10-16 must be excluded from reviews and latestDate
    assert.equal(json.reviews.length, 1);
    assert.equal(json.reviews[0].date, '2026-10-08');
    assert.equal(json.pipelineHealth.latestDate, '2026-10-08');

    // Provenance guard banner metadata must be set
    assert.equal(json.pipelineHealth.mockDataDetected, true);
    assert.equal(json.pipelineHealth.detectedMockRuns.length, 1);
    assert.equal(json.pipelineHealth.detectedMockRuns[0].date, '2026-10-16');

    // Between 2026-10-08 (Thu) and 2026-10-16 (Fri):
    // Weekdays are Oct 9 (Fri), Oct 12 (Mon - holiday!), Oct 13 (Tue), Oct 14 (Wed), Oct 15 (Thu), Oct 16 (Fri)
    // Total trading days = 5 (6 weekdays minus 1 holiday on Oct 12)
    assert.equal(json.pipelineHealth.tradingDaysSinceLatest, 5);
    assert.equal(json.pipelineHealth.isStale, true);
  } finally {
    if (origRunsDir === undefined) delete process.env.NEXUS_RUNS_DIR;
    else process.env.NEXUS_RUNS_DIR = origRunsDir;
    if (origHolidaysPath === undefined) delete process.env.NEXUS_HOLIDAYS_PATH;
    else process.env.NEXUS_HOLIDAYS_PATH = origHolidaysPath;
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test('Phase 3.5: cleaned real runs/ corpus returns isStale=true, latestDate=2026-10-08, n=12, and zero mock dates', async () => {
  const req = new Request('http://localhost:3002/api/stats?today=2026-10-16');
  const res = await GET(req);
  const json = await res.json();

  assert.equal(json.success, true);
  assert.equal(json.pipelineHealth.latestDate, '2026-10-08');
  assert.equal(json.pipelineHealth.isStale, true);
  assert.equal(json.pipelineHealth.tradingDaysSinceLatest, 6);
  assert.equal(json.pipelineHealth.mockDataDetected, false);

  const reviewDates = json.reviews.map((r) => r.date);
  assert.equal(reviewDates.includes('2026-10-14'), false);
  assert.equal(reviewDates.includes('2026-10-15'), false);
  assert.equal(reviewDates.includes('2026-10-16'), false);
  assert.equal(json.reviews[0].date, '2026-10-08');
  assert.equal(json.reviews[0].lock_status, 'retroactive');
  assert.equal(json.reviews[0].calibrated_confidence, 49.7);

  assert.equal(json.nexusStats.sample_size_n, 12);
  assert.equal(json.nexusStats.direction_scorable_sessions, 12);
  assert.equal(json.nexusStats.direction_accuracy_pct, 41.7);
  assert.equal(json.nexusStats.calibration.calibrated_confidence_pct, 49.7);
  assert.equal(json.nexusStats.calibration.brier_score, 0.3996);
});

