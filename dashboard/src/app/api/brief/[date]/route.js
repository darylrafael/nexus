import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { getRunsDirectory } from '@/lib/nexusData';

export async function GET(request, context) {
  try {
    const params = await context.params;
    const date = params?.date;

    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return NextResponse.json(
        { success: false, error: 'Invalid date parameter. Required format: YYYY-MM-DD' },
        { status: 400 }
      );
    }

    const url = new URL(request.url);
    const demoParam = url.searchParams.get('demo');
    const isDemo = demoParam === 'true' || (demoParam !== 'false' && process.env.NEXUS_DEMO_MODE === 'true');
    const runsDir = getRunsDirectory(isDemo);

    const briefPath = path.join(runsDir, date, 'morning_brief.md');

    if (!fs.existsSync(briefPath)) {
      return NextResponse.json(
        { 
          success: false, 
          error: `Morning brief document not found for date ${date}`,
          date 
        },
        { status: 404 }
      );
    }

    const markdown = fs.readFileSync(briefPath, 'utf8');
    const sourcesPath = path.join(runsDir, date, 'sources.json');
    let sources = {};
    if (fs.existsSync(sourcesPath)) {
      try {
        sources = JSON.parse(fs.readFileSync(sourcesPath, 'utf8'));
      } catch (e) {}
    }

    return NextResponse.json({
      success: true,
      date,
      markdown,
      sources
    });

  } catch (error) {
    console.error('Brief API Error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
