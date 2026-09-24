import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getRunsDirectory } from '@/lib/nexusData';

export async function GET() {
  try {
    const runsDir = getRunsDirectory(false);
    const telemetryPath = path.join(runsDir, 'global', 'telemetry.json');

    if (!fs.existsSync(telemetryPath)) {
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

    const content = fs.readFileSync(telemetryPath, 'utf8');
    const telemetry = JSON.parse(content);

    return NextResponse.json({
      success: true,
      isAvailable: true,
      stats: telemetry.stats || {
        totalRuns: 0,
        successfulRuns: 0,
        failedRuns: 0,
        successRate: '0.0',
        avgDurationMs: 0,
        runsToday: 0
      },
      agentBreakdown: telemetry.agentBreakdown || [],
      sessions: telemetry.sessions || []
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
