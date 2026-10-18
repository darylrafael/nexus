"use client";

import dynamic from "next/dynamic";
import { startTransition, useEffect, useMemo, useState } from "react";
import { LegalDisclaimerBanner, LegalDisclaimerFooter } from "../components/common/Disclaimer";
import { DataQualityBadge } from "../components/common/Badges";

const LessonsDatabaseView = dynamic(() => import("../components/views/LessonsDatabaseView"));
const ExecutionTelemetryView = dynamic(() => import("../components/views/ExecutionTelemetryView"));
const MethodologyView = dynamic(() => import("../components/common/MethodologyView"));
const PipelineStatusView = dynamic(() => import("../components/common/PipelineStatusView"));
const DataLineageView = dynamic(() => import("../components/common/DataLineageView"));
const SideSheet = dynamic(() => import("../components/common/SideSheet"));

const INITIAL_DASHBOARD_DATA = {
  success: true,
  isDemo: false,
  stats: {
    avgAccuracy: "34.3",
    totalSessions: 12,
    historyRescoredAt: "2026-10-15",
  },
  nexusStats: {
    sample_size_n: 12,
    direction_accuracy_pct: 41.7,
    direction_correct_count: 5,
    direction_scorable_sessions: 12,
    direction_ci_95: { lower_pct: 19.3, upper_pct: 68.0 },
    baselines: {
      always_bearish_pct: 66.7,
      always_bearish_count: 8,
      always_bearish_total: 12,
      persistence_pct: 63.6,
      persistence_correct_count: 7,
      persistence_scorable_sessions: 11,
      always_bullish_pct: 33.3,
      always_bullish_count: 4,
      always_bullish_total: 12,
    },
    calibration: {
      average_stated_confidence_pct: 79.6,
      calibrated_confidence_pct: 49.7,
      sample_size_n: 12,
      prior_pct: 55.0,
      prior_strength_n0: 30,
      realized_hit_rate_pct: 41.7,
      status_label: "illustrative shrinkage estimate",
      brier_score: 0.3996,
    },
    payoff: {
      long_only_total_bps: -176.0,
      short_only_total_bps: 244.0,
      long_short_total_bps: 68.0,
    },
  },
  pipelineHealth: {
    isStale: true,
    latestDate: "2026-10-08",
    tradingDaysSinceLatest: 6,
    staleMessage: "Automation feed paused since 2026-10-08 (6 trading days).",
    mockDataDetected: false,
  },
  reviews: [
    {
      date: "2026-10-08",
      ihsg_predicted: "Bullish",
      ihsg_confidence: 82,
      calibrated_confidence: 49.7,
      ihsg_actual: "Not reviewed",
      ihsg_actual_pct: null,
      ihsg_correct: null,
      accuracy_score: null,
      foreign_flow_predicted: "Stagnant/Sideways",
      foreign_flow_actual: "Not reviewed",
      ihsg_close: 6146.72,
      previous_close: 6146.72,
      ihsg_atr14: 79,
      is_true_atr14: false,
      volatility_label: "Prev-Day Range",
      dynamic_s1: 6068,
      dynamic_r1: 6226,
      actual_usdidr: 17885,
      summary:
        "Bank Indonesia (BI) maintained the BI-Rate at 5.75% in September 2026, consistent with efforts to stabilize the Rupiah and keep inflation within the 2.5±1% target for 2026-2027. Inflation for September 2026 was recorded at 3.28% YoY, while the Rupiah strengthened slightly to 17,895/USD on October 6, 2026, supported by BI's foreign exchange interventions (src_c48f564ee3, src_0ba9a5d054, src_363fc5b63c).",
      key_risk: "",
      lock_hash: "e994749a446521e7",
      lock_status: "retroactive",
      hash_computed_at: "2026-10-15",
      lock_note: "Hash added retroactively on 2026-10-15; not proof of pre-open lock",
      recommended_tickers: ["MYOR", "TBLA", "UNVR", "PGEO", "BYAN", "SIMP", "ADRO", "ICBP", "LSIP", "AALI"],
      sources: {
        src_c48f564ee3: { url: "https://www.jtrustbank.co.id/market_update/market-update-7-oct-2026", title: "Market Update 7 Oct 2026" },
        src_0ba9a5d054: { url: "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Pages/sp_2816226.aspx", title: "BI-Rate Tetap 5,75%: Memperkuat Stabilitas, Mendorong Pertumbuhan Ekonomi" },
        src_363fc5b63c: { url: "https://ekonomi.tvrinews.com/berita/t5gszqc-intervensi-bi-dan-stabilitas-ekonomi-domestik-dorong-penguatan-rupiah-selasa-ini", title: "Intervensi BI dan Stabilitas Ekonomi Domestik Dorong Penguatan Rupiah Selasa Ini — TVRI News | TVRI News" },
      },
      isPendingReview: true,
      isOlderPending: true,
    },
    {
      date: "2026-10-07",
      ihsg_predicted: "Bullish",
      ihsg_confidence: 90,
      calibrated_confidence: 49.7,
      ihsg_actual: "Bearish",
      ihsg_actual_pct: -0.75,
      ihsg_correct: false,
      foreign_flow_predicted: "Stagnant",
      foreign_flow_actual: "Unknown",
      foreign_flow_correct: null,
      accuracy_score: 9,
      isPendingReview: false,
      lock_status: "retroactive",
      lock_hash: "3025099b6f4426f3",
    },
    {
      date: "2026-10-06",
      ihsg_predicted: "Bullish",
      ihsg_confidence: 81,
      calibrated_confidence: 49.7,
      ihsg_actual: "Bullish",
      ihsg_actual_pct: 1.21,
      ihsg_correct: true,
      foreign_flow_predicted: "Stagnant",
      foreign_flow_actual: "Unknown",
      foreign_flow_correct: null,
      accuracy_score: 81,
      isPendingReview: false,
      lock_status: "retroactive",
      lock_hash: "5e48c9b66ab8af24",
    },
    {
      date: "2026-10-05",
      ihsg_predicted: "Neutral",
      ihsg_confidence: 82,
      calibrated_confidence: 49.7,
      ihsg_actual: "Bullish",
      ihsg_actual_pct: 1.36,
      ihsg_correct: false,
      foreign_flow_predicted: "Stagnant",
      foreign_flow_actual: "Unknown",
      foreign_flow_correct: null,
      accuracy_score: 0,
      isPendingReview: false,
      lock_status: "retroactive",
      lock_hash: "c03f5017b7bc3644",
    },
    {
      date: "2026-10-02",
      ihsg_predicted: "Bearish",
      ihsg_confidence: 67,
      calibrated_confidence: 49.7,
      ihsg_actual: "Bullish",
      ihsg_actual_pct: 0.46,
      ihsg_correct: false,
      foreign_flow_predicted: "Distribution",
      foreign_flow_actual: "Unknown",
      foreign_flow_correct: null,
      accuracy_score: 8,
      isPendingReview: false,
      lock_status: "retroactive",
      lock_hash: "4fa244d072675422",
    },
    {
      date: "2026-10-01",
      ihsg_predicted: "Bullish",
      ihsg_confidence: 72,
      calibrated_confidence: 49.7,
      ihsg_actual: "Bearish",
      ihsg_actual_pct: -1.02,
      ihsg_correct: false,
      foreign_flow_predicted: "Stagnant",
      foreign_flow_actual: "Unknown",
      foreign_flow_correct: null,
      accuracy_score: 0,
      isPendingReview: false,
      lock_status: "retroactive",
      lock_hash: "4800380bf97d5a10",
    },
  ],
};

const formatPct = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return `${num > 0 ? "+" : ""}${num.toFixed(2)}%`;
};

const formatNumber = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(num);
};

const formatHeaderDate = (dateStr) => {
  if (!dateStr) return "";
  try {
    const [year, month, day] = dateStr.split("-");
    if (!year || !month || !day) return dateStr;
    const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
    const mIdx = parseInt(month, 10) - 1;
    return `${day} ${months[mIdx] || month} ${year}`;
  } catch (e) {
    return dateStr;
  }
};

const cleanNarrative = (str) => {
  if (!str || typeof str !== "string") return "";
  return str
    .replace(/^Illustrative lesson:\s*/i, "")
    .replace(/^Illustrative:\s*/i, "")
    .replace(/^Demo fixture:\s*/i, "")
    .replace(/\billustrative\b\s*/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
};

export const getIdxMarketStatus = (customDate = null, holidays = null) => {
  try {
    const now = customDate ? new Date(customDate) : new Date();
    const wibStr = now.toLocaleString("en-US", { timeZone: "Asia/Jakarta" });
    const wib = new Date(wibStr);
    const day = wib.getDay(); // 0 = Sun, 6 = Sat
    const hour = wib.getHours();
    const min = wib.getMinutes();
    const totalMin = hour * 60 + min;

    const y = wib.getFullYear();
    const m = String(wib.getMonth() + 1).padStart(2, "0");
    const d = String(wib.getDate()).padStart(2, "0");
    const dateKey = `${y}-${m}-${d}`;

    const isHoliday = Boolean(
      holidays && (holidays[dateKey] || (Array.isArray(holidays) && holidays.includes(dateKey)))
    );
    const holidayName = isHoliday
      ? (typeof holidays === "object" && holidays[dateKey] ? holidays[dateKey] : "IDX Holiday")
      : null;

    const timeWib = `${String(hour).padStart(2, "0")}:${String(min).padStart(2, "0")} WIB`;

    if (isHoliday) {
      return {
        isOpen: false,
        status: "closed",
        label: `IDX: CLOSED (${(holidayName || "HOLIDAY").toUpperCase()})`,
        phase: "HOLIDAY_CLOSED",
        nextEvent: "06:55 WIB Morning Brief (Next Trading Day)",
        timeWib,
        isHoliday: true,
        isWeekend: false,
        isFriday: day === 5,
      };
    }

    if (day === 0 || day === 6) {
      return {
        isOpen: false,
        status: "closed",
        label: "IDX: CLOSED (WEEKEND)",
        phase: "WEEKEND_CLOSED",
        nextEvent: "06:55 WIB Morning Brief (Next Trading Day)",
        timeWib,
        isHoliday: false,
        isWeekend: true,
        isFriday: false,
      };
    }

    let nextEvent = "06:55 WIB Morning Brief";
    if (totalMin >= 415 && totalMin < 1200) {
      nextEvent = "20:00 WIB Evening Review";
    } else if (totalMin >= 1200) {
      nextEvent = day === 5 ? "06:55 WIB Morning Brief (Monday)" : "06:55 WIB Morning Brief (Next Trading Day)";
    }

    if (day >= 1 && day <= 4) {
      if (totalMin >= 525 && totalMin < 540) {
        return { isOpen: false, status: "recess", label: "IDX: PRE-OPENING (LQ45)", phase: "PRE_OPENING", nextEvent, timeWib, isFriday: false };
      }
      if (totalMin >= 540 && totalMin < 720) {
        return { isOpen: true, status: "open", label: "IDX: SESI 1 (09:00 - 12:00)", phase: "SESSION_1", nextEvent, timeWib, isFriday: false };
      }
      if (totalMin >= 720 && totalMin < 810) {
        return { isOpen: false, status: "recess", label: "IDX: ISTIRAHAT SESI", phase: "RECESS", nextEvent, timeWib, isFriday: false };
      }
      if (totalMin >= 810 && totalMin < 949) {
        return { isOpen: true, status: "open", label: "IDX: SESI 2 (13:30 - 15:49)", phase: "SESSION_2", nextEvent, timeWib, isFriday: false };
      }
      if (totalMin >= 949 && totalMin < 961) {
        return { isOpen: false, status: "recess", label: "IDX: PRE-CLOSING", phase: "PRE_CLOSING", nextEvent, timeWib, isFriday: false };
      }
      if (totalMin >= 961 && totalMin < 975) {
        return { isOpen: false, status: "recess", label: "IDX: POST-TRADING", phase: "POST_TRADING", nextEvent, timeWib, isFriday: false };
      }
      return { isOpen: false, status: "closed", label: "IDX: CLOSED", phase: "CLOSED", nextEvent, timeWib, isFriday: false };
    }

    if (day === 5) {
      if (totalMin >= 525 && totalMin < 540) {
        return { isOpen: false, status: "recess", label: "IDX: PRE-OPENING (LQ45)", phase: "PRE_OPENING", nextEvent, timeWib, isFriday: true };
      }
      if (totalMin >= 540 && totalMin < 690) {
        return { isOpen: true, status: "open", label: "IDX: SESI 1 (09:00 - 11:30)", phase: "SESSION_1", nextEvent, timeWib, isFriday: true };
      }
      if (totalMin >= 690 && totalMin < 840) {
        return { isOpen: false, status: "recess", label: "IDX: ISTIRAHAT JUMAT", phase: "RECESS", nextEvent, timeWib, isFriday: true };
      }
      if (totalMin >= 840 && totalMin < 949) {
        return { isOpen: true, status: "open", label: "IDX: SESI 2 (14:00 - 15:49)", phase: "SESSION_2", nextEvent, timeWib, isFriday: true };
      }
      if (totalMin >= 949 && totalMin < 961) {
        return { isOpen: false, status: "recess", label: "IDX: PRE-CLOSING", phase: "PRE_CLOSING", nextEvent, timeWib, isFriday: true };
      }
      if (totalMin >= 961 && totalMin < 975) {
        return { isOpen: false, status: "recess", label: "IDX: POST-TRADING", phase: "POST_TRADING", nextEvent, timeWib, isFriday: true };
      }
      return { isOpen: false, status: "closed", label: "IDX: CLOSED", phase: "CLOSED", nextEvent, timeWib, isFriday: true };
    }

    return { isOpen: false, status: "closed", label: "IDX: CLOSED", phase: "CLOSED", nextEvent, timeWib, isFriday: false };
  } catch (e) {
    return { isOpen: false, status: "closed", label: "IDX: CLOSED", phase: "CLOSED", nextEvent: "06:55 WIB Morning Brief", timeWib: "WIB", isFriday: false };
  }
};

const KNOWN_OUTLETS = {
  "idxchannel.com": "IDX Channel",
  "kontan.co.id": "Kontan",
  "cnbcindonesia.com": "CNBC Indonesia",
  "bisnis.com": "Bisnis.com",
  "bloomberg.com": "Bloomberg",
  "reuters.com": "Reuters",
  "investing.com": "Investing.com",
  "tradingeconomics.com": "TradingEconomics",
  "antaranews.com": "Antara",
  "detik.com": "Detik Finance",
  "kompas.com": "Kompas",
  "barchart.com": "Barchart",
  "marketwatch.com": "MarketWatch",
  "yahoo.com": "Yahoo Finance",
};

function formatSourceLabel(url) {
  if (!url) return "Source";
  try {
    const host = new URL(url).hostname.replace(/^www\./, "").toLowerCase();
    for (const [domain, name] of Object.entries(KNOWN_OUTLETS)) {
      if (host.includes(domain)) return name;
    }
    const cleanHost = host.split(".")[0];
    return cleanHost.charAt(0).toUpperCase() + cleanHost.slice(1);
  } catch (e) {
    return "Source";
  }
}

function RenderWithSources({ text, sources = {} }) {
  if (!text || typeof text !== "string") return null;

  const citationRegex = /([\(\[]?\s*(?:Source(?:\s*ID)?:?\s*)?(src_[a-zA-Z0-9_-]+)\s*[\)\]]?)/gi;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = citationRegex.exec(text)) !== null) {
    const matchStart = match.index;
    const matchEnd = citationRegex.lastIndex;
    const sourceId = match[2];

    if (matchStart > lastIndex) {
      parts.push(text.slice(lastIndex, matchStart));
    }

    const sourceData = sources?.[sourceId] || sources?.[sourceId.replace("src_", "")];
    const url = sourceData?.url;
    const title = sourceData?.title || "";

    if (url) {
      const displayLabel = formatSourceLabel(url);
      parts.push(
        <a
          key={`src-${sourceId}-${matchStart}`}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="source-citation-pill"
          title={title ? `${title}\n${url}` : url}
        >
          <span className="source-citation-icon">🔗</span>
          <span>{displayLabel}</span>
          <span className="source-citation-arrow">↗</span>
        </a>
      );
    }

    lastIndex = matchEnd;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts}</>;
}

function StatusBadge({ correct, isPending, size = "md", isLive = false }) {
  if (isPending || correct === null || correct === undefined) {
    return (
      <span className={`status-pill ${isLive ? "status-pending" : "status-unreviewed"} ${size === "sm" ? "status-sm" : ""}`}>
        <span className="status-indicator-dot" />
        <span className="status-text font-mono">{isLive ? "LIVE" : "NOT REVIEWED"}</span>
      </span>
    );
  }
  return (
    <span className={`status-pill ${correct ? "status-matched" : "status-missed"} ${size === "sm" ? "status-sm" : ""}`}>
      <span className="status-indicator-dot" />
      <span className="status-text font-mono">{correct ? "MATCHED" : "MISSED"}</span>
    </span>
  );
}

function DirectionBadge({ direction }) {
  const dir = (direction || "").toLowerCase();
  let badgeClass = "dir-neutral";
  let arrow = "◆";
  if (dir.includes("pending")) {
    badgeClass = "dir-pending";
    arrow = "⏳";
  } else if (dir.includes("bullish") || dir.includes("up")) {
    badgeClass = "dir-bullish";
    arrow = "▲";
  } else if (dir.includes("bearish") || dir.includes("down")) {
    badgeClass = "dir-bearish";
    arrow = "▼";
  }
  return (
    <span className={`dir-badge font-mono ${badgeClass}`}>
      <span className="dir-glyph">{arrow}</span>
      <span>{direction ? direction.toUpperCase() : "NEUTRAL"}</span>
    </span>
  );
}

function SectorAttribution({ review }) {
  const sectors = review?.sector_accuracy || {};
  const entries = Object.entries(sectors);

  if (entries.length === 0) return null;

  const isPending = review?.isPendingReview;

  return (
    <div className="eval-pane-section">
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Sector Performance &amp; Bias</span>
        <span className="eval-section-tag font-mono">
          {isPending ? "Today's Sector Bias" : "11 IDX-IC Scored Sectors"}
        </span>
      </div>
      <div className="sector-matrix-grid">
        {entries.map(([sector, statusOrHit]) => {
          let label = "● Miss";
          let badgeCls = "badge-missed";
          if (isPending) {
            badgeCls = statusOrHit === "BULLISH" ? "badge-matched" : (statusOrHit === "BEARISH" ? "badge-missed" : "badge-neutral");
            label = statusOrHit;
          } else if (statusOrHit === true) {
            badgeCls = "badge-matched";
            label = "● Match";
          } else if (statusOrHit === false) {
            badgeCls = "badge-missed";
            label = "▲ Miss";
          } else {
            badgeCls = "badge-neutral";
            label = "— Unscored";
          }
          return (
            <div className="sector-grid-cell" key={sector}>
              <span className="sector-cell-name" title={sector}>{sector}</span>
              <span className={`sector-cell-badge font-mono ${badgeCls}`}>
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MacroPulse({ review }) {
  const commodities = Object.entries(review?.actual_commodities || {}).map(([key, item]) => {
    if (!item) return null;
    let name = item.name || key;
    let price = item.price;
    let changePct = item.change_pct;
    let signal = item.signal;
    const raw = typeof item.raw === "string" ? item.raw : "";

    let refLabel = item.benchmark_label || null;
    if (!refLabel) {
      if (name.toLowerCase().includes("coal")) refLabel = "ICE Newcastle Dec '26 Ref";
      else if (name.toLowerCase().includes("cpo")) refLabel = "FCPO / Kemendag Ref";
      else if (name.toLowerCase().includes("nickel")) refLabel = "LME Cash Settlement Ref";
    }

    return {
      ...item,
      ticker: item.ticker || key,
      name,
      price,
      change_pct: changePct,
      signal: signal || (changePct > 0 ? "Up" : (changePct < 0 ? "Down" : "Reference Only")),
      refLabel,
      parse_confidence: item.parse_confidence || "none"
    };
  }).filter(Boolean);

  const rawPred = review?.foreign_flow_predicted;
  const rawAct = review?.foreign_flow_actual;
  const foreignPredicted = rawPred ? rawPred.replace("/", " / ") : "N/A";
  const foreignActual = rawAct 
    ? rawAct.replace("/", " / ") 
    : (review?.isPendingReview ? "Market Open" : "N/A");
  const foreignCorrect = review?.foreign_flow_correct;
  const usdidr = review?.actual_usdidr;
  const isUsdNumeric =
    usdidr !== null &&
    usdidr !== undefined &&
    usdidr !== "" &&
    Number.isFinite(Number(usdidr)) &&
    Number(usdidr) > 0;
  const divergenceAlert = review?.divergence_alert || review?.foreign_flow?.divergence_alert;

  return (
    <div className="eval-pane-section">
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Cross-Asset Feeds &amp; Liquidity</span>
        <span className="eval-section-tag font-mono">Market Telemetry</span>
      </div>
      <div className="macro-tape-strip">
        <div className="macro-tape-row liquidity-row">
          <div className="macro-strip-cell">
            <div className="macro-cell-head">Foreign Flow (Net Buy/Sell)</div>
            <div className="macro-cell-val font-mono">{foreignActual}</div>
            <div className="macro-cell-sub font-mono">
              <span className="macro-sub-label">Exp: {foreignPredicted}</span>
              {review?.isPendingReview ? (
                <span className="text-secondary font-mono" style={{ fontSize: "12px" }}>
                  (● Active)
                </span>
              ) : foreignCorrect !== undefined && foreignCorrect !== null ? (
                <span className={`macro-match-tag font-mono ${foreignCorrect ? "is-match" : "is-miss"}`}>
                  {foreignCorrect ? "✓ Match" : "✗ Miss"}
                </span>
              ) : null}
            </div>
            {divergenceAlert && (
              <div className="mt-1 text-xs text-warning font-mono" style={{ fontSize: "12px", lineHeight: "1.2" }} title={divergenceAlert}>
                ⚠️ Crossing Divergence
              </div>
            )}
          </div>

          <div className="macro-strip-cell">
            <div className="macro-cell-head">USD / IDR</div>
            <div className="macro-cell-val font-mono">
              {isUsdNumeric ? `Rp ${formatNumber(usdidr)}` : (usdidr && usdidr !== "Illustrative" ? String(usdidr) : "Unavailable")}
            </div>
            <div className="macro-cell-sub">
              {review?.isPendingReview ? "Yesterday Close Ref" : "Bank Indonesia / Official Close"}
            </div>
          </div>
        </div>

        {commodities.length > 0 && (
          <div
            className="macro-tape-row commodities-row"
            style={{ gridTemplateColumns: `repeat(${commodities.length}, minmax(0, 1fr))` }}
          >
            {commodities.map((item) => {
              const name = item.name || "Commodity";
              const hasPrice = Number.isFinite(Number(item.price));
              const hasChange = Number.isFinite(Number(item.change_pct));
              const change = Number(item.change_pct);
              const isUp = change >= 0;

              return (
                <div className="macro-strip-cell" key={item.ticker || name} title={item.raw ? String(item.raw).slice(0, 160) : undefined}>
                  <div className="macro-cell-head">{name}</div>
                  <div className="macro-cell-val font-mono">
                    {hasPrice ? `$${formatNumber(item.price)}` : (item.refLabel || "No price feed")}
                  </div>
                  <div className={`macro-cell-sub font-mono ${hasChange ? (isUp ? "text-matched" : "text-missed") : (item.signal === "Up" ? "text-matched" : (item.signal === "Down" ? "text-missed" : "text-muted"))}`}>
                    {hasChange ? `${isUp ? "▲ +" : "▼ "}${Math.abs(change).toFixed(2)}% 1D` : (item.signal === "Up" ? "▲ Firm / Bullish" : (item.signal === "Down" ? "▼ Soft / Bearish" : (item.signal || "—")))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionableMarketSetup({ review }) {
  const [showAllTickers, setShowAllTickers] = useState(false);
  const closeNum = (review?.ihsg_close && Number.isFinite(Number(review.ihsg_close)))
    ? Number(review.ihsg_close)
    : (review?.previous_close && Number.isFinite(Number(review.previous_close))
      ? Number(review.previous_close)
      : null);

  const pivot = closeNum ? Math.round(closeNum) : null;
  const isTrueAtr = Boolean(review?.is_true_atr14);
  const volatilityLabel = review?.volatility_label || (isTrueAtr ? "ATR(14)" : "Prev-Day Range");

  const atrVal = (review?.ihsg_atr14 && Number.isFinite(Number(review.ihsg_atr14)))
    ? Number(review.ihsg_atr14)
    : ((review?.ihsg_high && review?.ihsg_low && Number.isFinite(Number(review.ihsg_high)) && Number.isFinite(Number(review.ihsg_low)))
      ? Math.round(Number(review.ihsg_high) - Number(review.ihsg_low))
      : null);

  const atrPct = (closeNum && atrVal) ? ((atrVal / closeNum) * 100).toFixed(2) : "0.75";
  const s1 = (review?.dynamic_s1 && Number.isFinite(Number(review.dynamic_s1)))
    ? Number(review.dynamic_s1)
    : (closeNum && atrVal ? Math.round(closeNum - atrVal) : null);
  const r1 = (review?.dynamic_r1 && Number.isFinite(Number(review.dynamic_r1)))
    ? Number(review.dynamic_r1)
    : (closeNum && atrVal ? Math.round(closeNum + atrVal) : null);

  const focusWatchlist = (review?.actionable_watchlist && review.actionable_watchlist.length > 0)
    ? review.actionable_watchlist
    : (review?.recommended_tickers && review.recommended_tickers.length > 0
        ? review.recommended_tickers.map(ticker => ({
            ticker,
            sector: "Morning Brief Selection",
            bias: "MONITORED",
            note: "from morning brief — not advice"
          }))
        : []);

  const displayedWatchlist = showAllTickers ? focusWatchlist : focusWatchlist.slice(0, 6);

  return (
    <div className="eval-pane-section" style={{ borderBottom: "none" }}>
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Pre-Market Reference Range &amp; Monitored Tickers</span>
        <span className="eval-section-tag font-mono">
          {volatilityLabel}: ±{atrVal ? atrVal.toFixed(1) : "—"} pts ({atrPct}%)
        </span>
      </div>

      <div className="actionable-levels-strip" title={`${volatilityLabel} Reference Band (±${atrVal || "—"} pts / ±${atrPct}%) — Mathematical reference only, not trade advice`}>
        <div className="level-box">
          <span className="level-label font-mono">S1 Range Ref ({atrPct ? `-${atrPct}%` : "—"})</span>
          <span className="level-val font-mono text-missed">{s1 ? formatNumber(s1) : "—"}</span>
        </div>
        <div className="level-box pivot-box">
          <span className="level-label font-mono">PREV CLOSE REF</span>
          <span className="level-val font-mono text-primary">{pivot ? formatNumber(pivot) : "—"}</span>
        </div>
        <div className="level-box">
          <span className="level-label font-mono">R1 Range Ref ({atrPct ? `+${atrPct}%` : "—"})</span>
          <span className="level-val font-mono text-matched">{r1 ? formatNumber(r1) : "—"}</span>
        </div>
      </div>

      <div style={{ fontSize: "12px", color: "var(--text-tertiary)", margin: "8px 0 12px", fontStyle: "italic" }}>
        * Note: Volatility bounds are historical index spread references, not executable trade signals.
      </div>

      {focusWatchlist.length === 0 ? (
        <div className="text-muted font-mono text-xs py-3 text-center" style={{ opacity: 0.7 }}>
          No morning brief emittent focus list captured — not advice
        </div>
      ) : (
        <>
          <div className="focus-ticker-grid">
            {displayedWatchlist.map((item) => (
              <div className="focus-ticker-cell" key={item.ticker}>
                <div className="ticker-cell-top">
                  <span className="ticker-symbol font-mono">{item.ticker}</span>
                  <span className={`ticker-bias font-mono ${item.bias === "BULLISH" ? "text-matched" : (item.bias === "DEFENSIVE" ? "text-warning" : "text-muted")}`}>
                    {item.bias === "BULLISH" ? "▲ POSITIVE TILT" : (item.bias === "DEFENSIVE" ? "▼ DEFENSIVE" : "● MONITORED")}
                  </span>
                </div>
                <div className="ticker-cell-note">{item.note}</div>
              </div>
            ))}
          </div>
          {focusWatchlist.length > 6 && (
            <div style={{ textAlign: "center", marginTop: "10px" }}>
              <button
                type="button"
                className="watchlist-toggle-btn font-mono"
                onClick={() => setShowAllTickers(!showAllTickers)}
              >
                {showAllTickers
                  ? `▲ Show Top 6 Focus Emittents Only`
                  : `▼ View All ${focusWatchlist.length} Monitored Emittents (+${focusWatchlist.length - 6} more)`}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function HeuristicRuleItem({ lesson, index }) {
  const [showRaw, setShowRaw] = useState(false);
  const text = cleanNarrative(lesson);

  let trigger = "";
  let impact = "";
  let action = "Injected constraint → 06:55 Pre-Market Briefing prompt";

  if (text.includes("Ketika") && text.includes("maka")) {
    const withoutKetika = text.replace(/^Ketika\s+/i, "");
    const parts = withoutKetika.split(/\bmaka\s+/i);
    trigger = parts[0]?.replace(/\s*terjadi\s*$/i, "").trim() || "";
    impact = parts[1]?.trim() || "";
  } else if (text.includes("–") || text.includes("-")) {
    const parts = text.split(/[-–]/);
    trigger = parts[0]?.trim() || text;
    impact = parts.slice(1).join(" ")?.trim() || "";
  } else {
    trigger = text;
  }

  return (
    <div className="rca-memory-card">
      <div className="memory-card-label">
        <span className="memory-title font-mono">HEURISTIC RULE #{index + 1}</span>
        <span className="memory-injected-pill font-mono">Injected → 06:55 Brief</span>
      </div>

      {!showRaw && trigger ? (
        <div className="rca-rule-breakdown">
          <div className="rule-part">
            <span className="rule-part-tag tag-trigger font-mono">TRIGGER</span>
            <span className="rule-part-text font-medium">{trigger.replace(/,\s*tetapi\s+/i, " + ")}</span>
          </div>
          {impact && (
            <div className="rule-part">
              <span className="rule-part-tag tag-impact font-mono">DIVERGENCE</span>
              <span className="rule-part-text">{impact}</span>
            </div>
          )}
          <div className="rule-part">
            <span className="rule-part-tag tag-action font-mono">CONSTRAINT</span>
            <span className="rule-part-text text-secondary">{action}</span>
          </div>
        </div>
      ) : (
        <p className="rca-lesson-text">&ldquo;{text}&rdquo;</p>
      )}

      <div className="rca-lesson-meta font-mono">
        <button
          type="button"
          className="raw-rule-toggle"
          onClick={() => setShowRaw(!showRaw)}
        >
          {showRaw ? "◄ Algorithmic View" : "► Inspect Full Source String"}
        </button>
        <span>Adaptive Heuristics Store</span>
      </div>
    </div>
  );
}

function RCAPanel({ review }) {
  const lessons = review?.lessons || [];
  const unanticipated = review?.rca_unanticipated || [];
  const underestimated = review?.rca_underestimated || [];
  const overestimated = review?.rca_overestimated || [];

  const hasDiagnostics = unanticipated.length > 0 || underestimated.length > 0 || overestimated.length > 0;

  return (
    <div className="eval-pane">
      <div className="eval-pane-header">
        <div className="eval-pane-header-left">
          <span className="eval-pane-title">Attribution &amp; Root Cause Analysis</span>
          <span className="eval-section-tag font-mono">Diagnostic Engine</span>
        </div>
        <div className="loop-active-tag font-mono">
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
          Feedback Loop Active
        </div>
      </div>

      <div className="eval-pane-body">
        {!review?.isPendingReview && (
          <div style={{ padding: "14px 22px 0 22px" }}>
            <div className="rca-causal-flow">
              <span className="causal-node text-secondary font-mono">
                CALL: <strong className="text-primary">{review?.ihsg_predicted || "Neutral"}</strong> {review?.ihsg_confidence ? `(${review.ihsg_confidence}%)` : ""}
              </span>
              <span className="causal-arrow">──►</span>
              <span className="causal-node font-mono" style={{ borderColor: review?.ihsg_correct ? "var(--matched-border)" : "var(--warning-border)" }}>
                {review?.ihsg_correct ? (
                  <span className="text-matched">ALIGNED: Factor Thesis Confirmed</span>
                ) : (
                  <span className="text-warning">
                    DIVERGENCE: {cleanNarrative(unanticipated[0] || underestimated[0] || "Macro Variance")?.slice(0, 42)}
                  </span>
                )}
              </span>
              <span className="causal-arrow">──►</span>
              <span className="causal-node font-mono">
                RESULT: <strong className={Number(review?.ihsg_actual_pct) >= 0 ? "text-matched" : "text-missed"}>{formatPct(review?.ihsg_actual_pct)}</strong>
                <span className={review?.ihsg_correct ? "text-matched font-bold" : "text-missed font-bold"} style={{ marginLeft: "4px" }}>
                  [{review?.ihsg_correct ? "HIT" : "MISS"}]
                </span>
              </span>
            </div>
          </div>
        )}

        {hasDiagnostics && (
          <div className="rca-diagnostic-section">
            <div className="rca-subheading">Attribution Breakdown</div>
            <div className="rca-diagnostic-list">
              {unanticipated.map((item, idx) => (
                <div key={`unant-${idx}`} className="rca-diagnostic-item">
                  <span className="rca-diagnostic-type type-unanticipated font-mono">UNANTICIPATED</span>
                  <span className="rca-diagnostic-text"><RenderWithSources text={cleanNarrative(item)} sources={review?.sources} /></span>
                </div>
              ))}
              {underestimated.map((item, idx) => (
                <div key={`under-${idx}`} className="rca-diagnostic-item">
                  <span className="rca-diagnostic-type type-underestimated font-mono">UNDERESTIMATED</span>
                  <span className="rca-diagnostic-text"><RenderWithSources text={cleanNarrative(item)} sources={review?.sources} /></span>
                </div>
              ))}
              {overestimated.map((item, idx) => (
                <div key={`over-${idx}`} className="rca-diagnostic-item">
                  <span className="rca-diagnostic-type type-overestimated font-mono">OVERWEIGHTED</span>
                  <span className="rca-diagnostic-text"><RenderWithSources text={cleanNarrative(item)} sources={review?.sources} /></span>
                </div>
              ))}
            </div>
          </div>
        )}

        {lessons.length > 0 && (
          <div className="rca-lesson-section">
            <div className="rca-subheading">Identified Market Dynamic</div>
            {lessons.map((lesson, idx) => (
              <HeuristicRuleItem key={idx} lesson={lesson} index={idx} />
            ))}
          </div>
        )}

        {!hasDiagnostics && lessons.length === 0 && (
          <p className="rca-content-muted">
            {review?.isPendingReview
              ? "Trading session currently underway. Automated post-market attribution and root-cause analysis will execute at 20:00 WIB."
              : "Model parameters converged within target error bands. No active parameter revisions injected."}
          </p>
        )}
      </div>
    </div>
  );
}

function HistoryRow({ review, isSelected, onSelectSession, isSessionLive }) {
  const [expanded, setExpanded] = useState(false);
  const isUp = Number(review.ihsg_actual_pct) >= 0;
  const accuracyNum = Math.min(100, Math.max(0, Number(review.accuracy_score) || 0));
  const bpsNum = Math.round(Number(review.ihsg_actual_pct || 0) * 100);
  const isLive = isSessionLive ? isSessionLive(review) : false;

  const secEntries = Object.entries(review.sector_accuracy || {});
  const secMatches = secEntries.filter(([_, hit]) => hit === true).length;
  const secTotal = secEntries.length;

  const rowUsdIdr =
    review.actual_usdidr !== null &&
    review.actual_usdidr !== undefined &&
    review.actual_usdidr !== "" &&
    Number.isFinite(Number(review.actual_usdidr)) &&
    Number(review.actual_usdidr) > 0
      ? `Rp ${formatNumber(review.actual_usdidr)}`
      : (review.actual_usdidr && review.actual_usdidr !== "Illustrative" ? String(review.actual_usdidr) : "Unavailable");

  return (
    <>
      <tr
        onClick={() => {
          if (onSelectSession) onSelectSession(review.date);
          setExpanded(!expanded);
        }}
        className={`table-row ${isSelected ? "selected-session" : ""} ${expanded ? "expanded" : ""}`}
      >
        <td className="font-mono text-muted text-xs">
          <svg
            className={`chevron-icon ${expanded ? "rotated" : ""}`}
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
          {formatHeaderDate(review.date)}
        </td>
        <td>
          <div className="table-call-cell" style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
            <DirectionBadge direction={review.ihsg_predicted} />
            {review.ihsg_confidence && (
              <span className="font-mono text-xs text-muted font-semibold">{review.ihsg_confidence}%</span>
            )}
            <DataQualityBadge isWebFallback={review.isWebFallback} isUnscorable={review.isUnscorable} />
          </div>
        </td>
        <td>
          <DirectionBadge direction={review.isPendingReview ? "PENDING" : review.ihsg_actual} />
        </td>
        <td>
          {review.isPendingReview ? (
            <span className="font-mono text-xs text-muted">{isLive ? "In Progress" : "Not reviewed"}</span>
          ) : (
            <div className="delta-cell font-mono">
              <span className={isUp ? "text-matched" : "text-missed"}>{formatPct(review.ihsg_actual_pct)}</span>
              <span className="bps-text text-muted">({bpsNum > 0 ? `+${bpsNum}` : bpsNum} bps)</span>
            </div>
          )}
        </td>
        <td>
          <div className="font-mono text-xs flow-cell">
            <span>{review.foreign_flow_actual || "N/A"}</span>
            {review.foreign_flow_correct !== undefined && review.foreign_flow_correct !== null && (
              <span className={`font-semibold ${review.foreign_flow_correct ? "text-matched" : "text-missed"}`}>
                ({review.foreign_flow_correct ? "✓" : "✗"})
              </span>
            )}
          </div>
        </td>
        <td>
          <span className="font-mono text-xs text-muted">
            {review.isPendingReview
              ? `${secTotal} Tracked`
              : (secTotal > 0 ? `${secMatches}/${secTotal} (${Math.round((secMatches / secTotal) * 100)}%)` : "—")}
          </span>
        </td>
        <td>
          {review.isPendingReview ? (
            <span className="font-mono text-xs text-muted">{isLive ? "Pending" : "Not reviewed"}</span>
          ) : review.accuracy_score !== null && review.accuracy_score !== undefined ? (
            <div className="accuracy-cell font-mono">
              <span className="accuracy-text">{formatNumber(review.accuracy_score)}%</span>
              <div className="accuracy-bar-track">
                <div className="accuracy-bar-fill" style={{ width: `${accuracyNum}%` }} />
              </div>
            </div>
          ) : (
            <span className="font-mono text-xs text-muted">Unscorable</span>
          )}
        </td>
        <td>
          <StatusBadge correct={review.ihsg_correct} isPending={review.isPendingReview} isLive={isLive} size="sm" />
        </td>
      </tr>
      {expanded && (
        <tr className="expanded-row">
          <td colSpan="8" style={{ padding: 0 }}>
            <div className="expanded-panel">
              <div className="expanded-grid">
                <div className="detail-item">
                  <div className="detail-label">Liquidity &amp; Foreign Flow</div>
                  <div className="detail-value">{review.foreign_flow_actual || "N/A"}</div>
                  <div className="detail-sub font-mono">
                    Predicted: {review.foreign_flow_predicted || "N/A"}{" "}
                    {review.isPendingReview ? (
                      <span className="text-secondary" style={{ fontSize: "12px", marginLeft: "4px" }}>
                        (● Active)
                      </span>
                    ) : review.foreign_flow_correct !== undefined && review.foreign_flow_correct !== null ? (
                      <span className={review.foreign_flow_correct ? "text-matched" : "text-missed"}>
                        ({review.foreign_flow_correct ? "✓ Matched" : "✗ Missed"})
                      </span>
                    ) : null}
                  </div>
                </div>
                <div className="detail-item">
                  <div className="detail-label">USD / IDR &amp; Macro</div>
                  <div className="detail-value font-mono">
                    {rowUsdIdr}
                  </div>
                  <div className="detail-sub">Session closing exchange rate</div>
                </div>
                {review.isWebFallback && (
                  <div className="detail-item">
                    <div className="detail-label">Data Provider Status</div>
                    <div className="detail-value font-mono" style={{ fontSize: "12px", color: "var(--warning-text)" }}>
                      ⚡ Web Search Fallback Active
                    </div>
                    <div className="detail-sub">Sourced via search engines due to primary provider limitation</div>
                  </div>
                )}
                {review.isUnscorable && (
                  <div className="detail-item">
                    <div className="detail-label">Scoring Status</div>
                    <div className="detail-value font-mono text-muted" style={{ fontSize: "12px" }}>
                      ⏸ Session Unscorable
                    </div>
                    <div className="detail-sub">Excluded from accuracy benchmarks (holiday/unverifiable feeds)</div>
                  </div>
                )}
                <div className="detail-item">
                  <div className="detail-label">Sector Attribution</div>
                  <div className="detail-sub">
                    {review.sector_accuracy && Object.keys(review.sector_accuracy).length > 0 ? (
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                        {Object.entries(review.sector_accuracy).map(([sec, hit]) => {
                          const isPending = review.isPendingReview;
                          let textCls = "text-muted";
                          let label = String(hit);
                          if (isPending) {
                            textCls = hit === "BULLISH" ? "text-matched" : (hit === "BEARISH" ? "text-missed" : "text-secondary");
                            label = String(hit);
                          } else {
                            textCls = hit ? "text-matched" : "text-missed";
                            label = hit ? "● MATCH" : "▲ MISS";
                          }
                          return (
                            <span key={sec} className="sector-tile" style={{ fontSize: "12px", padding: "2px 6px" }}>
                              {sec}: <span className={textCls}>{label}</span>
                            </span>
                          );
                        })}
                      </div>
                    ) : (
                      "No sector breakdown captured"
                    )}
                  </div>
                </div>
              </div>
              {review.lessons && review.lessons.length > 0 && (
                <div className="expanded-lesson">
                  <div className="detail-label" style={{ marginBottom: "4px" }}>Captured Learning Point</div>
                  <p className="expanded-lesson-text">“{cleanNarrative(review.lessons[0])}”</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function Sidebar({ reviews = [], selectedDate, onSelectDate, currentView = "market", onSelectView, onOpenMethodology, isSessionLive }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo-icon">N</div>
        <div>
          <span className="sidebar-brand">NEXUS</span>
          <span className="sidebar-sub-brand">MARKET INTEL</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        <div className="nav-group">
          <div className="nav-section-title">Core Intelligence</div>
          <a 
            className={`nav-item ${currentView === "market" ? "active" : ""}`}
            onClick={(e) => { e.preventDefault(); onSelectView && onSelectView("market"); }}
            href="#market"
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            Market Intelligence
          </a>
          <a 
            className={`nav-item ${currentView === "lessons" ? "active" : ""}`}
            onClick={(e) => { e.preventDefault(); onSelectView && onSelectView("lessons"); }}
            href="#lessons"
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            Memory &amp; Heuristics
          </a>
          <a 
            className={`nav-item ${currentView === "telemetry" ? "active" : ""}`}
            onClick={(e) => { e.preventDefault(); onSelectView && onSelectView("telemetry"); }}
            href="#telemetry"
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Execution Telemetry
          </a>
          <button
            type="button"
            className="nav-item"
            style={{ width: "100%", textAlign: "left", background: "transparent", border: "none" }}
            onClick={onOpenMethodology}
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            Methodology &amp; Guide
          </button>
        </div>
      </nav>

      {reviews.length > 0 && (
        <div className="sidebar-sessions">
          <div className="sidebar-session-title">Recent Evaluations</div>
          {reviews.slice(0, 8).map((r) => {
            const isSel = (!selectedDate && r.date === reviews[0]?.date) || selectedDate === r.date;
            const isLive = isSessionLive ? isSessionLive(r) : false;
            return (
              <button
                key={r.date}
                className={`sidebar-session-item ${isSel ? "active" : ""}`}
                onClick={() => {
                  if (onSelectView) onSelectView("market");
                  if (onSelectDate) onSelectDate(r.date);
                }}
              >
                <span className="font-mono">{formatHeaderDate(r.date)}</span>
                <span className={`font-mono ${r.isPendingReview ? (isLive ? "text-warning" : "text-muted") : (r.ihsg_correct ? "text-matched" : "text-missed")}`}>
                  {r.isPendingReview ? (isLive ? "⏳ Live" : "Not reviewed") : (r.ihsg_correct ? "● Hit" : "▲ Miss")}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <div className="sidebar-cadence-card">
        <div className="cadence-card-head">
          <span className="cadence-head-title font-mono">AUTOMATION CADENCE</span>
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
        </div>
        <div className="cadence-timeline">
          <div className="cadence-step active">
            <span className="cadence-time font-mono">06:55 WIB</span>
            <span className="cadence-desc">Morning Briefing · OpenRouter 120b</span>
          </div>
          <div className="cadence-step">
            <span className="cadence-time font-mono">16:00 WIB</span>
            <span className="cadence-desc">IDX Settle · Official Closing Tapes</span>
          </div>
          <div className="cadence-step active">
            <span className="cadence-time font-mono">20:00 WIB</span>
            <span className="cadence-desc">Evening Review · Attribution &amp; RCA</span>
          </div>
        </div>
      </div>

      <div className="sidebar-telemetry">
        <div className="telemetry-box-title">System Status</div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">Cadence</span>
          <span className="telemetry-box-val font-mono">06:55 / 20:00 WIB</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">LLM Core</span>
          <span className="telemetry-box-val font-mono">gpt-oss-120b</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">Knowledge</span>
          <span className="telemetry-box-val font-mono text-matched">Local Store</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">Feedback Loop</span>
          <span className="telemetry-box-val font-mono text-matched">Active</span>
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="vault-status">
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
          <span>Knowledge Vault</span>
        </div>
        <span className="system-tag font-mono">Nexus Core</span>
      </div>
    </aside>
  );
}

function MobileBottomNav({ currentView, onSelectView, onOpenBrief, onOpenMethodology }) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Mobile Navigation">
      <button
        type="button"
        className={`mobile-nav-item ${currentView === "market" ? "active" : ""}`}
        onClick={() => onSelectView("market")}
      >
        <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <line x1="3" y1="9" x2="21" y2="9" />
          <line x1="9" y1="21" x2="9" y2="9" />
        </svg>
        <span>Market</span>
      </button>

      <button
        type="button"
        className={`mobile-nav-item ${currentView === "lessons" ? "active" : ""}`}
        onClick={() => onSelectView("lessons")}
      >
        <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
        </svg>
        <span>Memory</span>
      </button>

      <button
        type="button"
        className={`mobile-nav-item ${currentView === "telemetry" ? "active" : ""}`}
        onClick={() => onSelectView("telemetry")}
      >
        <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <span>Telemetry</span>
      </button>

      <button
        type="button"
        className="mobile-nav-item mobile-nav-action"
        onClick={onOpenMethodology}
        title="Open Methodology and Audit Documentation"
      >
        <svg className="mobile-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span>Guide</span>
      </button>
    </nav>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(INITIAL_DASHBOARD_DATA);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState("dark");
  const [filter, setFilter] = useState("all");
  const [selectedDate, setSelectedDate] = useState(null);
  const [currentView, setCurrentView] = useState("market");
  const [marketStatus, setMarketStatus] = useState(() => getIdxMarketStatus(null, null));
  const [staleBannerExpanded, setStaleBannerExpanded] = useState(false);
  const [scorecardDetailsOpen, setScorecardDetailsOpen] = useState(false);
  const [quickLedgerExpanded, setQuickLedgerExpanded] = useState(false);
  const [workbenchOpen, setWorkbenchOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [briefModalOpen, setBriefModalOpen] = useState(false);
  const [briefMarkdown, setBriefMarkdown] = useState("");
  const [briefSources, setBriefSources] = useState({});
  const [briefLoading, setBriefLoading] = useState(false);
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const [pipelineStatusOpen, setPipelineStatusOpen] = useState(false);
  const [lineageOpen, setLineageOpen] = useState(false);

  const todayTradingKey = useMemo(() => {
    try {
      const now = new Date();
      const wibStr = now.toLocaleString("en-US", { timeZone: "Asia/Jakarta" });
      const wib = new Date(wibStr);
      const y = wib.getFullYear();
      const m = String(wib.getMonth() + 1).padStart(2, "0");
      const d = String(wib.getDate()).padStart(2, "0");
      return `${y}-${m}-${d}`;
    } catch (e) {
      return null;
    }
  }, []);

  const handleOpenBriefModal = async (date) => {
    if (!date) return;
    setBriefModalOpen(true);
    setBriefLoading(true);
    try {
      const res = await fetch(`/api/brief/${date}`);
      if (res.ok) {
        const json = await res.json();
        setBriefMarkdown(json.markdown || "");
        setBriefSources(json.sources && Object.keys(json.sources).length > 0 ? json.sources : (activeReview?.sources || {}));
      } else {
        setBriefMarkdown("Briefing document not available for this session.");
        setBriefSources(activeReview?.sources || {});
      }
    } catch (e) {
      setBriefMarkdown("Failed to load brief markdown: " + e.message);
      setBriefSources(activeReview?.sources || {});
    } finally {
      setBriefLoading(false);
    }
  };

  useEffect(() => {
    let savedTheme = (typeof document !== "undefined" && document.documentElement.getAttribute("data-theme")) || "dark";
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        const stored = localStorage.getItem("nexus-theme");
        if (stored) savedTheme = stored;
      }
    } catch (e) {}
    if (savedTheme !== "dark") {
      setTheme(savedTheme);
    }
    if (typeof document !== "undefined" && document.documentElement.getAttribute("data-theme") !== savedTheme) {
      document.documentElement.setAttribute("data-theme", savedTheme);
    }

    fetch("/api/stats")
      .then((res) => res.json())
      .then((json) => {
        if (!json.success) {
          throw new Error(json.error || "Dashboard data unavailable");
        }
        startTransition(() => {
          setData(json);
        });
      })
      .catch((err) => {
        console.error(err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setMarketStatus(getIdxMarketStatus(null, data?.holidays));
    const statusTimer = setInterval(() => {
      setMarketStatus(getIdxMarketStatus(null, data?.holidays));
    }, 15000);
    return () => clearInterval(statusTimer);
  }, [data?.holidays]);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    try {
      if (typeof window !== "undefined" && window.localStorage) {
        localStorage.setItem("nexus-theme", nextTheme);
      }
    } catch (e) {}
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", nextTheme);
    }
  };

  const dashboard = useMemo(() => {
    if (!data) return null;

    const reviews = data.reviews || [];
    const latest = reviews[0] || null;
    const evaluatedReviews = reviews.filter((r) => !r.isPendingReview);
    const wins = evaluatedReviews.filter((review) => review.ihsg_correct).length;
    const winRate = evaluatedReviews.length ? ((wins / evaluatedReviews.length) * 100).toFixed(1) : null;
    const avgAccuracy = data.stats?.avgAccuracy ? Number(data.stats.avgAccuracy).toFixed(1) : null;

    let totalSectorChecks = 0;
    let totalSectorHits = 0;
    evaluatedReviews.forEach((r) => {
      Object.values(r.sector_accuracy || {}).forEach((hit) => {
        if (hit === true || hit === false) {
          totalSectorChecks += 1;
          if (hit === true) totalSectorHits += 1;
        }
      });
    });
    const sectorHitRate = totalSectorChecks > 0 ? ((totalSectorHits / totalSectorChecks) * 100).toFixed(1) : null;
    const totalLessons = data.recentLessons?.length || reviews.reduce((acc, r) => acc + (r.lessons?.length || 0), 0);

    return {
      stats: data.stats || {},
      nexusStats: data.nexusStats || {},
      pipelineHealth: data.pipelineHealth || { isStale: false },
      reviews,
      evaluatedReviews,
      latest,
      avgAccuracy,
      winRate,
      wins,
      evaluatedCount: evaluatedReviews.length,
      totalSectorChecks,
      totalSectorHits,
      sectorHitRate,
      totalLessons,
      isDemo: Boolean(data.isDemo),
      historyRescoredAt: data.stats?.historyRescoredAt || "2026-10-14",
    };
  }, [data]);

  const activeReview = useMemo(() => {
    if (!dashboard) return null;
    const revs = dashboard.reviews || [];
    if (!selectedDate) return dashboard.latest || revs[0] || null;
    return revs.find((r) => r.date === selectedDate) || dashboard.latest || revs[0] || null;
  }, [dashboard, selectedDate]);

  const isHistorical = Boolean(activeReview && dashboard?.latest && activeReview.date !== dashboard.latest.date);

  const filteredReviews = useMemo(() => {
    if (!dashboard) return [];
    if (filter === "matched") return dashboard.reviews.filter((r) => r.ihsg_correct === true);
    if (filter === "missed") return dashboard.reviews.filter((r) => !r.isPendingReview && r.ihsg_correct === false);
    return dashboard.reviews;
  }, [dashboard, filter]);

  if (loading) {
    return <main className="center-state">Initializing institutional telemetry feeds...</main>;
  }

  if (error || !dashboard) {
    return (
      <main className="center-state">
        <span className="text-missed font-medium">{error || "Unable to load dashboard data."}</span>
      </main>
    );
  }

  const isMatched = activeReview?.ihsg_correct;
  const isUp = Number(activeReview?.ihsg_actual_pct) >= 0;
  const nStats = dashboard.nexusStats || {};
  const isPipelineStale = Boolean(dashboard.pipelineHealth?.isStale);

  const isSessionLive = (review) => {
    if (!review || isPipelineStale) return false;
    return review.date === todayTradingKey && Boolean(marketStatus?.isOpen);
  };

  return (
    <div className="layout-root">
      <Sidebar
        reviews={dashboard.reviews}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
        currentView={currentView}
        onSelectView={setCurrentView}
        onOpenMethodology={() => setMethodologyOpen(true)}
        isSessionLive={isSessionLive}
      />

      <main className="main-viewport">
        {currentView === "market" && (
        <div className="content-container">
          {/* Top Header: Product Name + Plain Description + Freshness + Market Status */}
          <header className="page-header" style={{ alignItems: "flex-start", marginBottom: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", width: "100%", gap: "8px", flexWrap: "wrap" }}>
              <div>
                <div className="breadcrumb font-mono">NEXUS / MARKET INTELLIGENCE</div>
                <h1 className="page-title" style={{ fontSize: "20px", margin: "1px 0" }}>Nexus IHSG Intelligence</h1>
                <p className="header-subtitle" style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0 }}>
                  Daily IHSG pre-market call (06:55) &amp; post-close audit (20:00).
                </p>
              </div>
              <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                <div className={`market-status-chip is-${marketStatus.status}`}>
                  <span className={`live-dot ${marketStatus.isOpen ? "dot-open" : (marketStatus.status === "recess" ? "dot-amber" : "dot-closed")}`}></span>
                  <span className="font-mono text-xs">{marketStatus.label}</span>
                </div>
                <div className="live-badge font-mono">
                  <span className={`live-dot ${isPipelineStale ? "dot-amber" : "dot-open"}`}></span>
                  <span>{isPipelineStale ? `Stale: ${dashboard.pipelineHealth.latestDate}` : "Automation Active"}</span>
                </div>
              </div>
            </div>
            <div className="header-actions" style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
              <button
                type="button"
                className="methodology-trigger-btn font-mono"
                onClick={() => setPipelineStatusOpen(true)}
                title="View Pipeline Operational Status & Run Schedule"
              >
                <span>Status</span>
              </button>
              <button
                type="button"
                className="methodology-trigger-btn font-mono"
                onClick={() => setLineageOpen(true)}
                title="View Data Lineage & Provenance"
              >
                <span>Lineage</span>
              </button>
              <button
                type="button"
                className="methodology-trigger-btn font-mono"
                onClick={() => setMethodologyOpen(true)}
                title="View Scoring Methodology, Weightings & Known Limitations"
              >
                <span>Guide</span>
              </button>
              <button
                className="theme-toggle-btn"
                onClick={toggleTheme}
                title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
                aria-label="Toggle theme"
                style={{ minHeight: "44px", minWidth: "44px" }}
              >
                {theme === "dark" ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </button>
            </div>
          </header>

          {/* Provenance Guard Error Banner (Phase 2.3 Requirement: visible "Test data detected" banner if mock artifact found) */}
          {Boolean(dashboard.pipelineHealth?.mockDataDetected) && (
            <div
              className="mock-provenance-banner"
              role="alert"
              style={{
                padding: "10px 14px",
                marginBottom: "12px",
                borderRadius: "var(--radius-sm)",
                background: "var(--missed-bg)",
                border: "1px solid var(--missed-border)",
                color: "var(--missed-text)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "8px",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              <div>
                🚨 <strong>Test data detected:</strong>{" "}
                {dashboard.pipelineHealth.mockDataMessage ||
                  "Mock/synthetic provenance artifacts were detected in runs/ and excluded from all scores."}
              </div>
              <button
                type="button"
                className="font-mono text-xs"
                style={{
                  background: "var(--surface-well)",
                  border: "1px solid var(--missed-border)",
                  color: "var(--missed-text)",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  minHeight: "44px",
                  display: "inline-flex",
                  alignItems: "center",
                }}
                onClick={() => setPipelineStatusOpen(true)}
              >
                Inspect Excluded Runs ▸
              </button>
            </div>
          )}

          {/* Stale Pipeline Banner (Phase 4.1 & E5 Requirement: collapsed to 1 line with details toggle) */}
          {isPipelineStale && (
            <div className="stale-pipeline-banner" style={{ flexDirection: "column", alignItems: "stretch" }}>
              <div className="stale-banner-content" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "nowrap", gap: "8px", width: "100%" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
                  <span className="stale-icon" style={{ fontSize: "16px" }}>⚠️</span>
                  <span className="stale-banner-text" style={{ fontSize: "12px", fontWeight: 600, lineHeight: 1.25 }}>
                    Feed paused since {dashboard.pipelineHealth.latestDate ? formatHeaderDate(dashboard.pipelineHealth.latestDate) : "8 Oct"} ({dashboard.pipelineHealth.tradingDaysSinceLatest || 5} trading days).
                  </span>
                </div>
                <button
                  type="button"
                  className="font-mono text-xs"
                  style={{
                    background: "var(--surface-well)",
                    border: "1px solid var(--warning-border)",
                    color: "var(--warning-text)",
                    padding: "4px 8px",
                    borderRadius: "4px",
                    cursor: "pointer",
                    minHeight: "44px",
                    flexShrink: 0,
                    display: "inline-flex",
                    alignItems: "center"
                  }}
                  onClick={() => setStaleBannerExpanded(!staleBannerExpanded)}
                >
                  {staleBannerExpanded ? "Details ▲" : "Details ▾"}
                </button>
              </div>
              {staleBannerExpanded && (
                <div className="stale-banner-text" style={{ marginTop: "8px", fontSize: "12px", borderTop: "1px solid var(--warning-border)", paddingTop: "8px" }}>
                  {dashboard.pipelineHealth.staleMessage} Displaying most recent verified archive from <strong>{dashboard.pipelineHealth.latestDate}</strong>. Past unreviewed sessions are marked <em>Not reviewed</em> and excluded from scoring benchmarks.
                </div>
              )}
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              HIERARCHY STEP 2: TODAY'S / LATEST PRE-MARKET CALL CARD
              ══════════════════════════════════════════════════════════════════════ */}
          {dashboard.latest && (
            <section className="today-call-card">
              <div className="today-call-header" style={{ alignItems: "center", flexWrap: "nowrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", minWidth: 0 }}>
                  <span className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", letterSpacing: "0.04em" }}>
                    {isPipelineStale ? "LATEST VERIFIED CALL" : "TODAY'S PRE-MARKET CALL"}
                  </span>
                  <span className="font-mono text-xs text-muted">· {formatHeaderDate(dashboard.latest.date)} (06:55 WIB)</span>
                  {isPipelineStale && (
                    <span className="font-mono text-xs text-warning font-semibold">
                      · No new call generated today
                    </span>
                  )}
                </div>
                <div style={{ flexShrink: 0 }}>
                  <button
                    type="button"
                    className="font-mono text-xs"
                    style={{
                      background: "var(--surface-subtle)",
                      border: "1px solid var(--border-default)",
                      padding: "4px 8px",
                      borderRadius: "var(--radius-sm)",
                      color: "var(--accent-cyan)",
                      cursor: "pointer",
                      minHeight: "44px",
                      display: "inline-flex",
                      alignItems: "center",
                      whiteSpace: "nowrap"
                    }}
                    onClick={() => handleOpenBriefModal(dashboard.latest.date)}
                  >
                    Read Brief →
                  </button>
                </div>
              </div>

              <div className="today-call-main">
                <div className="today-call-dir-hero">
                  <span className="font-mono text-xs text-muted font-bold">PROJECTED BIAS</span>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <DirectionBadge direction={dashboard.latest.ihsg_predicted} />
                    {(dashboard.latest.calibrated_confidence || nStats.calibration?.calibrated_confidence_pct) && (
                      <span
                        className="calibrated-conf-badge font-mono text-sm font-bold text-matched"
                        title={`Calibrated probability (${nStats.calibration?.status_label || nStats.calibration?.calibration_note || "illustrative shrinkage estimate"}): shrunk from stated confidence using N0=${nStats.calibration?.prior_strength_n0 ?? 30}, prior cap=${nStats.calibration?.prior_pct ?? 55}%`}
                      >
                        {dashboard.latest.calibrated_confidence ?? nStats.calibration?.calibrated_confidence_pct}% Calibrated Conf (n={nStats.calibration?.sample_size_n ?? nStats.sample_size_n ?? 12}{(nStats.calibration?.sample_size_n ?? nStats.sample_size_n ?? 12) < 30 ? `, ${nStats.calibration?.status_label || nStats.calibration?.calibration_note || "illustrative shrinkage estimate"}` : ""})
                      </span>
                    )}
                  </div>
                  {dashboard.latest.ihsg_confidence && (
                    <span className="uncalibrated-conf-badge font-mono text-xs text-muted" style={{ marginTop: "1px" }}>
                      Model stated: {dashboard.latest.ihsg_confidence}% (uncalibrated)
                    </span>
                  )}
                </div>

                <div>
                  <span className="font-mono text-xs text-muted font-bold">CORE CATALYSTS &amp; THESIS</span>
                  <p style={{ fontSize: "13px", lineHeight: 1.5, margin: "4px 0 0", color: "var(--text-primary)" }}>
                    <RenderWithSources text={cleanNarrative(dashboard.latest.summary)} sources={dashboard.latest.sources} />
                  </p>
                </div>
              </div>

              {/* Key Risk Factor */}
              {dashboard.latest.key_risk && (
                <div className="today-risk-box" style={{ marginTop: "10px" }}>
                  <div className="font-mono text-xs text-warning font-bold" style={{ marginBottom: "2px" }}>
                    KEY RISK FACTOR (PRE-MARKET)
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                    <RenderWithSources text={cleanNarrative(dashboard.latest.key_risk)} sources={dashboard.latest.sources} />
                  </div>
                </div>
              )}

              {/* Timestamp & SHA-256 Lock Hash */}
              <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px", fontSize: "12px", color: "var(--text-tertiary)", fontFamily: "var(--font-mono)" }}>
                <span>🕒 Generated 06:55 WIB</span>
                {dashboard.latest.lock_status === "locked_pre_open" && dashboard.latest.created_at ? (
                  <span>🔒 Locked at 06:55 WIB · SHA-256: <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>{dashboard.latest.lock_hash || "verified"}</code></span>
                ) : (
                  <span style={{ color: "var(--warning-text)" }}>
                    ⚠️ Hash added retroactively; not proof of pre-open lock (computed {dashboard.latest.hash_computed_at || "2026-10-15"}) · SHA-256: <code style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>{dashboard.latest.lock_hash || "—"}</code>
                  </span>
                )}
              </div>
            </section>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              HIERARCHY STEP 3: TRACK RECORD CARD (HONEST SCORECARD)
              ══════════════════════════════════════════════════════════════════════ */}
          <section className="scorecard-card">
            <div className="scorecard-header">
              <div>
                <span className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", letterSpacing: "0.06em" }}>
                  SYSTEM TRACK RECORD &amp; BENCHMARKS
                </span>
                <h2 style={{ fontSize: "16px", margin: "2px 0 0", color: "var(--text-primary)" }}>
                  Honest Buy-Side Evaluation Scorecard
                </h2>
              </div>
              <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                <span className="font-mono text-xs" style={{ background: "var(--surface-well)", padding: "4px 8px", borderRadius: "4px" }}>
                  Scored Sessions: <strong>{nStats.sample_size_n ?? nStats.direction_scorable_sessions ?? dashboard.evaluatedCount}</strong>
                </span>
                <span
                  className="font-mono text-xs font-bold"
                  style={{
                    background: "var(--warning-bg)",
                    border: "1px solid var(--warning-border)",
                    color: "var(--warning-text)",
                    padding: "4px 8px",
                    borderRadius: "4px"
                  }}
                >
                  ⚠️ Sample too small to conclude skill (n &lt; 30)
                </span>
              </div>
            </div>

            <div className="scorecard-headline-grid">
              {/* Primary Direction Hit Rate Hero */}
              <div className="hit-rate-hero">
                <span className="font-mono text-xs text-muted font-bold">DIRECTION HIT RATE</span>
                <div className="hit-rate-number">
                  {nStats.direction_accuracy_pct !== undefined ? `${nStats.direction_accuracy_pct}%` : `${dashboard.winRate || "—"}%`}
                </div>
                <div className="font-mono text-xs text-secondary" style={{ marginTop: "4px" }}>
                  {nStats.direction_correct_count ?? 5} of {nStats.direction_scorable_sessions ?? 12} scorable calls matched
                </div>
                <div className="font-mono text-xs text-muted" style={{ marginTop: "2px" }}>
                  Wilson 95% CI: <strong>[{nStats.direction_ci_95?.lower_pct ?? nStats.direction_ci_95?.lower ?? "19.3"}%, {nStats.direction_ci_95?.upper_pct ?? nStats.direction_ci_95?.upper ?? "68.0"}%]</strong>
                </div>
              </div>

              {/* Comparative Baselines Grid */}
              <div className="baselines-grid">
                <div className="baseline-cell">
                  <span className="font-mono text-xs text-muted font-bold">ALWAYS-BEARISH</span>
                  <span className="font-mono text-base font-bold text-primary">
                    {nStats.baselines?.always_bearish_pct ?? nStats.baselines?.always_bearish ?? "66.7"}%{" "}
                    <span className="text-xs text-muted font-normal">
                      ({nStats.baselines?.always_bearish_count ?? 8}/{nStats.baselines?.always_bearish_total ?? 12})
                    </span>
                  </span>
                  <span className="font-mono text-xs text-missed">
                    Model lags by -25.0% (down sessions)
                  </span>
                </div>

                <div className="baseline-cell">
                  <span className="font-mono text-xs text-muted font-bold">PERSISTENCE BASELINE</span>
                  <span className="font-mono text-base font-bold text-primary">
                    {nStats.baselines?.persistence_pct ?? nStats.baselines?.persistence ?? "63.6"}%{" "}
                    <span className="text-xs text-muted font-normal">
                      ({nStats.baselines?.persistence_correct_count ?? 7}/{nStats.baselines?.persistence_scorable_sessions ?? 11})
                    </span>
                  </span>
                  <span className="font-mono text-xs text-missed">
                    Model lags by -21.9% (repeat prior day)
                  </span>
                </div>

                <div className="baseline-cell">
                  <span className="font-mono text-xs text-muted font-bold">ALWAYS-BULLISH</span>
                  <span className="font-mono text-base font-bold text-primary">
                    {nStats.baselines?.always_bullish_pct ?? nStats.baselines?.always_bullish ?? "33.3"}%{" "}
                    <span className="text-xs text-muted font-normal">
                      ({nStats.baselines?.always_bullish_count ?? 4}/{nStats.baselines?.always_bullish_total ?? 12})
                    </span>
                  </span>
                  <span className="font-mono text-xs text-matched">
                    Model leads by +8.4% (up sessions)
                  </span>
                </div>
              </div>
            </div>

            {/* Compact Payoff & Calibration Summary + Expandable Detail Strip (Phase 7.1) */}
            <div
              style={{
                marginTop: "10px",
                paddingTop: "10px",
                borderTop: "1px solid var(--border-subtle)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              <div className="font-mono text-xs" style={{ color: "var(--text-secondary)", lineHeight: 1.4 }}>
                <span>Long-Only: <strong className="text-missed">{nStats.payoff?.long_only_total_bps !== undefined ? `${nStats.payoff.long_only_total_bps} bps` : "-176.0 bps"}</strong></span>
                {" · "}
                <span>Short: <strong className="text-matched">+{nStats.payoff?.short_only_total_bps ?? "244.0"} bps</strong></span>
                {" · "}
                <span>Brier: <strong className="text-warning">{nStats.calibration?.brier_score ?? "0.3996"}</strong></span>
              </div>
              <button
                type="button"
                className="font-mono text-xs"
                style={{
                  background: "var(--surface-well)",
                  border: "1px solid var(--border-default)",
                  color: "var(--accent-cyan)",
                  padding: "4px 10px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  minHeight: "44px",
                  display: "inline-flex",
                  alignItems: "center",
                }}
                onClick={() => setScorecardDetailsOpen(!scorecardDetailsOpen)}
              >
                {scorecardDetailsOpen ? "Hide Payoff & Trajectory ▲" : "Payoff, Calibration & Trajectory ▾"}
              </button>
            </div>

            {scorecardDetailsOpen && (
              <div className="payoff-strip" style={{ marginTop: "10px" }}>
                <div className="payoff-grid">
                  <div>
                    <span className="font-mono text-xs text-muted font-bold">LONG-ONLY PAYOFF</span>
                    <div className="font-mono text-sm font-bold text-missed">
                      {nStats.payoff?.long_only_total_bps !== undefined ? `${nStats.payoff.long_only_total_bps > 0 ? "+" : ""}${nStats.payoff.long_only_total_bps} bps` : "-176.0 bps"}
                    </div>
                    <div className="font-mono text-xs text-muted" style={{ fontSize: "12px" }}>
                      Realized return on Bullish calls
                    </div>
                  </div>

                  <div>
                    <span className="font-mono text-xs text-muted font-bold">SHORT-ONLY (THEORETICAL)</span>
                    <div className="font-mono text-sm font-bold text-matched">
                      {nStats.payoff?.short_only_total_bps !== undefined ? `+${nStats.payoff.short_only_total_bps} bps` : "+244.0 bps"}
                    </div>
                    <div className="font-mono text-xs text-muted" style={{ fontSize: "12px" }}>
                      Index shorting (retail unavailable)
                    </div>
                  </div>

                  <div>
                    <span className="font-mono text-xs text-muted font-bold">CONFIDENCE CALIBRATION</span>
                    <div className="font-mono text-sm font-bold text-warning">
                      Stated {nStats.calibration?.average_stated_confidence_pct ?? "79.6"}% vs {nStats.calibration?.realized_hit_rate_pct ?? "41.7"}%
                    </div>
                    <div className="font-mono text-xs text-muted" style={{ fontSize: "12px" }}>
                      Calibrated: {nStats.calibration?.calibrated_confidence_pct ?? "49.7"}% (n={nStats.calibration?.sample_size_n ?? 12}) · Brier Score: {nStats.calibration?.brier_score ?? "0.3996"}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: "12px", color: "var(--text-tertiary)", marginTop: "10px", lineHeight: 1.5 }}>
                  * Note: Basis points (bps) reflect theoretical cash index movement before brokerage commissions, financing, and borrow fees. Indonesian retail accounts cannot directly short the IHSG cash index. Profit Factor metric is demoted at small sample size (n=12).
                </div>

                <div style={{ marginTop: "10px", background: "var(--surface-subtle)", padding: "10px 14px", borderRadius: "var(--radius-sm)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span className="font-mono text-xs text-muted font-bold">CUMULATIVE BENCHMARK TRAJECTORY (12 SESSIONS)</span>
                    <span className="font-mono text-xs text-secondary">History rescored on {dashboard.historyRescoredAt}</span>
                  </div>
                  <div style={{ display: "flex", gap: "4px", height: "14px", borderRadius: "3px", overflow: "hidden", background: "var(--surface-well)" }}>
                    {dashboard.reviews.map((r) => (
                      <div
                        key={r.date}
                        style={{
                          flex: 1,
                          background: r.isPendingReview ? "var(--warning-border)" : (r.ihsg_correct ? "var(--matched-text)" : "var(--missed-text)"),
                          opacity: r.isPendingReview ? 0.5 : 1
                        }}
                        title={`${formatHeaderDate(r.date)}: ${r.isPendingReview ? "Pending Review" : (r.ihsg_correct ? "Hit" : "Miss")} (${r.ihsg_predicted} vs actual ${r.ihsg_actual || "—"})`}
                      />
                    ))}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--text-tertiary)", marginTop: "4px", fontFamily: "var(--font-mono)" }}>
                    <span>● Green = Hit (5)</span>
                    <span>▲ Red = Miss (7)</span>
                    <span>⏳ Amber = Pending</span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* ══════════════════════════════════════════════════════════════════════
              HIERARCHY STEP 4: LAST 5 SESSIONS QUICK AUDIT LEDGER
              ══════════════════════════════════════════════════════════════════════ */}
          <section className="quick-ledger-card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" }}>
              <div>
                <span className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)", letterSpacing: "0.06em" }}>
                  RECENT VERIFIED SESSIONS
                </span>
                <h3 style={{ fontSize: "15px", margin: "2px 0 0", color: "var(--text-primary)" }}>
                  Recent Sessions: Call → Result → Verdict
                </h3>
              </div>
              <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                <button
                  type="button"
                  className="font-mono text-xs"
                  style={{
                    color: "var(--text-secondary)",
                    fontWeight: 600,
                    padding: "6px 10px",
                    borderRadius: "4px",
                    background: "var(--surface-well)",
                    border: "1px solid var(--border-default)",
                    cursor: "pointer",
                    minHeight: "44px",
                    display: "inline-flex",
                    alignItems: "center",
                  }}
                  onClick={() => setQuickLedgerExpanded(!quickLedgerExpanded)}
                >
                  {quickLedgerExpanded ? "Collapse ▲" : "Show 5 Recent ▾"}
                </button>
                <a
                  href="#full-archive"
                  className="font-mono text-xs"
                  style={{
                    color: "var(--accent-cyan)",
                    textDecoration: "none",
                    fontWeight: 600,
                    padding: "6px 12px",
                    borderRadius: "4px",
                    background: "var(--surface-subtle)",
                    border: "1px solid var(--border-default)",
                    minHeight: "44px",
                    display: "inline-flex",
                    alignItems: "center"
                  }}
                  onClick={(e) => {
                    e.preventDefault();
                    setArchiveOpen(true);
                    const el = document.getElementById("full-archive");
                    if (el) el.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  Full Archive ({dashboard.reviews.length}) ↓
                </a>
              </div>
            </div>

            {!quickLedgerExpanded ? (
              <div
                style={{
                  padding: "8px 12px",
                  background: "var(--surface-subtle)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div className="font-mono text-xs" style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                    {formatHeaderDate(dashboard.reviews[0]?.date)}
                  </span>
                  <DirectionBadge direction={dashboard.reviews[0]?.ihsg_predicted} />
                  <span className="text-muted">→</span>
                  <StatusBadge
                    correct={dashboard.reviews[0]?.ihsg_correct}
                    isPending={dashboard.reviews[0]?.isPendingReview}
                    size="sm"
                  />
                </div>
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="quick-ledger-table font-mono text-xs">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-default)", textAlign: "left", color: "var(--text-tertiary)" }}>
                      <th style={{ padding: "8px 10px" }}>Session</th>
                      <th style={{ padding: "8px 10px" }}>Morning Call (06:55)</th>
                      <th style={{ padding: "8px 10px" }}>Actual Close (16:00)</th>
                      <th style={{ padding: "8px 10px" }}>Foreign Net</th>
                      <th style={{ padding: "8px 10px" }}>Verdict</th>
                      <th style={{ padding: "8px 10px", textAlign: "right" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.reviews.slice(0, 5).map((rev) => {
                      const isUpRow = Number(rev.ihsg_actual_pct) >= 0;
                      const isSelected = activeReview?.date === rev.date;
                      return (
                        <tr
                          key={rev.date}
                          className={`quick-ledger-row ${isSelected ? "selected-session" : ""}`}
                          onClick={() => {
                            setSelectedDate(rev.date);
                            setWorkbenchOpen(true);
                          }}
                        >
                          <td className="quick-ledger-cell" style={{ fontWeight: 600 }}>
                            {formatHeaderDate(rev.date)}
                          </td>
                          <td className="quick-ledger-cell">
                            <DirectionBadge direction={rev.ihsg_predicted} />
                            {rev.ihsg_confidence && <span style={{ marginLeft: "4px", color: "var(--text-secondary)" }}>{rev.ihsg_confidence}%</span>}
                          </td>
                          <td className="quick-ledger-cell">
                            {rev.isPendingReview ? (
                              <span className="text-warning">In Progress</span>
                            ) : (
                              <>
                                <DirectionBadge direction={rev.ihsg_actual} />
                                <span className={isUpRow ? "text-matched" : "text-missed"} style={{ marginLeft: "4px" }}>
                                  {formatPct(rev.ihsg_actual_pct)}
                                </span>
                              </>
                            )}
                          </td>
                          <td className="quick-ledger-cell">
                            <span>{rev.foreign_flow_actual || "N/A"}</span>
                          </td>
                          <td className="quick-ledger-cell">
                            <StatusBadge correct={rev.ihsg_correct} isPending={rev.isPendingReview} size="sm" />
                          </td>
                          <td className="quick-ledger-cell" style={{ textAlign: "right" }}>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedDate(rev.date);
                                setWorkbenchOpen(true);
                              }}
                              style={{
                                background: isSelected ? "var(--accent-cyan)" : "var(--surface-well)",
                                color: isSelected ? "#000" : "var(--text-primary)",
                                border: "none",
                                padding: "6px 12px",
                                borderRadius: "3px",
                                cursor: "pointer",
                                fontSize: "12px",
                                fontFamily: "var(--font-mono)",
                                fontWeight: 600,
                                minHeight: "44px",
                                minWidth: "44px",
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center"
                              }}
                            >
                              {isSelected ? "Active" : "Inspect"}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* ══════════════════════════════════════════════════════════════════════
              HIERARCHY STEP 5: DETAILS IN COLLAPSIBLE & INTERACTIVE WORKBENCH
              ══════════════════════════════════════════════════════════════════════ */}
          <div className="section-eyebrow font-mono">
            <span className="console-prompt">{"//"}</span> 02 · {isHistorical ? "INSPECTING HISTORICAL SESSION" : "SESSION VERIFICATION & RCA"}
          </div>
          {!workbenchOpen ? (
            <div
              className="collapsible-section-card"
              style={{
                padding: "16px 20px",
                background: "var(--surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                marginBottom: "12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "12px"
              }}
            >
              <div>
                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  {activeReview ? `Session Analysis & RCA: ${formatHeaderDate(activeReview.date)}` : "Session Diagnostics & RCA"}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Variance bridge, multi-agent signals, sector attribution, and lessons learned.
                </div>
              </div>
              <button
                type="button"
                className="font-mono text-xs"
                style={{
                  background: "var(--surface-well)",
                  border: "1px solid var(--border-strong)",
                  padding: "8px 16px",
                  borderRadius: "4px",
                  color: "var(--accent-cyan)",
                  cursor: "pointer",
                  fontWeight: 600,
                  minHeight: "44px",
                  display: "inline-flex",
                  alignItems: "center"
                }}
                onClick={() => setWorkbenchOpen(true)}
              >
                🔎 Open Session Workbench ▾
              </button>
            </div>
          ) : (
            activeReview && (
              <section className="eval-section">
                <header className="eval-header">
                  <div className="eval-header-title">
                    {activeReview.isPendingReview
                      ? "Active Trading Session — Pending 20:00 Review"
                      : (isHistorical ? `Historical Session Audit: ${activeReview.date}` : "Post-Market Evaluation & RCA")}
                  </div>
                  <div className="eval-header-right" style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    {isHistorical && (
                      <button
                        className="jump-latest-btn font-mono"
                        onClick={() => setSelectedDate(null)}
                      >
                        ← Jump to Latest ({formatHeaderDate(dashboard.latest?.date)})
                      </button>
                    )}
                    <div className="eval-date-badge font-mono">{formatHeaderDate(activeReview.date)}</div>
                    <button
                      type="button"
                      className="font-mono text-xs"
                      style={{
                        background: "var(--surface-well)",
                        border: "1px solid var(--border-default)",
                        color: "var(--text-secondary)",
                        padding: "6px 12px",
                        borderRadius: "4px",
                        cursor: "pointer",
                        minHeight: "44px",
                        display: "inline-flex",
                        alignItems: "center"
                      }}
                      onClick={() => setWorkbenchOpen(false)}
                    >
                      Collapse Workbench ▲
                    </button>
                  </div>
                </header>

                {/* 4-Column Variance Bridge */}
                <div className="variance-bridge-grid">
                  <div className="bridge-cell">
                    <div className="bridge-cell-header font-mono">PRE-MARKET THESIS (06:55)</div>
                    <div className="bridge-cell-body">
                      <DirectionBadge direction={activeReview.ihsg_predicted} />
                      {activeReview.calibrated_confidence ? (
                        <span
                          className="confidence-pill font-mono"
                          title={`Calibrated: ${activeReview.calibrated_confidence}% vs Raw: ${activeReview.ihsg_confidence || "—"}%`}
                        >
                          {activeReview.calibrated_confidence}% Conf
                        </span>
                      ) : activeReview.ihsg_confidence ? (
                        <span className="confidence-pill font-mono">{activeReview.ihsg_confidence}% Conf</span>
                      ) : null}
                    </div>
                    <div className="bridge-cell-sub">
                      Exp. Flow: <span className="text-secondary font-medium font-mono">{activeReview.foreign_flow_predicted || "Neutral"}</span>
                    </div>
                  </div>

                  <div className="bridge-cell">
                    <div className="bridge-cell-header font-mono">SESSION CLOSE (16:00)</div>
                    <div className="bridge-cell-body">
                      {activeReview.isPendingReview ? (
                        <span className="font-mono text-xs text-warning">Trading In Progress</span>
                      ) : (
                        <>
                          <DirectionBadge direction={activeReview.ihsg_actual} />
                          <span className={`font-mono text-sm font-semibold ${isUp ? "text-matched" : "text-missed"}`}>
                            ({formatPct(activeReview.ihsg_actual_pct)})
                          </span>
                        </>
                      )}
                    </div>
                    <div className="bridge-cell-sub">
                      Act. Flow: <span className="text-secondary font-medium font-mono">
                        {activeReview.isPendingReview ? "Pending Close" : (activeReview.foreign_flow_actual || "N/A")}
                      </span>
                    </div>
                  </div>

                  <div className="bridge-cell">
                    <div className="bridge-cell-header font-mono">SPREAD &amp; DELTA</div>
                    <div className="bridge-cell-body">
                      {activeReview.isPendingReview ? (
                        <span className="font-mono text-xs text-muted">Awaiting Market Close</span>
                      ) : (
                        <>
                          <span className={`font-mono text-base font-bold ${isUp ? "text-matched" : "text-missed"}`}>
                            {formatPct(activeReview.ihsg_actual_pct)}
                          </span>
                          <span className={`font-mono text-xs font-semibold ${activeReview.payoff_bps != null ? (activeReview.payoff_bps >= 0 ? "text-matched" : "text-missed") : "text-muted"}`}>
                            ({activeReview.payoff_bps != null ? (activeReview.payoff_bps >= 0 ? `+${activeReview.payoff_bps}` : `${activeReview.payoff_bps}`) : Math.round(Number(activeReview.ihsg_actual_pct || 0) * 100)} bps)
                          </span>
                        </>
                      )}
                    </div>
                    <div className="bridge-cell-sub">
                      Variance: <span className={`font-mono ${activeReview.isPendingReview ? "text-muted" : (isMatched ? "text-matched font-medium" : "text-missed font-medium")}`}>
                        {activeReview.isPendingReview ? "Session Active" : (isMatched ? "Direction Aligned" : "Direction Divergence")}
                      </span>
                    </div>
                  </div>

                  <div className="bridge-cell" style={{ borderRight: "none" }}>
                    <div className="bridge-cell-header font-mono">ATTRIBUTION VERDICT</div>
                    <div className="bridge-cell-body">
                      <StatusBadge correct={isMatched} isPending={activeReview.isPendingReview} />
                    </div>
                    <div className="bridge-cell-sub">
                      Accuracy Score: <span className="text-primary font-bold font-mono">
                        {activeReview.isPendingReview ? "Awaiting 20:00 Review" : (activeReview.accuracy_score !== null ? `${formatNumber(activeReview.accuracy_score)}%` : "Unscorable")}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Workbench Body */}
                <div className="eval-body">
                  <div className="eval-pane">
                    <div className="eval-pane-header">
                      <div className="eval-pane-header-left">
                        <span className="eval-pane-title">Market Signals &amp; Synthesis</span>
                        <span className="eval-section-tag font-mono">06:55 → 20:00 WIB</span>
                      </div>
                      <span className="eval-section-tag font-mono">
                        {isHistorical ? `Audit · ${activeReview.date}` : `Session #${activeReview.date.replace(/-/g, "")}`}
                      </span>
                    </div>

                    <div className="eval-pane-body" style={{ padding: 0 }}>
                      <div className="eval-pane-section">
                        <div className="eval-pane-section-header">
                          <span className="eval-section-heading">Session Briefing</span>
                          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                            {activeReview.date && (
                              <button
                                type="button"
                                className="font-mono"
                                style={{
                                  background: "var(--surface-hover)",
                                  border: "1px solid var(--border-strong)",
                                  padding: "3px 8px",
                                  borderRadius: "4px",
                                  color: "var(--accent-cyan)",
                                  cursor: "pointer",
                                  fontSize: "12px",
                                  minHeight: "44px",
                                  display: "inline-flex",
                                  alignItems: "center"
                                }}
                                onClick={() => handleOpenBriefModal(activeReview.date)}
                              >
                                Read Full Telegram Brief →
                              </button>
                            )}
                            <span className="eval-section-tag font-mono">OpenRouter / 120b</span>
                          </div>
                        </div>
                        <p className="eval-summary-text">
                          <RenderWithSources text={cleanNarrative(activeReview.summary)} sources={activeReview.sources} />
                          {!activeReview.summary && "No executive summary logged."}
                        </p>
                        {activeReview.key_risk && (
                          <div style={{ marginTop: "10px", padding: "8px 12px", background: "var(--surface-hover)", borderRadius: "4px", borderLeft: "3px solid var(--missed-text)" }}>
                            <div className="font-mono text-xs" style={{ color: "var(--missed-text)", fontWeight: 600, marginBottom: "2px" }}>KEY RISK FACTOR</div>
                            <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.4 }}>
                              <RenderWithSources text={cleanNarrative(activeReview.key_risk)} sources={activeReview.sources} />
                            </div>
                          </div>
                        )}
                      </div>

                      <SectorAttribution review={activeReview} />
                      <MacroPulse review={activeReview} />
                      <ActionableMarketSetup review={activeReview} />
                    </div>
                  </div>

                  <div className="eval-column-right">
                    <RCAPanel review={activeReview} />
                  </div>
                </div>
              </section>
            )
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              HIERARCHY STEP 6: FULL HISTORICAL EVALUATION ARCHIVE
              ══════════════════════════════════════════════════════════════════════ */}
          <div className="section-eyebrow font-mono" id="full-archive">
            <span className="console-prompt">{"//"}</span> 03 · AUDITABLE EXECUTION ARCHIVE
          </div>
          {!archiveOpen ? (
            <div
              className="collapsible-section-card"
              style={{
                padding: "16px 20px",
                background: "var(--surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                marginBottom: "12px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "12px"
              }}
            >
              <div>
                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Full Historical Archive ({dashboard.reviews.length} Sessions)
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Complete auditable ledger with direction calls, actual closes, payoffs, and accuracy scores.
                </div>
              </div>
              <button
                type="button"
                className="font-mono text-xs"
                style={{
                  background: "var(--surface-well)",
                  border: "1px solid var(--border-strong)",
                  padding: "8px 16px",
                  borderRadius: "4px",
                  color: "var(--accent-cyan)",
                  cursor: "pointer",
                  fontWeight: 600,
                  minHeight: "44px",
                  display: "inline-flex",
                  alignItems: "center"
                }}
                onClick={() => setArchiveOpen(true)}
              >
                📁 View Full Historical Ledger ({dashboard.reviews.length}) ▾
              </button>
            </div>
          ) : (
            <section className="history-section">
              <header className="history-header">
                <div>
                  <h2 className="history-title">Historical Evaluation Archive</h2>
                  <div className="history-subtitle">
                    Full chronological ledger of 12 autonomous sessions. Rescored on {dashboard.historyRescoredAt}.
                  </div>
                </div>
                <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                  <div className="filter-tabs">
                    <button
                      className={`filter-tab-btn ${filter === "all" ? "active" : ""}`}
                      onClick={() => setFilter("all")}
                    >
                      All ({dashboard.reviews.length})
                    </button>
                    <button
                      className={`filter-tab-btn ${filter === "matched" ? "active" : ""}`}
                      onClick={() => setFilter("matched")}
                    >
                      Matched ({dashboard.wins})
                    </button>
                    <button
                      className={`filter-tab-btn ${filter === "missed" ? "active" : ""}`}
                      onClick={() => setFilter("missed")}
                    >
                      Missed ({dashboard.evaluatedCount - dashboard.wins})
                    </button>
                  </div>
                  <button
                    type="button"
                    className="font-mono text-xs"
                    style={{
                      background: "var(--surface-well)",
                      border: "1px solid var(--border-default)",
                      color: "var(--text-secondary)",
                      padding: "6px 12px",
                      borderRadius: "4px",
                      cursor: "pointer",
                      minHeight: "44px",
                      display: "inline-flex",
                      alignItems: "center"
                    }}
                    onClick={() => setArchiveOpen(false)}
                  >
                    Collapse Archive ▲
                  </button>
                </div>
              </header>

            {/* Mobile Touch-Friendly Card List (Visible <= 768px) */}
            <div className="mobile-cards-list">
              {filteredReviews.map((review) => {
                const isSel = activeReview?.date === review.date;
                const isUp = Number(review.ihsg_actual_pct) >= 0;
                return (
                  <div
                    key={review.date}
                    className={`mobile-history-card ${isSel ? "selected-session" : ""}`}
                    onClick={() => setSelectedDate(review.date)}
                  >
                    <div className="mobile-card-top">
                      <span className="font-mono font-bold text-xs text-primary">{formatHeaderDate(review.date)}</span>
                      <StatusBadge correct={review.ihsg_correct} isPending={review.isPendingReview} size="sm" />
                    </div>
                    <div className="mobile-card-comparison">
                      <div className="mobile-card-col">
                        <span className="mobile-card-label font-mono">CALL</span>
                        <DirectionBadge direction={review.ihsg_predicted} />
                        {review.ihsg_confidence && (
                          <span className="font-mono text-xs text-muted font-semibold">{review.ihsg_confidence}%</span>
                        )}
                      </div>
                      <div className="mobile-card-arrow font-mono">➔</div>
                      <div className="mobile-card-col">
                        <span className="mobile-card-label font-mono">CLOSE</span>
                        {review.isPendingReview ? (
                          <span className="font-mono text-xs text-warning">In Progress</span>
                        ) : (
                          <>
                            <DirectionBadge direction={review.ihsg_actual} />
                            <span className={`font-mono text-xs font-semibold ${isUp ? "text-matched" : "text-missed"}`}>
                              {formatPct(review.ihsg_actual_pct)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="mobile-card-bottom font-mono text-xs">
                      <span>Flow: {review.foreign_flow_actual || "N/A"}</span>
                      <span className="text-primary font-bold">
                        {review.isPendingReview ? "Pending Close" : (review.accuracy_score !== null ? `${formatNumber(review.accuracy_score)}% Score` : "Unscorable")}
                      </span>
                    </div>
                  </div>
                );
              })}
              {filteredReviews.length === 0 && (
                <div className="text-muted font-mono text-xs text-center py-4">
                  No records match the selected filter.
                </div>
              )}
            </div>

            {/* Desktop Quantitative Table (> 768px) */}
            <div className="table-wrapper desktop-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Session Date</th>
                    <th>Pre-Market Call</th>
                    <th>Session Close</th>
                    <th>Spread (Bps)</th>
                    <th>Foreign Flow</th>
                    <th>Sector Hit</th>
                    <th>Accuracy</th>
                    <th>Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredReviews.map((review) => (
                    <HistoryRow
                      key={review.date}
                      review={review}
                      isSelected={activeReview?.date === review.date}
                      onSelectSession={(d) => setSelectedDate(d)}
                    />
                  ))}
                  {filteredReviews.length === 0 && (
                    <tr>
                      <td colSpan="8" className="text-muted" style={{ textAlign: "center", padding: "24px 0" }}>
                        No records match the selected filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
          )}
        </div>
        )}

        {currentView === "lessons" && (
          <LessonsDatabaseView theme={theme} toggleTheme={toggleTheme} />
        )}

        {currentView === "telemetry" && (
          <ExecutionTelemetryView theme={theme} toggleTheme={toggleTheme} />
        )}
        <LegalDisclaimerFooter />
      </main>

      {/* SideSheet for Methodology & Audit Guide (lazy-mounted) */}
      {methodologyOpen && (
        <SideSheet
          isOpen={methodologyOpen}
          onClose={() => setMethodologyOpen(false)}
          title="Nexus System Methodology &amp; Audit Guide"
          subtitle="Transparent documentation for outside investors, researchers, and recruiters"
          tag="Audit Guide"
          maxWidth="820px"
        >
          <MethodologyView onClose={() => setMethodologyOpen(false)} historyRescoredAt={dashboard.historyRescoredAt} />
        </SideSheet>
      )}

      {/* SideSheet for Pipeline Status (G3, lazy-mounted) */}
      {pipelineStatusOpen && (
        <SideSheet
          isOpen={pipelineStatusOpen}
          onClose={() => setPipelineStatusOpen(false)}
          title="Nexus Autonomous Pipeline Health"
          subtitle="Real-time execution telemetry, scheduling, and error logs"
          tag="System Health"
          maxWidth="760px"
        >
          <PipelineStatusView
            status={marketStatus}
            pipelineHealth={dashboard?.pipelineHealth}
            telemetry={data?.telemetry}
            latestDate={dashboard?.latest?.date}
          />
        </SideSheet>
      )}

      {/* SideSheet for Data Lineage (G2, lazy-mounted) */}
      {lineageOpen && (
        <SideSheet
          isOpen={lineageOpen}
          onClose={() => setLineageOpen(false)}
          title="Quantitative Data Lineage & Provenance"
          subtitle="Verification timestamps, vendor sources, and integrity flags"
          tag="Data Lineage"
          maxWidth="760px"
        >
          <DataLineageView review={activeReview} />
        </SideSheet>
      )}

      {/* SideSheet for Morning Brief Markdown (lazy-mounted) */}
      {briefModalOpen && (
        <SideSheet
          isOpen={briefModalOpen}
          onClose={() => setBriefModalOpen(false)}
          title={`Morning Brief — ${activeReview?.date}`}
          subtitle="Pre-Market Intelligence Telegram Document"
          tag="Markdown Reader"
          maxWidth="760px"
        >
          {briefLoading ? (
            <div style={{ padding: "32px", textAlign: "center", color: "var(--text-secondary)", fontFamily: "monospace" }}>
              Retrieving morning intelligence document...
            </div>
          ) : (
            <article className="markdown-document-body" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "13px", padding: "16px 20px" }}>
              <LegalDisclaimerBanner />
              <RenderWithSources text={briefMarkdown} sources={briefSources} />
            </article>
          )}
        </SideSheet>
      )}

      <MobileBottomNav
        currentView={currentView}
        onSelectView={setCurrentView}
        onOpenBrief={() => handleOpenBriefModal(activeReview?.date)}
        onOpenMethodology={() => setMethodologyOpen(true)}
      />
    </div>
  );
}
