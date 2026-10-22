// Track-record math shared by the scorecard, verdict, equity chart and benchmarks.
//
// WHY this lives in one module: before, the KPI cards read pre-computed bps sums
// from nexus_stats.json while the chart recomputed its own numbers, and several
// components had hardcoded fallbacks (e.g. "+16.77%", "9 Hits"). Any drift
// between those made the page contradict itself. Everything here is derived
// from the same `reviews` array the ledger shows.
//
// Conventions:
// - A session is "scored" when it has been reviewed and has a numeric close-to-close % move.
// - Bullish call -> long the index that day. Bearish -> short. Neutral -> stay in cash (0%).
// - Returns are COMPOUNDED (growth of 1 unit of capital), which is what an investor
//   means by "return". Simple bps sums are also exposed for reference.
// - No costs, no slippage, no borrow fees. Shorting the IHSG cash index is not
//   available to most IDX retail investors, so long-only is the realistic headline.

export function directionOf(label) {
  const d = String(label || "").toLowerCase();
  if (d.includes("bull") || d === "up") return "bull";
  if (d.includes("bear") || d === "down") return "bear";
  return "neutral";
}

export function scoredSessions(reviews = []) {
  return [...reviews]
    .filter(
      (r) =>
        r &&
        !r.isPendingReview &&
        r.ihsg_actual_pct !== null &&
        r.ihsg_actual_pct !== undefined &&
        r.ihsg_actual_pct !== "" &&
        Number.isFinite(Number(r.ihsg_actual_pct))
    )
    .sort((a, b) => a.date.localeCompare(b.date));
}

// Wilson score interval, 95%.
export function wilsonInterval(k, n, z = 1.96) {
  if (!n) return null;
  const p = k / n;
  const denom = 1 + (z * z) / n;
  const center = (p + (z * z) / (2 * n)) / denom;
  const half = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / denom;
  return { lower: Math.max(0, center - half) * 100, upper: Math.min(1, center + half) * 100 };
}

export function computePerformance(reviews = []) {
  const sessions = scoredSessions(reviews);
  const n = sessions.length;

  let eqLong = 1;
  let eqLongShort = 1;
  let eqBuyHold = 1;
  let eqAlwaysShort = 1;
  let hits = 0;
  let directionScorable = 0;
  let alwaysBearHits = 0;
  let alwaysBullHits = 0;
  let persistenceHits = 0;
  let persistenceScorable = 0;
  let longTrades = 0;
  let shortTrades = 0;
  let cashDays = 0;
  let statedConfSum = 0;
  let statedConfCount = 0;

  const points = [];
  const contributions = []; // long/short daily contribution in % (simple)

  sessions.forEach((r, idx) => {
    const pct = Number(r.ihsg_actual_pct);
    const ret = pct / 100;
    const call = directionOf(r.ihsg_predicted);
    const actualDir = directionOf(r.ihsg_actual);

    let longRet = 0;
    let lsRet = 0;
    if (call === "bull") {
      longRet = ret;
      lsRet = ret;
      longTrades += 1;
    } else if (call === "bear") {
      lsRet = -ret;
      shortTrades += 1;
    } else {
      cashDays += 1;
    }

    eqLong *= 1 + longRet;
    eqLongShort *= 1 + lsRet;
    eqBuyHold *= 1 + ret;
    eqAlwaysShort *= 1 - ret;

    if (r.ihsg_correct === true || r.ihsg_correct === false) {
      directionScorable += 1;
      if (r.ihsg_correct === true) hits += 1;
      if (actualDir === "bear") alwaysBearHits += 1;
      if (actualDir === "bull") alwaysBullHits += 1;
      if (idx > 0) {
        const prevActual = directionOf(sessions[idx - 1].ihsg_actual);
        persistenceScorable += 1;
        if (prevActual === actualDir) persistenceHits += 1;
      }
    }

    const conf = Number(r.ihsg_confidence);
    if (Number.isFinite(conf) && conf > 0) {
      statedConfSum += conf;
      statedConfCount += 1;
    }

    contributions.push({ date: r.date, pct: lsRet * 100 });

    points.push({
      date: r.date,
      call,
      pred: r.ihsg_predicted,
      actual: r.ihsg_actual,
      actualPct: pct,
      correct: r.ihsg_correct,
      dayLongPct: longRet * 100,
      dayLongShortPct: lsRet * 100,
      longOnly: (eqLong - 1) * 100,
      longShort: (eqLongShort - 1) * 100,
      buyHold: (eqBuyHold - 1) * 100,
      alwaysShort: (eqAlwaysShort - 1) * 100,
    });
  });

  // Concentration: share of the long/short simple P&L that came from the best 2 sessions.
  const totalLsSimple = contributions.reduce((acc, c) => acc + c.pct, 0);
  const sortedContrib = [...contributions].sort((a, b) => b.pct - a.pct);
  const top2 = sortedContrib.slice(0, 2);
  const top2Sum = top2.reduce((acc, c) => acc + c.pct, 0);
  const top2Share = totalLsSimple > 0 ? Math.min(999, (top2Sum / totalLsSimple) * 100) : null;

  const hitRate = directionScorable ? (hits / directionScorable) * 100 : null;
  const ci = wilsonInterval(hits, directionScorable);
  const alwaysBearPct = directionScorable ? (alwaysBearHits / directionScorable) * 100 : null;
  const alwaysBullPct = directionScorable ? (alwaysBullHits / directionScorable) * 100 : null;
  const persistencePct = persistenceScorable ? (persistenceHits / persistenceScorable) * 100 : null;
  const naive = [
    { id: "bear", label: "Always say \"down\"", pct: alwaysBearPct, hits: alwaysBearHits, n: directionScorable },
    { id: "bull", label: "Always say \"up\"", pct: alwaysBullPct, hits: alwaysBullHits, n: directionScorable },
    { id: "persist", label: "Repeat yesterday's direction", pct: persistencePct, hits: persistenceHits, n: persistenceScorable },
  ].filter((b) => b.pct !== null);
  const bestNaive = naive.reduce((best, b) => (best === null || b.pct > best.pct ? b : best), null);

  return {
    n,
    firstDate: sessions[0]?.date || null,
    lastDate: sessions[n - 1]?.date || null,
    hits,
    misses: directionScorable - hits,
    directionScorable,
    hitRate,
    ci,
    naive,
    bestNaive,
    beatsBestNaive: hitRate !== null && bestNaive ? hitRate > bestNaive.pct : null,
    avgStatedConf: statedConfCount ? statedConfSum / statedConfCount : null,
    longOnlyPct: (eqLong - 1) * 100,
    longShortPct: (eqLongShort - 1) * 100,
    buyHoldPct: (eqBuyHold - 1) * 100,
    alwaysShortPct: (eqAlwaysShort - 1) * 100,
    longTrades,
    shortTrades,
    cashDays,
    top2,
    top2Share,
    points,
  };
}

// Plain-language verdict. Deterministic so the headline can be explained and tested.
export function verdictFor(perf) {
  if (!perf || !perf.directionScorable) {
    return { tone: "neutral", label: "Not enough data", text: "No scored sessions yet." };
  }
  const { hitRate, bestNaive, ci, directionScorable } = perf;
  const beats = bestNaive ? hitRate > bestNaive.pct : false;
  const significant = ci ? ci.lower > 50 : false;
  if (beats && significant && directionScorable >= 30) {
    return { tone: "good", label: "Shows an edge", text: "Beats every naive baseline and the 95% range stays above a coin flip." };
  }
  if (beats) {
    return {
      tone: "warn",
      label: "Promising, not proven",
      text: `Beats the naive baselines, but ${directionScorable} sessions is too few to rule out luck.`,
    };
  }
  return {
    tone: "bad",
    label: "No edge yet",
    text: `A naive rule — ${bestNaive?.label || "a simple baseline"} — would have been right more often (${bestNaive ? bestNaive.pct.toFixed(0) : "—"}% vs ${hitRate.toFixed(0)}%).`,
  };
}

export const fmtSignedPct = (v, digits = 1) => {
  if (v === null || v === undefined || !Number.isFinite(Number(v))) return "—";
  const num = Number(v);
  return `${num > 0 ? "+" : ""}${num.toFixed(digits)}%`;
};
