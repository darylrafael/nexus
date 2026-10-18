import { NextResponse } from 'next/server.js';
import fs from 'fs';
import path from 'path';
import { getRunsDirectory, checkRunDirProvenance } from '../../../lib/nexusData.js';

function enrichCommodityMap(commodities) {
  if (!commodities || typeof commodities !== 'object') return commodities;
  const enriched = {};
  const kwMap = {
    coal: ['batu bara', 'coal', 'newcastle'],
    cpo: ['cpo', 'crude palm oil', 'sawit', 'palm oil'],
    nickel: ['nikel', 'nickel', 'lme']
  };
  const downWords = /(?:turun|melemah|terkoreksi|merosot|anjlok|terpukul|jatuh|drop|dropped|fell|falls|down|decline|declined|slump|plunge|minus|decrease)/i;
  const upWords = /(?:naik|menguat|melonjak|terangkat|rebound|rose|rises|surge|surged|up|gain|gained|rally|increase)/i;

  for (const [key, item] of Object.entries(commodities)) {
    if (!item) continue;
    let name = item.name || key;
    let price = item.price;
    let changePct = item.change_pct;
    let signal = item.signal;
    const raw = typeof item.raw === 'string' ? item.raw : '';

    if (raw && !raw.startsWith('Data unavailable:')) {
      const lowerKey = (name || key).toLowerCase();
      let keywords = [];
      if (lowerKey.includes('coal')) keywords = kwMap.coal;
      else if (lowerKey.includes('cpo')) keywords = kwMap.cpo;
      else if (lowerKey.includes('nickel')) keywords = kwMap.nickel;

      const sentences = raw.split(/[.!?\n]+/);

      if (price == null) {
        for (const sent of sentences) {
          const sentLower = sent.toLowerCase();
          if (keywords.length > 0 && !keywords.some(k => sentLower.includes(k))) continue;
          const mUsd = sent.match(/(?:USD|\$)\s*([0-9]{1,4}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)/i);
          if (mUsd) {
            price = parseFloat(mUsd[1].replace(/,/g, ''));
            break;
          }
          const mTon = sent.match(/([0-9]{2,4}(?:\.[0-9]+)?)\s*(?:\/ton|\/MT|USD)/i);
          if (mTon) {
            price = parseFloat(mTon[1]);
            break;
          }
        }
      }

      if (changePct == null) {
        for (const sent of sentences) {
          const sentLower = sent.toLowerCase();
          if (keywords.length > 0 && !keywords.some(k => sentLower.includes(k))) continue;
          const mPct = sent.match(/([+-]?[0-9]+(?:\.[0-9]+)?)\s*%/);
          if (mPct) {
            const num = parseFloat(mPct[1].replace(',', '.'));
            const isExplicit = mPct[1].startsWith('+') || mPct[1].startsWith('-');
            const isDown = downWords.test(sentLower);
            const isUp = upWords.test(sentLower);

            if (isExplicit) {
              changePct = num;
            } else if (isDown && !isUp) {
              changePct = -Math.abs(num);
            } else if (isUp && !isDown) {
              changePct = Math.abs(num);
            }
            if (changePct != null) break;
          }
        }
      }

      if (!signal && changePct != null) {
        signal = changePct > 0 ? 'Up' : (changePct < 0 ? 'Down' : 'Flat');
      }
    }

    let benchmarkLabel = null;
    const nameLower = name.toLowerCase();
    if (nameLower.includes('coal')) {
      benchmarkLabel = "ICE Newcastle Dec '26 Futures";
    } else if (nameLower.includes('cpo')) {
      benchmarkLabel = 'FCPO / Kemendag Ref';
    } else if (nameLower.includes('nickel')) {
      benchmarkLabel = 'LME Cash Settlement';
    }

    enriched[key] = {
      ...item,
      raw: raw ? raw.slice(0, 160) : undefined,
      name,
      price: price != null ? price : null,
      change_pct: changePct != null ? changePct : null,
      signal: signal || (changePct != null ? (changePct > 0 ? 'Up' : (changePct < 0 ? 'Down' : 'Flat')) : 'Unavailable'),
      benchmark_label: benchmarkLabel
    };
  }
  return enriched;
}

function slimSourcesMap(sourcesMap, textBlobs = []) {
  if (!sourcesMap || typeof sourcesMap !== 'object') return {};
  const combined = textBlobs.filter(Boolean).join(' ');
  const citedIds = new Set();
  const re = /src_[a-zA-Z0-9_-]+/g;
  let m;
  while ((m = re.exec(combined)) !== null) {
    citedIds.add(m[0]);
    citedIds.add(m[0].replace(/^src_/, ''));
  }
  const slim = {};
  for (const [k, v] of Object.entries(sourcesMap)) {
    if (!v || typeof v !== 'object') continue;
    if (citedIds.has(k) || citedIds.has(`src_${k}`)) {
      slim[k] = { url: v.url || null, title: v.title || '' };
    }
  }
  return slim;
}

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const demoParam = url.searchParams.get('demo');
    const todayParam = url.searchParams.get('today');
    
    // Default to LIVE runs if available, unless demo is explicitly requested
    const isDemo = demoParam === 'true' || (demoParam !== 'false' && process.env.NEXUS_DEMO_MODE === 'true');
    const runsDir = getRunsDirectory(isDemo);
    let reviews = [];
    const detectedMockRuns = [];

    // Load canonical stats from global artifact
    let nexusStats = null;
    const nexusStatsPath = path.join(runsDir, 'global', 'nexus_stats.json');
    if (fs.existsSync(nexusStatsPath)) {
      try {
        nexusStats = JSON.parse(fs.readFileSync(nexusStatsPath, 'utf8'));
      } catch (e) {}
    }
    
    // Load IDX holiday calendar from data/idx_holidays.json
    let holidaysMap = {};
    const holidayCandidates = [
      process.env.NEXUS_HOLIDAYS_PATH,
      path.join(runsDir, '..', 'data', 'idx_holidays.json'),
      path.join(runsDir, '..', 'idx_holidays.json'),
      path.join(process.cwd(), 'data', 'idx_holidays.json'),
      path.join(process.cwd(), '..', 'data', 'idx_holidays.json'),
    ].filter(Boolean);
    const holidaysPath = holidayCandidates.find(p => fs.existsSync(p));
    if (holidaysPath) {
      try {
        const rawHolidays = JSON.parse(fs.readFileSync(holidaysPath, 'utf8'));
        for (const [_, list] of Object.entries(rawHolidays.holidays || {})) {
          if (Array.isArray(list)) {
            for (const h of list) {
              if (h.date) holidaysMap[h.date] = h.name || 'Libur Bursa';
            }
          }
        }
      } catch (e) {
        console.error('Failed to parse idx_holidays.json', e);
      }
    }

    // Current Jakarta date & time (supports deterministic test override via ?today=YYYY-MM-DD or NEXUS_TODAY_KEY)
    const nowJktStr = new Date().toLocaleString("en-US", { timeZone: "Asia/Jakarta" });
    const nowJkt = new Date(nowJktStr);
    const todayYear = nowJkt.getFullYear();
    const todayMonth = String(nowJkt.getMonth() + 1).padStart(2, '0');
    const todayDay = String(nowJkt.getDate()).padStart(2, '0');
    const computedTodayKey = `${todayYear}-${todayMonth}-${todayDay}`;
    const todayKey = (todayParam && /^\d{4}-\d{2}-\d{2}$/.test(todayParam))
      ? todayParam
      : (process.env.NEXUS_TODAY_KEY || computedTodayKey);
    const minDate = process.env.NEXUS_MIN_DATE || null;

    if (fs.existsSync(runsDir)) {
      const dates = fs.readdirSync(runsDir);
      for (const date of dates) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) continue;
        if (minDate && date < minDate) continue;
        const runDirPath = path.join(runsDir, date);
        const { isMock, reasons } = checkRunDirProvenance(runDirPath);
        if (isMock) {
          detectedMockRuns.push({ date, reasons });
          continue;
        }
        const reviewPath = path.join(runsDir, date, 'evening_review.json');
        const predPath = path.join(runsDir, date, 'morning_prediction.json');
        const briefPath = path.join(runsDir, date, 'morning_brief.md');
        const sourcesPath = path.join(runsDir, date, 'sources.json');

        let sourcesMap = {};
        if (fs.existsSync(sourcesPath)) {
          try {
            sourcesMap = JSON.parse(fs.readFileSync(sourcesPath, 'utf8'));
          } catch (e) {}
        }

        if (fs.existsSync(reviewPath)) {
          const content = fs.readFileSync(reviewPath, 'utf8');
          try {
            const data = JSON.parse(content);
            const actualsPath = path.join(runsDir, date, 'evening_actuals.json');
            let isTrueAtr = true;
            let volatilityLabel = "ATR(14)";

            if (fs.existsSync(actualsPath)) {
              try {
                const actData = JSON.parse(fs.readFileSync(actualsPath, 'utf8'));
                if (data.ihsg_close == null && actData.ihsg_close != null) data.ihsg_close = actData.ihsg_close;
                if (data.ihsg_prev == null && actData.ihsg_prev != null) data.ihsg_prev = actData.ihsg_prev;
                if (data.ihsg_open == null && actData.ihsg_open != null) data.ihsg_open = actData.ihsg_open;
                if (data.ihsg_high == null && actData.ihsg_high != null) data.ihsg_high = actData.ihsg_high;
                if (data.ihsg_low == null && actData.ihsg_low != null) data.ihsg_low = actData.ihsg_low;
                if (data.ihsg_volume == null && actData.ihsg_volume != null) data.ihsg_volume = actData.ihsg_volume;
                if (data.actual_usdidr == null && actData.usdidr != null) data.actual_usdidr = actData.usdidr;
                if (!data.actual_commodities && actData.commodities) data.actual_commodities = actData.commodities;
                if (actData.data_quality) data.data_quality = actData.data_quality;

                if (data.ihsg_atr14 == null) {
                  if (actData.ihsg_atr14 != null) {
                    data.ihsg_atr14 = actData.ihsg_atr14;
                    data.dynamic_s1 = actData.dynamic_s1;
                    data.dynamic_r1 = actData.dynamic_r1;
                    data.dynamic_s2 = actData.dynamic_s2;
                    data.dynamic_r2 = actData.dynamic_r2;
                    isTrueAtr = true;
                    volatilityLabel = "ATR(14)";
                  } else if (actData.ihsg_high != null && actData.ihsg_low != null) {
                    const dayRange = Math.round(Number(actData.ihsg_high) - Number(actData.ihsg_low));
                    data.ihsg_atr14 = dayRange;
                    isTrueAtr = false;
                    volatilityLabel = "Prev-Day Range";
                    if (data.ihsg_close) {
                      data.dynamic_s1 = Math.round(data.ihsg_close - dayRange);
                      data.dynamic_r1 = Math.round(data.ihsg_close + dayRange);
                    }
                  }
                }
                if (!data.divergence_alert && actData.foreign_flow?.divergence_alert) {
                  data.divergence_alert = actData.foreign_flow.divergence_alert;
                }
              } catch (e) {}
            }
            const isWebFallback = data.ihsg_source === 'web_fallback' || data.source === 'web_fallback';
            const isUnscorable = data.ihsg_correct === null || data.accuracy_score === null;

            let predData = {};
            if (fs.existsSync(predPath)) {
              try {
                predData = JSON.parse(fs.readFileSync(predPath, 'utf8'));
              } catch (e) {}
            }
            let briefText = "";
            if (fs.existsSync(briefPath)) {
              try {
                briefText = fs.readFileSync(briefPath, 'utf8');
              } catch (e) {}
            }

            // Build clean monitored watchlist (D2: clean ticker, sector, clean sentence note, no raw markdown, no trade-action language)
            const tickers = predData.recommended_tickers || data.recommended_tickers || [];
            let actionableWatchlist = [];
            if (Array.isArray(tickers) && tickers.length > 0) {
              actionableWatchlist = tickers.map(ticker => {
                let note = "Sector catalyst from morning brief — research only";
                if (briefText) {
                  const lines = briefText.split('\n');
                  const matchLine = lines.find(l => l.includes(ticker));
                  if (matchLine) {
                    let cleanL = matchLine
                      .replace(/\*\*(?:Bullish|Bearish|Neutral|BUY|SELL|Buy|Sell)\*\*[:\s-]*/gi, '')
                      .replace(/^[#*\s-]+/, '')
                      .replace(/\[.*?\]/g, '')
                      .replace(/\*\*/g, '')
                      .trim();
                    cleanL = cleanL.replace(/\b(?:buy on weakness|target price|entry level|stop loss|tp|sl)\b/gi, '').trim();
                    if (cleanL.length > 0) {
                      note = cleanL.length > 120 ? `${cleanL.slice(0, 117)}...` : cleanL;
                    }
                  }
                }
                return {
                  ticker,
                  sector: "IDX Focus",
                  bias: "MONITORED",
                  note
                };
              });
            }

            const revLockStatus = predData.lock_status || data.lock_status || "retroactive";
            const revCreatedAt = predData.created_at || data.created_at || null;
            const revLockedAt = (revLockStatus === "locked_pre_open" && revCreatedAt)
              ? (predData.locked_at || data.locked_at || "06:55 WIB")
              : null;

            reviews.push({
              date,
              ...data,
              lock_hash: predData.lock_hash || data.lock_hash || null,
              locked_at: revLockedAt,
              lock_status: revLockStatus,
              hash_computed_at: predData.hash_computed_at || data.hash_computed_at || "2026-10-15",
              created_at: revCreatedAt,
              lock_note: predData.lock_note || data.lock_note || (revLockStatus === "retroactive" ? "Hash added retroactively; not proof of pre-open lock" : null),
              calibrated_confidence: nexusStats?.calibration?.calibrated_confidence_pct ?? predData.calibrated_confidence ?? data.calibrated_confidence ?? null,
              actionable_watchlist: actionableWatchlist.length > 0 ? actionableWatchlist : (data.actionable_watchlist || []),
              is_true_atr14: isTrueAtr,
              volatility_label: volatilityLabel,
              actual_commodities: enrichCommodityMap(data.actual_commodities || {}),
              qualityBadges: {
                isWebFallback,
                confidence: isWebFallback ? 'low' : 'verified',
                isUnscorable,
              },
              sources: slimSourcesMap(sourcesMap, [
                data.summary,
                data.key_risk,
                ...(data.rca_unanticipated || []),
                ...(data.rca_underestimated || []),
                ...(data.rca_overestimated || []),
              ]),
              isPendingReview: false
            });
          } catch (e) {
            console.error(`Failed to parse ${reviewPath}`, e);
          }
        } else if (fs.existsSync(predPath)) {
          // Morning session awaiting market close review
          try {
            const predContent = fs.readFileSync(predPath, 'utf8');
            const pred = JSON.parse(predContent);
            let summaryText = "";
            let briefText = "";
            if (fs.existsSync(briefPath)) {
              briefText = fs.readFileSync(briefPath, 'utf8');
              const match = briefText.match(/### 1\.[^\n]+\n-\s+\*\*Summary\*\*:\s*([^\n]+)/);
              summaryText = match ? match[1] : (pred.key_risk || "Morning brief active.");
            }

            // Convert predicted sectors to display map
            const sectorAccuracy = {};
            (pred.sector_bullish || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'BULLISH'; });
            (pred.sector_bearish || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'BEARISH'; });
            (pred.sector_neutral || []).forEach(s => { sectorAccuracy[s.replace(/\s*\([^)]*\)/, '')] = 'NEUTRAL'; });

            let previousClose = null;
            let yesterdayUsdIdr = null;
            let yesterdayCommodities = null;

            const mockDateSet = new Set(detectedMockRuns.map(m => m.date));
            const sortedPastDates = dates
              .filter(d => /^\d{4}-\d{2}-\d{2}$/.test(d) && d < date && (!minDate || d >= minDate) && !mockDateSet.has(d) && !checkRunDirProvenance(path.join(runsDir, d)).isMock)
              .sort()
              .reverse();

            let yesterdayAtr = null;
            let isTrueAtr = true;
            let volatilityLabel = "ATR(14)";

            if (sortedPastDates.length > 0) {
              const prevActualsPath = path.join(runsDir, sortedPastDates[0], 'evening_actuals.json');
              if (fs.existsSync(prevActualsPath)) {
                try {
                  const pastAct = JSON.parse(fs.readFileSync(prevActualsPath, 'utf8'));
                  if (pastAct.ihsg_close != null) previousClose = pastAct.ihsg_close;
                  else if (pastAct.ihsg?.close != null) previousClose = pastAct.ihsg.close;

                  if (pastAct.ihsg_atr14 != null) {
                    yesterdayAtr = pastAct.ihsg_atr14;
                    isTrueAtr = true;
                    volatilityLabel = "ATR(14)";
                  } else if (pastAct.ihsg_high != null && pastAct.ihsg_low != null) {
                    yesterdayAtr = Math.round(Number(pastAct.ihsg_high) - Number(pastAct.ihsg_low));
                    isTrueAtr = false;
                    volatilityLabel = "Prev-Day Range";
                  }

                  if (pastAct.usdidr_rate != null) yesterdayUsdIdr = pastAct.usdidr_rate;
                  else if (pastAct.usdidr?.rate != null) yesterdayUsdIdr = pastAct.usdidr.rate;
                  else if (typeof pastAct.usdidr === 'number') yesterdayUsdIdr = pastAct.usdidr;

                  if (pastAct.commodities && Object.keys(pastAct.commodities).length > 0) {
                    yesterdayCommodities = pastAct.commodities;
                  }
                } catch (e) {}
              }
            }

            // Monitored Watchlist derived strictly from brief — remove trade-action "BUY" language
            let actionableWatchlist = [];
            if (Array.isArray(pred.recommended_tickers) && pred.recommended_tickers.length > 0) {
              actionableWatchlist = pred.recommended_tickers.map(ticker => {
                let note = "Sector catalyst from morning brief — research only";
                if (briefText) {
                  const lines = briefText.split('\n');
                  const matchLine = lines.find(l => l.includes(ticker));
                  if (matchLine) {
                    let cleanL = matchLine
                      .replace(/\*\*(?:Bullish|Bearish|Neutral|BUY|SELL|Buy|Sell)\*\*[:\s-]*/gi, '')
                      .replace(/^[#*\s-]+/, '')
                      .replace(/\[.*?\]/g, '')
                      .replace(/\*\*/g, '')
                      .trim();
                    cleanL = cleanL.replace(/\b(?:buy on weakness|target price|entry level|stop loss|tp|sl)\b/gi, '').trim();
                    if (cleanL.length > 0) {
                      note = cleanL.length > 120 ? `${cleanL.slice(0, 117)}...` : cleanL;
                    }
                  }
                }
                return {
                  ticker,
                  sector: "IDX Focus",
                  bias: "MONITORED",
                  note
                };
              });
            }

            const isPastSession = date < todayKey;
            const predLockStatus = pred.lock_status || "retroactive";
            const predCreatedAt = pred.created_at || null;
            const predLockedAt = (predLockStatus === "locked_pre_open" && predCreatedAt)
              ? (pred.locked_at || "06:55 WIB")
              : null;

            reviews.push({
              date,
              ihsg_predicted: pred.ihsg_signal || "Neutral",
              ihsg_confidence: pred.ihsg_confidence || null,
              calibrated_confidence: nexusStats?.calibration?.calibrated_confidence_pct ?? pred.calibrated_confidence ?? null,
              lock_hash: pred.lock_hash || null,
              locked_at: predLockedAt,
              lock_status: predLockStatus,
              hash_computed_at: pred.hash_computed_at || "2026-10-15",
              created_at: predCreatedAt,
              lock_note: pred.lock_note || (predLockStatus === "retroactive" ? "Hash added retroactively; not proof of pre-open lock" : null),
              ihsg_actual: isPastSession ? "Not reviewed" : "Pending Close",
              ihsg_actual_pct: null,
              ihsg_correct: null,
              foreign_flow_predicted: pred.foreign_flow_signal || "Neutral",
              foreign_flow_actual: isPastSession ? "Not reviewed" : "Market Open",
              foreign_flow_correct: null,
              ihsg_close: previousClose,
              previous_close: previousClose,
              ihsg_atr14: yesterdayAtr,
              is_true_atr14: isTrueAtr,
              volatility_label: volatilityLabel,
              dynamic_s1: (previousClose && yesterdayAtr) ? Math.round(previousClose - yesterdayAtr) : null,
              dynamic_r1: (previousClose && yesterdayAtr) ? Math.round(previousClose + yesterdayAtr) : null,
              actual_usdidr: yesterdayUsdIdr,
              actual_commodities: enrichCommodityMap(yesterdayCommodities || {}),
              actionable_watchlist: actionableWatchlist,
              sector_accuracy: sectorAccuracy,
              accuracy_score: null, // Never report 0 for pending/unreviewed sessions
              rca_unanticipated: [],
              rca_underestimated: [],
              rca_overestimated: [],
              lessons: [],
              summary: summaryText,
              key_risk: pred.key_risk || "",
              recommended_tickers: pred.recommended_tickers || [],
              sources: slimSourcesMap(sourcesMap, [summaryText, pred.key_risk]),
              isPendingReview: true,
              isOlderPending: isPastSession
            });
          } catch (e) {
            console.error(`Failed to parse ${predPath}`, e);
          }
        }
      }
    }

    // Sort reviews by date descending
    reviews.sort((a, b) => b.date.localeCompare(a.date));

    // Pipeline Health & Staleness Check (trading days)
    const latestDate = reviews.length > 0 ? reviews[0].date : null;
    let tradingDaysSinceLatest = 0;
    if (latestDate && latestDate < todayKey) {
      // Walk days strictly between latestDate and todayKey
      let cur = new Date(latestDate + 'T00:00:00Z');
      const target = new Date(todayKey + 'T00:00:00Z');
      cur.setUTCDate(cur.getUTCDate() + 1);
      while (cur <= target) {
        const y = cur.getUTCFullYear();
        const m = String(cur.getUTCMonth() + 1).padStart(2, '0');
        const d = String(cur.getUTCDate()).padStart(2, '0');
        const curStr = `${y}-${m}-${d}`;
        const dayOfWeek = cur.getUTCDay();
        const isWeekend = (dayOfWeek === 0 || dayOfWeek === 6);
        const isHoliday = Boolean(holidaysMap[curStr]);
        if (!isWeekend && !isHoliday) {
          tradingDaysSinceLatest += 1;
        }
        cur.setUTCDate(cur.getUTCDate() + 1);
      }
    }

    const isPipelineStale = tradingDaysSinceLatest > 1;

    // Compute scorable totals and sector breadth
    let evaluatedDays = 0;
    let sumAccuracy = 0;
    let scorableAccCount = 0;
    let recentLessons = [];

    reviews.forEach(r => {
      if (!r.isPendingReview) {
        evaluatedDays += 1;
        if (r.accuracy_score !== null && r.accuracy_score !== undefined) {
          sumAccuracy += Number(r.accuracy_score);
          scorableAccCount += 1;
        }
      }
      if (r.lessons && r.lessons.length > 0) {
        recentLessons.push(...r.lessons.map(l => ({ date: r.date, text: l })));
      }
    });

    const avgAccuracy = scorableAccCount > 0 ? (sumAccuracy / scorableAccCount).toFixed(1) : null;

    // Sector breadth: count predicted bias for active session, and actual hit/miss separately
    let sectorBreadth = { bullish: 0, bearish: 0, neutral: 0, total: 0 };
    if (reviews.length > 0) {
      const latestSec = reviews[0].sector_accuracy || {};
      for (const [_, val] of Object.entries(latestSec)) {
        sectorBreadth.total += 1;
        const v = String(val).toUpperCase();
        if (v === 'BULLISH') sectorBreadth.bullish += 1;
        else if (v === 'BEARISH') sectorBreadth.bearish += 1;
        else if (v === 'NEUTRAL') sectorBreadth.neutral += 1;
      }
    }

    // Telemetry totalRuns (never fabricate reviews.length * 2)
    let totalRuns = null;
    const telemetryPath = path.join(runsDir, 'global', 'telemetry.json');
    if (fs.existsSync(telemetryPath)) {
      try {
        const telemetry = JSON.parse(fs.readFileSync(telemetryPath, 'utf8'));
        totalRuns = telemetry?.stats?.totalRuns ?? null;
      } catch (e) {}
    }

    const mockDataDetected = detectedMockRuns.length > 0;

    const response = NextResponse.json({
      success: true,
      isDemo,
      pipelineHealth: {
        latestDate,
        todayKey,
        tradingDaysSinceLatest,
        isStale: isPipelineStale,
        staleMessage: isPipelineStale ? `Last update: ${latestDate} (${tradingDaysSinceLatest} trading days ago). Automated pipeline may be paused.` : null,
        mockDataDetected,
        detectedMockRuns,
        mockDataMessage: mockDataDetected
          ? `Test data detected: ${detectedMockRuns.length} mock/synthetic run(s) (${detectedMockRuns.map(m => m.date).join(', ')}) were found in runs/ and excluded from all metrics.`
          : null,
      },
      holidays: holidaysMap,
      nexusStats: nexusStats || null,
      stats: {
        totalDays: evaluatedDays,
        avgAccuracy: nexusStats?.rolling_avg_accuracy ?? avgAccuracy,
        directionAccuracy: nexusStats?.direction_accuracy_pct ?? null,
        directionCi95: nexusStats?.direction_ci_95 ?? null,
        baselines: nexusStats?.baselines ?? null,
        calibration: nexusStats?.calibration ?? null,
        payoff: nexusStats?.payoff ?? null,
        isSampleSufficient: nexusStats?.is_sample_sufficient ?? false,
        sampleWarning: nexusStats?.sample_warning ?? null,
        flowAccuracy: nexusStats?.flow_accuracy_pct ?? null,
        sectorAccuracy: nexusStats?.sector_accuracy_pct ?? null,
        totalRuns: totalRuns,
        sectorBreadth,
        historyRescoredAt: nexusStats?.history_rescored_at ?? null,
      },
      recentLessons: recentLessons.slice(0, 10),
      reviews
    });
    response.headers.set('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=300');
    return response;
    
  } catch (error) {
    console.error("API Error:", error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
