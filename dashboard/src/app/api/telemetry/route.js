import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';

export async function GET() {
  try {
    const nexusRoot = path.join(process.cwd(), '..');
    const dbPath = path.join(nexusRoot, 'nexus_sessions.db');

    if (!fs.existsSync(dbPath)) {
      return NextResponse.json({
        success: true,
        isAvailable: false,
        stats: {
          totalRuns: 0,
          successfulRuns: 0,
          failedRuns: 0,
          successRate: '0.0',
          avgDurationMs: 0,
          runsToday: 0
        },
        agentBreakdown: [],
        sessions: []
      });
    }

    const db = new Database(dbPath, { readonly: true });

    // 1. Pipeline Health Stats
    const totalRow = db.prepare(`
      SELECT 
        COUNT(*) as total_runs,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_runs,
        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_runs,
        AVG(duration_ms) as avg_duration_ms
      FROM sessions
    `).get() || {};

    const total = totalRow.total_runs || 0;
    const successful = totalRow.successful_runs || 0;
    const failed = totalRow.failed_runs || 0;
    const avgDurationMs = Math.round(totalRow.avg_duration_ms || 0);
    const successRate = total > 0 ? ((successful / total) * 100).toFixed(1) : '0.0';

    // Runs today (based on local ISO date prefix)
    const todayStr = new Date().toISOString().slice(0, 10);
    const todayRow = db.prepare(`
      SELECT COUNT(*) as runs_today 
      FROM sessions 
      WHERE timestamp LIKE ?
    `).get(`${todayStr}%`) || {};
    const runsToday = todayRow.runs_today || 0;

    // 2. Deterministic Agent Performance Breakdown
    const agentBreakdown = db.prepare(`
      SELECT 
        agent,
        COUNT(*) as total_calls,
        ROUND(AVG(duration_ms), 1) as avg_duration_ms,
        ROUND(SUM(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 1) as success_rate_pct,
        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
      FROM sessions
      GROUP BY agent
      ORDER BY total_calls DESC
    `).all() || [];

    // 3. Recent 50 Sessions for Execution Ledger
    const sessions = db.prepare(`
      SELECT 
        id, 
        timestamp, 
        query, 
        agent, 
        model, 
        result, 
        success, 
        error_msg, 
        duration_ms
      FROM sessions
      ORDER BY id DESC
      LIMIT 50
    `).all() || [];

    db.close();

    return NextResponse.json({
      success: true,
      isAvailable: true,
      stats: {
        totalRuns: total,
        successfulRuns: successful,
        failedRuns: failed,
        successRate,
        avgDurationMs,
        runsToday
      },
      agentBreakdown,
      sessions
    });

  } catch (error) {
    console.error('Telemetry API Error:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message,
      isAvailable: false
    }, { status: 500 });
  }
}
