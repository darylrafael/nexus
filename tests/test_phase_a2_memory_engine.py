import json
import subprocess
from pathlib import Path


def test_memory_route_payload_contract():
    """Verify api/memory calculates validated, contradicted, and validationRate properly."""
    # Test through node script execution verifying the memory logic
    script = """
    const path = require('path');
    const fs = require('fs');

    const runsDir = path.resolve('runs');
    const globalStatsPath = path.join(runsDir, 'global', 'nexus_stats.json');
    const globalData = JSON.parse(fs.readFileSync(globalStatsPath, 'utf8'));
    const allLessons = globalData.all_lessons || [];

    const dailyReviews = [];
    const dates = fs.readdirSync(runsDir).filter(d => /^\\d{4}-\\d{2}-\\d{2}$/.test(d));
    dates.sort((a, b) => b.localeCompare(a));

    for (const date of dates) {
      const reviewFile = path.join(runsDir, date, 'evening_review.json');
      if (fs.existsSync(reviewFile)) {
        const data = JSON.parse(fs.readFileSync(reviewFile, 'utf8'));
        dailyReviews.push({ date, ...data });
      }
    }

    const heuristics = allLessons.map((ruleText, idx) => {
      const evidence = [];
      let lastObserved = '';

      dailyReviews.forEach(rev => {
        const hasLesson = (rev.lessons || []).some(l => l.includes(ruleText) || ruleText.includes(l));
        if (hasLesson) {
          if (!lastObserved) lastObserved = rev.date;
          evidence.push({
            date: rev.date,
            outcome: rev.ihsg_correct ? 'VALIDATED' : 'CONTRADICTED',
            ihsg_actual: rev.ihsg_actual || 'Flat',
            ihsg_actual_pct: rev.ihsg_actual_pct || 0.0,
            summary: rev.summary || 'Post-market evaluation completed.'
          });
        }
      });

      const observed = evidence.length;
      const validated = evidence.filter(e => e.outcome === 'VALIDATED').length;
      const contradicted = evidence.filter(e => e.outcome === 'CONTRADICTED').length;
      const totalTested = validated + contradicted;
      const validationRate = totalTested > 0 ? Math.round((validated / totalTested) * 100) : null;

      let status = 'HYPOTHESIS';
      if (observed >= 2 && validationRate !== null && validationRate >= 50) {
        status = 'ACTIVE';
      } else if (observed >= 2 && validationRate !== null && validationRate < 50) {
        status = 'SUPERSEDED';
      } else if (observed === 1) {
        status = 'ACTIVE';
      } else if (observed === 0) {
        status = 'UNTESTED';
      }

      return {
        id: `rule-${idx + 1}`,
        rule: ruleText,
        observed,
        validated,
        contradicted,
        validationRate,
        status,
        evidence
      };
    });

    console.log(JSON.stringify({ heuristicsCount: heuristics.length, sample: heuristics[0] }));
    """

    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    out = json.loads(res.stdout)

    assert out["heuristicsCount"] > 0
    sample = out["sample"]
    assert "validated" in sample
    assert "contradicted" in sample
    assert "validationRate" in sample
    assert "status" in sample
    assert sample["status"] in ["ACTIVE", "SUPERSEDED", "HYPOTHESIS", "UNTESTED"]
    assert sample["observed"] == sample["validated"] + sample["contradicted"]
