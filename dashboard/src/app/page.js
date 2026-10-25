"use client";

import { useEffect, useMemo, useState } from "react";
import LessonsDatabaseView from "../components/views/LessonsDatabaseView";
import ExecutionTelemetryView from "../components/views/ExecutionTelemetryView";
import SideSheet from "../components/common/SideSheet";
import MethodologyView from "../components/common/MethodologyView";
import DataLineageView from "../components/common/DataLineageView";
import PipelineStatusView from "../components/common/PipelineStatusView";
import PayoffTrajectoryChart from "../components/market-intelligence/PayoffTrajectoryChart";
import BenchmarkComparisonBars from "../components/market-intelligence/BenchmarkComparisonBars";
import ConfidenceCalibrationVisual from "../components/market-intelligence/ConfidenceCalibrationVisual";
import KpiDetailModal from "../components/market-intelligence/KpiDetailModal";

const formatPct = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0.0%";
  return `${num > 0 ? "+" : ""}${num.toFixed(2)}%`;
};

const formatNumber = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
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
    .replace(/\[([^\]]+)\]/g, "$1")
    .replace(/^Illustrative lesson:\s*/i, "")
    .replace(/^Illustrative:\s*/i, "")
    .replace(/^Demo fixture:\s*/i, "")
    .replace(/\billustrative\b\s*/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
};

const formatFlowLabel = (raw) => {
  if (!raw || raw === "Unknown" || raw === "N/A") return "Unverified";
  return String(raw).replace("/", " / ");
};

const getIdxMarketStatus = () => {
  try {
    const now = new Date();
    const wibStr = now.toLocaleString("en-US", { timeZone: "Asia/Jakarta" });
    const wib = new Date(wibStr);
    const day = wib.getDay();
    const hour = wib.getHours();
    const min = wib.getMinutes();
    const totalMin = hour * 60 + min;

    if (day === 0 || day === 6) {
      return { isOpen: false, status: "closed", label: "IDX: CLOSED (WEEKEND)" };
    }

    if (day >= 1 && day <= 4) {
      if (totalMin >= 540 && totalMin < 720) {
        return { isOpen: true, status: "open", label: "IDX: OPEN (SESI 1)" };
      }
      if (totalMin >= 720 && totalMin < 810) {
        return { isOpen: false, status: "recess", label: "IDX: BREAK" };
      }
      if (totalMin >= 810 && totalMin < 960) {
        return { isOpen: true, status: "open", label: "IDX: OPEN (SESI 2)" };
      }
      return { isOpen: false, status: "closed", label: "IDX: CLOSED" };
    }

    if (day === 5) {
      if (totalMin >= 540 && totalMin < 690) {
        return { isOpen: true, status: "open", label: "IDX: OPEN (SESI 1)" };
      }
      if (totalMin >= 690 && totalMin < 840) {
        return { isOpen: false, status: "recess", label: "IDX: BREAK" };
      }
      if (totalMin >= 840 && totalMin < 960) {
        return { isOpen: true, status: "open", label: "IDX: OPEN (SESI 2)" };
      }
      return { isOpen: false, status: "closed", label: "IDX: CLOSED" };
    }

    return { isOpen: false, status: "closed", label: "IDX: CLOSED" };
  } catch (e) {
    return { isOpen: false, status: "closed", label: "IDX: CLOSED" };
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

function PerformanceSparkline({ reviews = [] }) {
  if (!reviews || reviews.length === 0) return null;
  const chronPoints = [...reviews].reverse().map((r, i) => ({
    date: r.date,
    acc: Number(r.accuracy_score) || 50,
    hit: r.ihsg_correct,
    idx: i,
  }));

  const w = 136;
  const h = 32;
  const padX = 6;
  const padY = 5;
  const minVal = 10;
  const maxVal = 100;

  const getX = (i) => padX + (i / Math.max(1, chronPoints.length - 1)) * (w - 2 * padX);
  const getY = (val) => h - padY - ((Math.max(minVal, Math.min(maxVal, val)) - minVal) / (maxVal - minVal)) * (h - 2 * padY);

  const pointsD = chronPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${getX(i).toFixed(1)} ${getY(p.acc).toFixed(1)}`).join(" ");
  const areaD = `${pointsD} L ${getX(chronPoints.length - 1).toFixed(1)} ${h} L ${getX(0).toFixed(1)} ${h} Z`;
  const targetY = getY(60);

  return (
    <div className="sparkline-wrapper" title="Composite Accuracy Trajectory (Dashed: 60% Benchmark Target)">
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="sparkline-svg">
        <defs>
          <linearGradient id="kpiSparkGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity="0.0" />
          </linearGradient>
        </defs>
        <line
          x1={padX}
          y1={targetY}
          x2={w - padX}
          y2={targetY}
          stroke="var(--border-strong)"
          strokeDasharray="2,2"
          strokeWidth="1"
          opacity="0.65"
        />
        <path d={areaD} fill="url(#kpiSparkGrad)" />
        <path
          d={pointsD}
          fill="none"
          stroke="var(--accent-cyan)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {chronPoints.map((p, i) => (
          <circle
            key={i}
            cx={getX(i)}
            cy={getY(p.acc)}
            r={2.5}
            fill={p.hit ? "var(--matched-text)" : "var(--missed-text)"}
            stroke="var(--surface)"
            strokeWidth="1"
          />
        ))}
      </svg>
    </div>
  );
}

function StatusBadge({ correct, isPending, size = "md" }) {
  if (isPending || correct === null || correct === undefined) {
    return (
      <span className={`status-pill status-pending ${size === "sm" ? "status-sm" : ""}`}>
        <span className="status-indicator-dot" />
        <span className="status-text">IN PROGRESS</span>
      </span>
    );
  }
  return (
    <span className={`status-pill ${correct ? "status-matched" : "status-missed"} ${size === "sm" ? "status-sm" : ""}`}>
      <span className="status-indicator-dot" />
      <span className="status-text">{correct ? "MATCHED" : "MISSED"}</span>
    </span>
  );
}

function DirectionBadge({ direction }) {
  const dir = (direction || "").toLowerCase();
  let badgeClass = "dir-neutral";
  let arrow = "—";
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
    <span className={`dir-badge ${badgeClass}`}>
      <span className="dir-glyph">{arrow}</span>
      <span>{direction ? direction.toUpperCase() : "NEUTRAL"}</span>
    </span>
  );
}

function SectorAttribution({ review }) {
  const sectors = review?.sector_accuracy || {};
  const entries = Object.entries(sectors);

  if (entries.length === 0) return null;

  const isPending = Boolean(review?.isPendingReview);
  const verifiableEntries = entries.filter(([_, val]) => isPending || val === true || val === false);
  const unverifiedNames = entries.filter(([_, val]) => !isPending && val === null).map(([sec]) => sec);
  const matchCount = verifiableEntries.filter(([_, val]) => val === true).length;

  return (
    <div className="eval-pane-section">
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Sector Attribution</span>
        <span className="eval-section-tag font-mono">
          {isPending
            ? "Predicted Bias"
            : (verifiableEntries.length > 0 ? `${matchCount}/${verifiableEntries.length} Scorable Matched` : "No Verifiable Closing %")}
        </span>
      </div>

      {verifiableEntries.length > 0 && (
        <div className="sector-matrix-grid">
          {verifiableEntries.map(([sector, statusOrHit]) => {
            let label = "✗ Miss";
            let badgeCls = "badge-missed";
            if (isPending) {
              badgeCls = statusOrHit === "BULLISH" ? "badge-matched" : (statusOrHit === "BEARISH" ? "badge-missed" : "badge-neutral");
              label = String(statusOrHit);
            } else if (statusOrHit === true) {
              badgeCls = "badge-matched";
              label = "✓ Match";
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
      )}

      {unverifiedNames.length > 0 && (
        <div style={{ marginTop: verifiableEntries.length > 0 ? "6px" : "0", fontSize: "11px", color: "var(--text-tertiary)", lineHeight: 1.4 }}>
          <span className="font-mono" style={{ fontWeight: 600 }}>Unverified (excluded from score):</span>{" "}
          {unverifiedNames.join(" · ")}
        </div>
      )}
    </div>
  );
}

function MacroPulse({ review }) {
  const commodities = Object.values(review?.actual_commodities || {}).filter(
    (item) => item && item.name && ((item.price !== null && Number.isFinite(Number(item.price))) || (item.change_pct !== null && Number.isFinite(Number(item.change_pct))))
  );

  const foreignPredicted = formatFlowLabel(review?.foreign_flow_predicted);
  const foreignActual = review?.isPendingReview ? "Market Open" : formatFlowLabel(review?.foreign_flow_actual);
  const foreignCorrect = review?.foreign_flow_correct;
  const usdidr = review?.actual_usdidr;
  const isUsdNumeric = Number.isFinite(Number(usdidr)) && Number(usdidr) > 0;

  return (
    <div className="eval-pane-section">
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Cross-Asset &amp; Liquidity</span>
        <span className="eval-section-tag font-mono">Close Snapshot</span>
      </div>
      <div className="macro-tape-strip">
        <div className="macro-tape-row liquidity-row">
          <div className="macro-strip-cell">
            <div className="macro-cell-head">Foreign Flow (IDX)</div>
            <div className="macro-cell-val font-mono" style={{ color: foreignActual === "Unverified" ? "var(--text-tertiary)" : "var(--text-primary)" }}>
              {foreignActual}
            </div>
            <div className="macro-cell-sub font-mono">
              <span className="macro-sub-label">Exp: {foreignPredicted}</span>
              {review?.isPendingReview ? (
                <span className="text-secondary font-mono" style={{ fontSize: "10px" }}>
                  (● Active)
                </span>
              ) : foreignCorrect !== undefined && foreignCorrect !== null ? (
                <span className={`macro-match-tag font-mono ${foreignCorrect ? "is-match" : "is-miss"}`}>
                  {foreignCorrect ? "✓ Match" : "✗ Miss"}
                </span>
              ) : null}
            </div>
          </div>

          <div className="macro-strip-cell">
            <div className="macro-cell-head">USD / IDR</div>
            <div className="macro-cell-val font-mono">
              {isUsdNumeric ? `Rp ${formatNumber(usdidr)}` : (usdidr && usdidr !== "Illustrative" ? String(usdidr) : "Unavailable")}
            </div>
            <div className="macro-cell-sub">
              {review?.isPendingReview ? "Prev Close Ref" : "Session Close"}
            </div>
          </div>
        </div>

        {commodities.length > 0 && (
          <div
            className="macro-tape-row commodities-row"
            style={{ gridTemplateColumns: `repeat(${Math.min(4, commodities.length)}, minmax(0, 1fr))` }}
          >
            {commodities.map((item) => {
              const hasPrice = item.price !== null && item.price !== undefined && Number.isFinite(Number(item.price)) && Number(item.price) > 0;
              const hasChange = item.change_pct !== null && item.change_pct !== undefined && Number.isFinite(Number(item.change_pct));
              const change = Number(item.change_pct || 0);
              const isUp = change >= 0;
              return (
                <div className="macro-strip-cell" key={item.ticker || item.name}>
                  <div className="macro-cell-head" title={item.name}>{item.name}</div>
                  {hasPrice ? (
                    <>
                      <div className="macro-cell-val font-mono">${formatNumber(item.price)}</div>
                      {hasChange && (
                        <div className={`macro-cell-sub font-mono ${isUp ? "text-matched" : "text-missed"}`}>
                          {formatPct(item.change_pct)} 1D
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div className={`macro-cell-val font-mono ${isUp ? "text-matched" : "text-missed"}`}>
                        {formatPct(item.change_pct)}
                      </div>
                      <div className="macro-cell-sub font-mono">1D Change</div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function cleanWatchlistNote(ticker, note) {
  if (!note || typeof note !== "string") return "";
  let clean = note
    .replace(new RegExp(`^${ticker}[:\\s-]+`, "i"), "")
    .replace(/,\s*src_[a-zA-Z0-9_-]+/gi, "")
    .replace(/[\(\[]?\s*src_[a-zA-Z0-9_-]+\s*[\)\]]?/gi, "")
    .replace(/\(\s*,?\s*/g, "(")
    .replace(/,\s*\)/g, ")")
    .replace(/\(\s*\)/g, "")
    .replace(/^[-,:\s]+/, "")
    .replace(/[-,:\s]+$/, "")
    .trim();
  clean = clean.replace(/No price change provided for [^,]+,\s*but expected to be/i, "Expected to be");
  return clean;
}

function ActionableMarketSetup({ review }) {
  const pivot = Number(review?.premarket_pivot || review?.ihsg_prev || review?.ihsg_close || 0);
  const s1 = Number(review?.premarket_s1 || review?.dynamic_s1 || (pivot ? Math.round(pivot * 0.993) : 0));
  const r1 = Number(review?.premarket_r1 || review?.dynamic_r1 || (pivot ? Math.round(pivot * 1.007) : 0));

  const focusWatchlist = Array.isArray(review?.actionable_watchlist) ? review.actionable_watchlist : [];

  if (!pivot && focusWatchlist.length === 0) return null;

  const detailedTickers = [];
  const compactTickers = [];
  focusWatchlist.forEach((item) => {
    const cleaned = cleanWatchlistNote(item.ticker, item.note);
    const isGeneric = !cleaned || /Sector catalyst from morning brief/i.test(cleaned);
    if (isGeneric) {
      compactTickers.push(item.ticker);
    } else {
      detailedTickers.push({ ...item, cleanedNote: cleaned });
    }
  });

  return (
    <div className="eval-pane-section" style={{ borderBottom: "none" }}>
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Pre-Market Levels &amp; Watchlist</span>
        <span className="eval-section-tag font-mono">
          {review?.premarket_s1 ? "Morning Brief Levels" : "14D ATR Band"}
        </span>
      </div>

      {pivot > 0 && (
        <div className="actionable-levels-strip">
          <div className="level-box">
            <span className="level-label font-mono">S1 SUPPORT</span>
            <span className="level-val font-mono text-missed">{formatNumber(Math.round(s1))}</span>
          </div>
          <div className="level-box pivot-box">
            <span className="level-label font-mono">PIVOT</span>
            <span className="level-val font-mono text-primary">{formatNumber(Math.round(pivot))}</span>
          </div>
          <div className="level-box">
            <span className="level-label font-mono">R1 RESISTANCE</span>
            <span className="level-val font-mono text-matched">{formatNumber(Math.round(r1))}</span>
          </div>
        </div>
      )}

      {detailedTickers.length > 0 && (
        <div className="focus-ticker-grid" style={{ marginTop: "8px" }}>
          {detailedTickers.slice(0, 4).map((item) => (
            <div className="focus-ticker-cell" key={item.ticker}>
              <div className="ticker-cell-top">
                <span className="ticker-symbol font-mono">{item.ticker}</span>
                <span className={`ticker-bias font-mono ${item.bias === "BULLISH" ? "text-matched" : (item.bias === "DEFENSIVE" ? "text-warning" : "text-muted")}`}>
                  {item.bias}
                </span>
              </div>
              <div className="ticker-cell-note">
                <RenderWithSources text={item.cleanedNote} sources={review?.sources} />
              </div>
            </div>
          ))}
        </div>
      )}

      {compactTickers.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
          <span className="font-mono text-xs text-muted">Focus Tickers:</span>
          {compactTickers.map((t) => (
            <span
              key={t}
              className="font-mono text-xs"
              style={{
                padding: "2px 8px",
                borderRadius: "4px",
                background: "var(--surface-subtle)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontWeight: 600,
              }}
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function HeuristicRuleItem({ lesson, index }) {
  const text = cleanNarrative(lesson);

  let trigger = "";
  let impact = "";

  if (/^Ketika\s+/i.test(text) && /\bmaka\s+/i.test(text)) {
    const withoutKetika = text.replace(/^Ketika\s+/i, "");
    const parts = withoutKetika.split(/\bmaka\s+/i);
    trigger = parts[0]?.replace(/,?\s*terjadi\s*$/i, "").trim() || "";
    impact = parts.slice(1).join(" ")?.trim() || "";
  } else if (text.includes("–") || text.includes(" - ")) {
    const parts = text.split(/\s+[-–]\s+/);
    trigger = parts[0]?.trim() || text;
    impact = parts.slice(1).join(" - ")?.trim() || "";
  }

  return (
    <div
      style={{
        padding: "10px 12px",
        background: "var(--surface-subtle)",
        border: "1px solid var(--border-subtle)",
        borderLeft: "3px solid var(--accent-cyan)",
        borderRadius: "var(--radius-sm)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "5px" }}>
        <span className="font-mono text-xs font-bold" style={{ color: "var(--accent-cyan)" }}>
          RULE #{index + 1}
        </span>
        <span className="memory-injected-pill font-mono">→ Next 06:55 Brief</span>
      </div>

      {trigger && impact ? (
        <div style={{ fontSize: "12px", lineHeight: 1.45, color: "var(--text-secondary)" }}>
          <strong style={{ color: "var(--text-primary)" }}>WHEN:</strong> {trigger}{" "}
          <strong style={{ color: "var(--matched-text)" }}>→ THEN:</strong> {impact}
        </div>
      ) : (
        <p style={{ fontSize: "12px", lineHeight: 1.45, color: "var(--text-primary)", margin: 0 }}>{text}</p>
      )}
    </div>
  );
}

function RCAPanel({ review }) {
  const [showAllDrivers, setShowAllDrivers] = useState(false);

  const lessons = (review?.lessons || []).slice(0, 2);
  const rawDrivers = [
    ...(review?.rca_unanticipated || []).map((text) => ({ type: "UNANTICIPATED", cls: "type-unanticipated", text: cleanNarrative(text) })),
    ...(review?.rca_underestimated || []).map((text) => ({ type: "UNDERESTIMATED", cls: "type-underestimated", text: cleanNarrative(text) })),
    ...(review?.rca_overestimated || []).map((text) => ({ type: "OVERWEIGHTED", cls: "type-overestimated", text: cleanNarrative(text) })),
  ].filter((d) => d.text);

  // Deduplicate drivers that repeat the same opening phrase
  const seenKeys = new Set();
  const uniqueDrivers = rawDrivers.filter((d) => {
    const norm = d.text.toLowerCase().slice(0, 36);
    if (seenKeys.has(norm)) return false;
    seenKeys.add(norm);
    return true;
  });

  const visibleDrivers = showAllDrivers ? uniqueDrivers : uniqueDrivers.slice(0, 4);

  return (
    <div className="eval-pane">
      <div className="eval-pane-header">
        <div className="eval-pane-header-left">
          <span className="eval-pane-title">Root Cause &amp; Learned Rules</span>
        </div>
        <div className="loop-active-tag font-mono">
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
          Self-Learning Loop
        </div>
      </div>

      <div className="eval-pane-body">
        {uniqueDrivers.length > 0 && (
          <div className="rca-diagnostic-section">
            <div className="rca-subheading">
              <span>Variance Attribution ({uniqueDrivers.length})</span>
            </div>
            <div className="rca-diagnostic-list">
              {visibleDrivers.map((item, idx) => (
                <div key={idx} className="rca-diagnostic-item">
                  <span className={`rca-diagnostic-type ${item.cls} font-mono`}>{item.type}</span>
                  <span className="rca-diagnostic-text">
                    <RenderWithSources text={item.text} sources={review?.sources} />
                  </span>
                </div>
              ))}
            </div>
            {uniqueDrivers.length > 4 && (
              <button
                type="button"
                onClick={() => setShowAllDrivers(!showAllDrivers)}
                className="watchlist-toggle-btn font-mono"
                style={{ marginTop: "4px" }}
              >
                {showAllDrivers
                  ? "Show Top 4 Variance Drivers ▴"
                  : `+ Show ${uniqueDrivers.length - 4} More Variance Drivers ▾`}
              </button>
            )}
          </div>
        )}

        {lessons.length > 0 && (
          <div className="rca-lesson-section">
            <div className="rca-subheading">
              <span>Extracted Session Rules ({lessons.length})</span>
              <span className="font-mono text-xs text-muted">Cap: Max 2/Session</span>
            </div>
            {lessons.map((lesson, idx) => (
              <HeuristicRuleItem key={idx} lesson={lesson} index={idx} />
            ))}
          </div>
        )}

        {uniqueDrivers.length === 0 && lessons.length === 0 && (
          <p className="rca-content-muted">
            {review?.isPendingReview
              ? "Session in progress. Post-market evaluation runs at 20:00 WIB."
              : "No parameter revisions extracted for this session."}
          </p>
        )}
      </div>
    </div>
  );
}

function HistoryRow({ review, isSelected, onSelectSession }) {
  const [expanded, setExpanded] = useState(false);
  const isUp = Number(review.ihsg_actual_pct) >= 0;
  const accuracyNum = Math.min(100, Math.max(0, Number(review.accuracy_score) || 0));
  const bpsNum = Math.round(Number(review.ihsg_actual_pct || 0) * 100);

  const secEntries = Object.entries(review.sector_accuracy || {});
  const secVerifiable = secEntries.filter(([_, hit]) => hit === true || hit === false);
  const secMatches = secVerifiable.filter(([_, hit]) => hit === true).length;
  const secTotal = secVerifiable.length;

  const rowUsdIdr = Number.isFinite(Number(review.actual_usdidr))
    ? `Rp ${formatNumber(review.actual_usdidr)}`
    : "—";

  const flowLabel = formatFlowLabel(review.foreign_flow_actual);

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
          <div className="table-call-cell">
            <DirectionBadge direction={review.ihsg_predicted} />
            {review.ihsg_confidence && (
              <span className="font-mono text-xs text-muted font-semibold">{review.ihsg_confidence}%</span>
            )}
          </div>
        </td>
        <td>
          <DirectionBadge direction={review.isPendingReview ? "PENDING" : review.ihsg_actual} />
        </td>
        <td>
          {review.isPendingReview ? (
            <span className="font-mono text-xs text-muted">In Progress</span>
          ) : (
            <div className="delta-cell font-mono">
              <span className={isUp ? "text-matched" : "text-missed"}>{formatPct(review.ihsg_actual_pct)}</span>
              <span className="bps-text text-muted">({bpsNum > 0 ? `+${bpsNum}` : bpsNum} bps)</span>
            </div>
          )}
        </td>
        <td>
          <div className="font-mono text-xs flow-cell">
            <span className={flowLabel === "Unverified" ? "text-muted" : ""}>{flowLabel}</span>
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
              ? `${secEntries.length} Tracked`
              : (secTotal > 0 ? `${secMatches}/${secTotal} (${Math.round((secMatches / secTotal) * 100)}%)` : "—")}
          </span>
        </td>
        <td>
          {review.isPendingReview ? (
            <span className="font-mono text-xs text-muted">Pending</span>
          ) : (
            <div className="accuracy-cell font-mono">
              <span className="accuracy-text">{formatNumber(review.accuracy_score)}%</span>
              <div className="accuracy-bar-track">
                <div className="accuracy-bar-fill" style={{ width: `${accuracyNum}%` }} />
              </div>
            </div>
          )}
        </td>
        <td>
          <StatusBadge correct={review.ihsg_correct} isPending={review.isPendingReview} size="sm" />
        </td>
      </tr>
      {expanded && (
        <tr className="expanded-row">
          <td colSpan="8" style={{ padding: 0 }}>
            <div className="expanded-panel">
              <div className="expanded-grid">
                <div className="detail-item">
                  <div className="detail-label">Foreign Flow</div>
                  <div className="detail-value">{flowLabel}</div>
                  <div className="detail-sub font-mono">
                    Exp: {formatFlowLabel(review.foreign_flow_predicted)}{" "}
                    {review.isPendingReview ? (
                      <span className="text-secondary" style={{ fontSize: "10px", marginLeft: "4px" }}>
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
                  <div className="detail-label">USD / IDR</div>
                  <div className="detail-value font-mono">{rowUsdIdr}</div>
                  <div className="detail-sub">Session close</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label">Verifiable Sector Checks</div>
                  <div className="detail-sub">
                    {secVerifiable.length > 0 ? (
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                        {secVerifiable.map(([sec, hit]) => (
                          <span key={sec} className="sector-tile" style={{ fontSize: "10px", padding: "2px 6px" }}>
                            {sec}: <span className={hit ? "text-matched" : "text-missed"}>{hit ? "✓ MATCH" : "✗ MISS"}</span>
                          </span>
                        ))}
                      </div>
                    ) : (
                      "No scorable sector closing % in feed"
                    )}
                  </div>
                </div>
              </div>
              {review.lessons && review.lessons.length > 0 && (
                <div className="expanded-lesson">
                  <div className="detail-label" style={{ marginBottom: "4px" }}>Extracted Lesson</div>
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

function Sidebar({ reviews = [], selectedDate, onSelectDate, currentView = "market", onSelectView }) {
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
          <div className="nav-section-title">Views</div>
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
        </div>
      </nav>

      {reviews.length > 0 && (
        <div className="sidebar-sessions" style={{ maxHeight: "240px", overflowY: "auto" }}>
          <div className="sidebar-session-title">Sessions ({reviews.length})</div>
          {reviews.map((r) => {
            const isSel = (!selectedDate && r.date === reviews[0]?.date) || selectedDate === r.date;
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
                <span className={`font-mono ${r.isPendingReview ? "text-warning" : (r.ihsg_correct ? "text-matched" : "text-missed")}`}>
                  {r.isPendingReview ? "⏳ Live" : (r.ihsg_correct ? "✓ Hit" : "✗ Miss")}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <div className="sidebar-telemetry">
        <div className="telemetry-box-title">Daily Schedule (WIB)</div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">06:55</span>
          <span className="telemetry-box-val font-mono">Morning Brief</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">16:00</span>
          <span className="telemetry-box-val font-mono">IDX Market Close</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">20:00</span>
          <span className="telemetry-box-val font-mono">Audit &amp; RCA</span>
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="vault-status">
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
          <span>Vault Synced</span>
        </div>
        <span className="system-tag font-mono">v2.5</span>
      </div>
    </aside>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [theme, setTheme] = useState("dark");
  const [filter, setFilter] = useState("all");
  const [historyPage, setHistoryPage] = useState(1);
  const [selectedDate, setSelectedDate] = useState(null);
  const [currentView, setCurrentView] = useState("market");
  const [marketStatus, setMarketStatus] = useState({ isOpen: false, status: "closed", label: "IDX: CLOSED" });
  const [briefModalOpen, setBriefModalOpen] = useState(false);
  const [briefMarkdown, setBriefMarkdown] = useState("");
  const [briefSources, setBriefSources] = useState({});
  const [briefLoading, setBriefLoading] = useState(false);
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const [lineageOpen, setLineageOpen] = useState(false);
  const [pipelineStatusOpen, setPipelineStatusOpen] = useState(false);
  const [activeBenchTab, setActiveBenchTab] = useState(null); // null | 'trajectory' | 'baselines' | 'calibration'
  const [activeKpiModal, setActiveKpiModal] = useState(null);

  const HISTORY_PAGE_SIZE = 8;

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
    const savedTheme = localStorage.getItem("nexus-theme") || "dark";
    setTheme(savedTheme);
    document.documentElement.setAttribute("data-theme", savedTheme);

    fetch("/api/stats")
      .then((res) => res.json())
      .then((json) => {
        if (!json.success) {
          throw new Error(json.error || "Dashboard data unavailable");
        }
        setData(json);
      })
      .catch((err) => {
        console.error(err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setMarketStatus(getIdxMarketStatus());
    const statusTimer = setInterval(() => {
      setMarketStatus(getIdxMarketStatus());
    }, 15000);
    return () => clearInterval(statusTimer);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("nexus-theme", nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
  };

  const dashboard = useMemo(() => {
    if (!data) return null;

    const reviews = data.reviews || [];
    const latest = reviews[0];
    const evaluatedReviews = reviews.filter((r) => !r.isPendingReview);
    const wins = evaluatedReviews.filter((review) => review.ihsg_correct).length;
    const winRate = evaluatedReviews.length ? ((wins / evaluatedReviews.length) * 100).toFixed(1) : "0.0";
    const avgAccuracy = Number(data.stats?.avgAccuracy || 0).toFixed(1);

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
    const computedSectorRate = totalSectorChecks > 0 ? ((totalSectorHits / totalSectorChecks) * 100).toFixed(1) : "0.0";
    const sectorHitRate = data.stats?.sectorAccuracy != null ? Number(data.stats.sectorAccuracy).toFixed(1) : computedSectorRate;
    const totalLessons = data.stats?.totalLessonsCount ?? data.nexusStats?.all_lessons?.length ?? reviews.reduce((acc, r) => acc + (r.lessons?.length || 0), 0);
    const quarantinedLessonsCount = data.stats?.quarantinedLessonsCount ?? data.nexusStats?.rejected_lessons?.length ?? 0;

    return {
      stats: data.stats || {},
      reviews,
      evaluatedReviews,
      latest,
      avgAccuracy,
      winRate: data.stats?.directionAccuracy != null ? Number(data.stats.directionAccuracy).toFixed(1) : winRate,
      wins: data.stats?.directionCorrectCount ?? wins,
      evaluatedCount: data.stats?.directionScorableSessions ?? evaluatedReviews.length,
      totalSectorChecks: data.stats?.sectorVerifiableCount ?? totalSectorChecks,
      totalSectorHits: data.stats?.sectorCorrectCount ?? totalSectorHits,
      sectorHitRate,
      totalLessons,
      quarantinedLessonsCount,
      isDemo: Boolean(data.isDemo),
    };
  }, [data]);

  const activeReview = useMemo(() => {
    if (!dashboard) return null;
    if (!selectedDate) return dashboard.latest;
    return dashboard.reviews.find((r) => r.date === selectedDate) || dashboard.latest;
  }, [dashboard, selectedDate]);

  const isHistorical = Boolean(activeReview && dashboard?.latest && activeReview.date !== dashboard.latest.date);

  const benchmarkValue = useMemo(() => {
    const lat = dashboard?.latest;
    if (!lat) return "—";
    if (lat.ihsg_close && Number.isFinite(Number(lat.ihsg_close))) return formatNumber(lat.ihsg_close);
    if (lat.previous_close && Number.isFinite(Number(lat.previous_close))) return formatNumber(lat.previous_close);
    const lastEvaluated = dashboard?.reviews?.find((r) => !r.isPendingReview && r.ihsg_close);
    if (lastEvaluated?.ihsg_close) return formatNumber(lastEvaluated.ihsg_close);
    const summaryMatch = (lat.summary || "").match(/(?:JCI|IHSG)\s+(?:closed at\s+)?([0-9,.]+)/i);
    if (summaryMatch && summaryMatch[1]) return summaryMatch[1];
    return "—";
  }, [dashboard]);

  const filteredReviews = useMemo(() => {
    if (!dashboard) return [];
    if (filter === "matched") return dashboard.reviews.filter((r) => r.ihsg_correct === true);
    if (filter === "missed") return dashboard.reviews.filter((r) => !r.isPendingReview && r.ihsg_correct === false);
    return dashboard.reviews;
  }, [dashboard, filter]);

  const totalHistoryPages = Math.max(1, Math.ceil(filteredReviews.length / HISTORY_PAGE_SIZE));
  const safeHistoryPage = Math.min(historyPage, totalHistoryPages);
  const paginatedReviews = useMemo(() => {
    const start = (safeHistoryPage - 1) * HISTORY_PAGE_SIZE;
    return filteredReviews.slice(start, start + HISTORY_PAGE_SIZE);
  }, [filteredReviews, safeHistoryPage]);

  if (loading) {
    return <main className="center-state">Loading market intelligence...</main>;
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
  const toggleBenchTab = (tab) => {
    setActiveBenchTab((prev) => (prev === tab ? null : tab));
  };

  return (
    <div className="layout-root">
      <Sidebar
        reviews={dashboard.reviews}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
        currentView={currentView}
        onSelectView={setCurrentView}
      />

      <main className="main-viewport">
        {currentView === "market" && (
        <div className="content-container">
          <header className="page-header">
            <div>
              <div className="breadcrumb">NEXUS · IDX Quantitative Intelligence</div>
              <h1 className="page-title">Daily Market Evaluation</h1>
            </div>
            <div className="header-actions">
              <div className={`market-status-chip is-${marketStatus.status}`}>
                <span className={`live-dot ${marketStatus.isOpen ? "dot-open" : (marketStatus.status === "recess" ? "dot-amber" : "dot-closed")}`}></span>
                <span>{marketStatus.label}</span>
              </div>
              <button
                type="button"
                className="header-pill-btn"
                onClick={() => setPipelineStatusOpen(true)}
                title="View Pipeline Telemetry"
              >
                Status
              </button>
              <button
                type="button"
                className="header-pill-btn"
                onClick={() => setLineageOpen(true)}
                title="View Quantitative Data Lineage"
              >
                Lineage
              </button>
              <button
                type="button"
                className="header-pill-btn"
                onClick={() => setMethodologyOpen(true)}
                title="View Scoring Methodology & Guide"
              >
                Methodology
              </button>
              <button
                className="theme-toggle-btn"
                onClick={toggleTheme}
                title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
                aria-label="Toggle theme"
              >
                {theme === "dark" ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </button>
            </div>
          </header>

          {/* Compact Context Strip */}
          <div className="system-context-strip">
            <div className="context-item">
              <span className="context-label font-mono">IHSG CLOSE</span>
              <div className={`context-value font-mono font-semibold ${dashboard.latest?.isPendingReview ? "text-secondary" : (Number(dashboard.latest?.ihsg_actual_pct) >= 0 ? "text-matched" : "text-missed")}`}>
                {benchmarkValue}{" "}
                <span className="context-sub font-mono">
                  ({dashboard.latest?.isPendingReview ? "Prev Close" : formatPct(dashboard.latest?.ihsg_actual_pct)})
                </span>
              </div>
            </div>
            <div className="context-divider" />
            <div className="context-item">
              <span className="context-label font-mono">FOREIGN FLOW</span>
              <div className="context-value font-medium">
                {dashboard.latest?.isPendingReview
                  ? `Exp: ${formatFlowLabel(dashboard.latest?.foreign_flow_predicted)}`
                  : formatFlowLabel(dashboard.latest?.foreign_flow_actual)}
              </div>
            </div>
            <div className="context-divider" />
            <div className="context-item">
              <span className="context-label font-mono">CLOSED-LOOP PIPELINE</span>
              <div className="context-value font-mono text-xs" style={{ color: "var(--text-secondary)" }}>
                06:55 Forecast Lock → 16:00 IDX Close → 20:00 Audit &amp; Memory Gate
              </div>
            </div>
          </div>

          {/* 4 Core KPI Cards (Equal Height) */}
          <section className="kpi-row" style={{ marginBottom: "16px" }}>
            <div
              className="kpi-card interactive"
              onClick={() => setActiveKpiModal("hit_rate")}
              title="Click to view Directional Hit Rate & Benchmark Breakdown"
            >
              <div className="kpi-top">
                <span className="kpi-label font-mono">IHSG Hit Rate</span>
                <span className="kpi-click-hint font-mono">Details ↗</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">{dashboard.winRate}%</div>
                <div className="outcome-pips font-mono" style={{ flexWrap: "nowrap" }} title="Last 6 evaluated sessions (newest first)">
                  {dashboard.reviews.slice(0, 6).map((r) => (
                    <span
                      key={r.date}
                      className={`outcome-pip ${r.isPendingReview ? "pip-pending" : (r.ihsg_correct ? "pip-hit" : "pip-miss")}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedDate(r.date);
                      }}
                      title={`${formatHeaderDate(r.date)}: ${r.isPendingReview ? "Live" : (r.ihsg_correct ? "Hit" : "Miss")}`}
                    >
                      {r.isPendingReview ? "⏳" : (r.ihsg_correct ? "●" : "✗")}
                    </span>
                  ))}
                </div>
              </div>
              <div className="kpi-context">
                <span>{dashboard.wins} / {dashboard.evaluatedCount} sessions matched direction</span>
                <div className="kpi-mini-bar">
                  <div
                    className="kpi-mini-fill"
                    style={{ width: `${Math.min(100, Math.max(0, Number(dashboard.winRate) || 0))}%` }}
                  />
                </div>
              </div>
            </div>

            <div
              className="kpi-card interactive"
              onClick={() => setActiveKpiModal("accuracy")}
              title="Click to view 50/30/20 Attribution Formula & Calibration"
            >
              <div className="kpi-top">
                <span className="kpi-label font-mono">Composite Score</span>
                <span className="kpi-click-hint font-mono">Formula ↗</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">{dashboard.avgAccuracy}%</div>
                <PerformanceSparkline reviews={dashboard.reviews} />
              </div>
              <div className="kpi-context">
                <span>50% Direction · 30% Sector · 20% Flow</span>
                <div className="kpi-mini-bar">
                  <div
                    className="kpi-mini-fill"
                    style={{ width: `${Math.min(100, Math.max(0, Number(dashboard.avgAccuracy) || 0))}%` }}
                  />
                </div>
              </div>
            </div>

            <div
              className="kpi-card interactive"
              onClick={() => setActiveKpiModal("sector")}
              title="Click to view Sector Win Rate Matrix"
            >
              <div className="kpi-top">
                <span className="kpi-label font-mono">Sector Accuracy</span>
                <span className="kpi-click-hint font-mono">Matrix ↗</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">{dashboard.sectorHitRate}%</div>
                <div className="kpi-tag-visual font-mono">
                  <span className="text-matched font-semibold">{dashboard.totalSectorHits}</span>
                  <span className="text-muted"> / {dashboard.totalSectorChecks} Scorable</span>
                </div>
              </div>
              <div className="kpi-context">
                <span>Deterministic commodity → sector rules</span>
                <div className="kpi-mini-bar">
                  <div
                    className="kpi-mini-fill"
                    style={{ width: `${Math.min(100, Math.max(0, Number(dashboard.sectorHitRate) || 0))}%` }}
                  />
                </div>
              </div>
            </div>

            <div
              className="kpi-card interactive"
              onClick={() => setActiveKpiModal("memory")}
              title="Click to view Validated & Quarantined Heuristic Rules"
            >
              <div className="kpi-top">
                <span className="kpi-label font-mono">Learned Rules</span>
                <span className="kpi-click-hint font-mono">Audit ↗</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">
                  {dashboard.totalLessons}{" "}
                  <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)" }}>Valid</span>
                </div>
                <span className="memory-active-pill font-mono">
                  <span className="live-dot" style={{ width: 6, height: 6 }}></span>
                  {dashboard.quarantinedLessonsCount} Blocked
                </span>
              </div>
              <div className="kpi-context">
                <span>5-stage hygiene gate → 06:55 prompt</span>
                <div className="kpi-mini-bar">
                  <div className="kpi-mini-fill" style={{ width: "100%" }} />
                </div>
              </div>
            </div>
          </section>

          {/* 1-Click Quantitative Benchmark Bar */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "10px",
              padding: "8px 14px",
              marginBottom: activeBenchTab ? "12px" : "24px",
              background: "var(--surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              boxShadow: "var(--shadow-card)",
            }}
          >
            <span className="font-mono text-xs text-secondary">
              Sample: <strong className="text-primary">n={dashboard.evaluatedCount}</strong> · 95% Wilson CI:{" "}
              <strong className="text-primary">
                [{data?.stats?.directionCi95?.lower_pct ?? data?.nexusStats?.direction_ci_95?.lower_pct ?? "—"}%,{" "}
                {data?.stats?.directionCi95?.upper_pct ?? data?.nexusStats?.direction_ci_95?.upper_pct ?? "—"}%]
              </strong>
            </span>
            <div className="filter-tabs">
              <button
                type="button"
                onClick={() => toggleBenchTab("trajectory")}
                className={`filter-tab-btn font-mono text-xs ${activeBenchTab === "trajectory" ? "active" : ""}`}
              >
                📈 Equity Curve ({data?.stats?.payoff?.long_short_total_bps != null ? `${data.stats.payoff.long_short_total_bps >= 0 ? "+" : ""}${(Number(data.stats.payoff.long_short_total_bps) / 100).toFixed(2)}% L/S` : "View"})
              </button>
              <button
                type="button"
                onClick={() => toggleBenchTab("baselines")}
                className={`filter-tab-btn font-mono text-xs ${activeBenchTab === "baselines" ? "active" : ""}`}
              >
                📊 Naive Baselines
              </button>
              <button
                type="button"
                onClick={() => toggleBenchTab("calibration")}
                className={`filter-tab-btn font-mono text-xs ${activeBenchTab === "calibration" ? "active" : ""}`}
              >
                🎯 Calibration &amp; Brier
              </button>
            </div>
          </div>

          {activeBenchTab && (
            <div className="bench-panel" style={{ marginTop: "0", marginBottom: "24px" }}>
              {activeBenchTab === "trajectory" && (
                <PayoffTrajectoryChart
                  reviews={dashboard?.reviews || data?.reviews || []}
                  payoffStats={data?.nexusStats?.payoff || data?.stats?.payoff || {}}
                  onSelectDate={(d) => setSelectedDate(d)}
                />
              )}
              {activeBenchTab === "baselines" && (
                <BenchmarkComparisonBars
                  nStats={data?.nexusStats || data?.stats || {}}
                />
              )}
              {activeBenchTab === "calibration" && (
                <ConfidenceCalibrationVisual
                  calibration={data?.nexusStats?.calibration || data?.stats?.calibration || {}}
                />
              )}
            </div>
          )}

          {/* Active Session Evaluation */}
          {activeReview && (
            <section className="eval-section" style={{ marginBottom: "24px" }}>
              <header className="eval-header">
                <div className="eval-header-title">
                  {activeReview.isPendingReview
                    ? "Active Session — Pending 20:00 WIB Review"
                    : (isHistorical ? "Historical Session Audit" : "Latest Session Verdict")}
                </div>
                <div className="eval-header-right">
                  {isHistorical && (
                    <button
                      className="jump-latest-btn font-mono"
                      onClick={() => setSelectedDate(null)}
                    >
                      ← Latest ({formatHeaderDate(dashboard.latest?.date)})
                    </button>
                  )}
                  <div className="eval-date-badge font-mono">{formatHeaderDate(activeReview.date)}</div>
                </div>
              </header>

              {/* 4-Column Variance Bridge */}
              <div className="variance-bridge-grid">
                <div className="bridge-cell">
                  <div className="bridge-cell-header font-mono">06:55 PRE-MARKET CALL</div>
                  <div className="bridge-cell-body">
                    <DirectionBadge direction={activeReview.ihsg_predicted} />
                    {activeReview.ihsg_confidence && (
                      <span className="confidence-pill font-mono">{activeReview.ihsg_confidence}% Conf</span>
                    )}
                  </div>
                  <div className="bridge-cell-sub">
                    Exp. Flow: <span className="text-secondary font-medium font-mono">{formatFlowLabel(activeReview.foreign_flow_predicted)}</span>
                  </div>
                </div>

                <div className="bridge-cell">
                  <div className="bridge-cell-header font-mono">16:00 IDX CLOSE</div>
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
                      {activeReview.isPendingReview ? "Pending Close" : formatFlowLabel(activeReview.foreign_flow_actual)}
                    </span>
                  </div>
                </div>

                <div className="bridge-cell">
                  <div className="bridge-cell-header font-mono">SESSION RETURN</div>
                  <div className="bridge-cell-body">
                    {activeReview.isPendingReview ? (
                      <span className="font-mono text-xs text-muted">Awaiting Close</span>
                    ) : (
                      <>
                        <span className={`font-mono text-base font-bold ${isUp ? "text-matched" : "text-missed"}`}>
                          {formatPct(activeReview.ihsg_actual_pct)}
                        </span>
                        <span className="font-mono text-xs text-muted">
                          ({Math.round(Number(activeReview.ihsg_actual_pct || 0) * 100)} bps)
                        </span>
                      </>
                    )}
                  </div>
                  <div className="bridge-cell-sub">
                    <span className={`font-mono ${activeReview.isPendingReview ? "text-muted" : (isMatched ? "text-matched font-medium" : "text-missed font-medium")}`}>
                      {activeReview.isPendingReview ? "Session Active" : (isMatched ? "Direction Aligned" : "Direction Diverged")}
                    </span>
                  </div>
                </div>

                <div className="bridge-cell" style={{ borderRight: "none" }}>
                  <div className="bridge-cell-header font-mono">VERDICT</div>
                  <div className="bridge-cell-body">
                    <StatusBadge correct={isMatched} isPending={activeReview.isPendingReview} />
                  </div>
                  <div className="bridge-cell-sub">
                    Score: <span className="text-primary font-bold font-mono">
                      {activeReview.isPendingReview ? "Pending" : `${formatNumber(activeReview.accuracy_score)}%`}
                    </span>
                  </div>
                </div>
              </div>

              {/* Twin Workbench Panes */}
              <div className="eval-body">
                <div className="eval-pane">
                  <div className="eval-pane-header">
                    <div className="eval-pane-header-left">
                      <span className="eval-pane-title">Session Summary &amp; Signals</span>
                    </div>
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
                          fontSize: "11px"
                        }}
                        onClick={() => handleOpenBriefModal(activeReview.date)}
                      >
                        Full Morning Brief →
                      </button>
                    )}
                  </div>

                  <div className="eval-pane-body" style={{ padding: 0 }}>
                    <div className="eval-pane-section">
                      {activeReview.premarket_summary && !activeReview.isPendingReview && (
                        <div style={{ marginBottom: "8px", padding: "8px 12px", background: "var(--surface-subtle)", borderRadius: "4px", borderLeft: "3px solid var(--accent-cyan)" }}>
                          <div className="font-mono text-xs" style={{ color: "var(--accent-cyan)", fontWeight: 600, marginBottom: "2px" }}>
                            06:55 PRE-MARKET THESIS
                          </div>
                          <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                            <RenderWithSources text={cleanNarrative(activeReview.premarket_summary)} sources={activeReview.sources} />
                          </div>
                        </div>
                      )}
                      <div className="font-mono text-xs" style={{ color: "var(--text-tertiary)", fontWeight: 600, marginBottom: "4px" }}>
                        {activeReview.isPendingReview ? "06:55 PRE-MARKET THESIS" : "20:00 POST-MARKET AUDIT"}
                      </div>
                      <p className="eval-summary-text" style={{ margin: 0 }}>
                        <RenderWithSources text={cleanNarrative(activeReview.summary)} sources={activeReview.sources} />
                        {!activeReview.summary && "No summary logged."}
                      </p>
                      {activeReview.key_risk && (
                        <div style={{ marginTop: "8px", padding: "8px 12px", background: "var(--surface-hover)", borderRadius: "4px", borderLeft: "3px solid var(--missed-text)" }}>
                          <div className="font-mono text-xs" style={{ color: "var(--missed-text)", fontWeight: 600, marginBottom: "2px" }}>KEY RISK</div>
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
          )}

          {/* Paginated Historical Ledger */}
          <section className="history-section">
            <header className="history-header">
              <div>
                <h2 className="history-title">Session History ({dashboard.reviews.length})</h2>
              </div>
              <div className="filter-tabs">
                <button
                  className={`filter-tab-btn font-mono ${filter === "all" ? "active" : ""}`}
                  onClick={() => { setFilter("all"); setHistoryPage(1); }}
                >
                  All ({dashboard.reviews.length})
                </button>
                <button
                  className={`filter-tab-btn font-mono ${filter === "matched" ? "active" : ""}`}
                  onClick={() => { setFilter("matched"); setHistoryPage(1); }}
                >
                  Hit ({dashboard.wins})
                </button>
                <button
                  className={`filter-tab-btn font-mono ${filter === "missed" ? "active" : ""}`}
                  onClick={() => { setFilter("missed"); setHistoryPage(1); }}
                >
                  Miss ({dashboard.evaluatedCount - dashboard.wins})
                </button>
              </div>
            </header>
            <div className="table-wrapper desktop-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Call (06:55)</th>
                    <th>Close (16:00)</th>
                    <th>Return</th>
                    <th>Foreign Flow</th>
                    <th>Sectors (Scorable)</th>
                    <th>Score</th>
                    <th>Verdict</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedReviews.map((review) => (
                    <HistoryRow
                      key={review.date}
                      review={review}
                      isSelected={activeReview?.date === review.date}
                      onSelectSession={(d) => setSelectedDate(d)}
                    />
                  ))}
                  {paginatedReviews.length === 0 && (
                    <tr>
                      <td colSpan="8" className="text-muted" style={{ textAlign: "center", padding: "24px 0" }}>
                        No sessions match the selected filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="mobile-cards-list">
              {paginatedReviews.map((review) => (
                <div
                  key={review.date}
                  className={`mobile-history-card ${activeReview?.date === review.date ? "selected-session" : ""}`}
                  onClick={() => setSelectedDate(review.date)}
                >
                  <div className="mobile-card-top">
                    <span className="font-mono text-xs font-bold">{formatHeaderDate(review.date)}</span>
                    <StatusBadge correct={review.ihsg_correct} isPending={review.isPendingReview} size="sm" />
                  </div>
                  <div className="mobile-card-comparison">
                    <div className="mobile-card-col">
                      <span className="mobile-card-label font-mono">CALL:</span>
                      <DirectionBadge direction={review.ihsg_predicted} />
                      {review.ihsg_confidence && <span className="font-mono text-xs text-muted">({review.ihsg_confidence}%)</span>}
                    </div>
                    <div className="mobile-card-arrow">──►</div>
                    <div className="mobile-card-col">
                      <span className="mobile-card-label font-mono">ACTUAL:</span>
                      <DirectionBadge direction={review.isPendingReview ? "PENDING" : review.ihsg_actual} />
                      {!review.isPendingReview && (
                        <span className={`font-mono text-xs font-semibold ${Number(review.ihsg_actual_pct) >= 0 ? "text-matched" : "text-missed"}`}>
                          {formatPct(review.ihsg_actual_pct)}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="mobile-card-bottom font-mono text-xs">
                    <span>Flow: {formatFlowLabel(review.foreign_flow_actual)}</span>
                    <span>Score: {formatNumber(review.accuracy_score)}%</span>
                  </div>
                </div>
              ))}
              {paginatedReviews.length === 0 && (
                <div className="font-mono text-xs text-muted text-center py-4">
                  No sessions match the selected filter.
                </div>
              )}
            </div>

            {filteredReviews.length > HISTORY_PAGE_SIZE && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 16px",
                  borderTop: "1px solid var(--border-subtle)",
                  background: "var(--surface-subtle)",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span className="font-mono text-xs text-secondary">
                  Showing {(safeHistoryPage - 1) * HISTORY_PAGE_SIZE + 1}–{Math.min(safeHistoryPage * HISTORY_PAGE_SIZE, filteredReviews.length)} of {filteredReviews.length} sessions
                </span>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <button
                    type="button"
                    className="filter-tab-btn font-mono"
                    disabled={safeHistoryPage <= 1}
                    onClick={() => setHistoryPage((p) => Math.max(1, p - 1))}
                    style={{ opacity: safeHistoryPage <= 1 ? 0.45 : 1, cursor: safeHistoryPage <= 1 ? "default" : "pointer" }}
                  >
                    ← Prev
                  </button>
                  <span className="font-mono text-xs text-primary" style={{ padding: "0 8px" }}>
                    Page {safeHistoryPage} of {totalHistoryPages}
                  </span>
                  <button
                    type="button"
                    className="filter-tab-btn font-mono"
                    disabled={safeHistoryPage >= totalHistoryPages}
                    onClick={() => setHistoryPage((p) => Math.min(totalHistoryPages, p + 1))}
                    style={{ opacity: safeHistoryPage >= totalHistoryPages ? 0.45 : 1, cursor: safeHistoryPage >= totalHistoryPages ? "default" : "pointer" }}
                  >
                    Next →
                  </button>
                </div>
              </div>
            )}
          </section>
        </div>
        )}

        {currentView === "lessons" && (
          <LessonsDatabaseView theme={theme} toggleTheme={toggleTheme} />
        )}

        {currentView === "telemetry" && (
          <ExecutionTelemetryView theme={theme} toggleTheme={toggleTheme} />
        )}
      </main>

      <SideSheet
        isOpen={briefModalOpen}
        onClose={() => setBriefModalOpen(false)}
        title={`Morning Brief — ${activeReview?.date}`}
        subtitle="Pre-Market Intelligence Document (06:55 WIB)"
        tag="Markdown"
        maxWidth="760px"
      >
        {briefLoading ? (
          <div style={{ padding: "32px", textAlign: "center", color: "var(--text-secondary)", fontFamily: "monospace" }}>
            Loading morning brief...
          </div>
        ) : (
          <article className="markdown-document-body" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "13px", padding: "16px 20px" }}>
            <RenderWithSources text={briefMarkdown} sources={briefSources} />
          </article>
        )}
      </SideSheet>

      <SideSheet
        isOpen={pipelineStatusOpen}
        onClose={() => setPipelineStatusOpen(false)}
        title="Pipeline Status"
        subtitle="Automated Cloud Cron Cadence & Provenance Health"
        tag="Status"
        maxWidth="720px"
      >
        <PipelineStatusView
          onClose={() => setPipelineStatusOpen(false)}
          stats={data?.stats}
          pipelineHealth={data?.pipelineHealth}
          reviews={dashboard.reviews}
        />
      </SideSheet>

      <SideSheet
        isOpen={lineageOpen}
        onClose={() => setLineageOpen(false)}
        title="Data Lineage & Provenance"
        subtitle="Cryptographic Lock Verification, OHLC Geometry & Source Audit"
        tag="Lineage"
        maxWidth="780px"
      >
        <DataLineageView
          onClose={() => setLineageOpen(false)}
          activeReview={activeReview}
          stats={data?.stats}
        />
      </SideSheet>

      <SideSheet
        isOpen={methodologyOpen}
        onClose={() => setMethodologyOpen(false)}
        title="Methodology & Scoring Guide"
        subtitle="50/30/20 Scoring Engine, Shrinkage Calibration & 5-Stage Hygiene Gate"
        tag="Guide"
        maxWidth="780px"
      >
        <MethodologyView
          onClose={() => setMethodologyOpen(false)}
          historyRescoredAt={data?.stats?.historyRescoredAt}
          nexusStats={data?.nexusStats}
        />
      </SideSheet>

      <KpiDetailModal
        isOpen={Boolean(activeKpiModal)}
        onClose={() => setActiveKpiModal(null)}
        type={activeKpiModal}
        dashboard={dashboard}
        data={data}
        onSelectDate={(date) => {
          setSelectedDate(date);
          setActiveKpiModal(null);
        }}
        onSwitchView={(view) => {
          setCurrentView(view);
          setActiveKpiModal(null);
        }}
      />
    </div>
  );
}
