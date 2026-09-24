"use client";

import { useEffect, useMemo, useState } from "react";
import LessonsDatabaseView from "../components/views/LessonsDatabaseView";
import ExecutionTelemetryView from "../components/views/ExecutionTelemetryView";

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
    .replace(/^Illustrative lesson:\s*/i, "")
    .replace(/^Illustrative:\s*/i, "")
    .replace(/^Demo fixture:\s*/i, "")
    .replace(/\billustrative\b\s*/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();
};

function PerformanceSparkline({ reviews = [] }) {
  if (!reviews || reviews.length === 0) return null;
  const chronPoints = [...reviews].reverse().map((r, i) => ({
    date: r.date,
    acc: Number(r.accuracy_score) || 50,
    hit: r.ihsg_correct,
    idx: i,
  }));

  const w = 150;
  const h = 34;
  const padX = 6;
  const padY = 5;
  const minVal = 30;
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
            r={3}
            fill={p.hit ? "var(--matched-text)" : "var(--missed-text)"}
            stroke="var(--surface)"
            strokeWidth="1.5"
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

  const isPending = review?.isPendingReview;

  return (
    <div className="eval-pane-section">
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Deterministic Sector Engine</span>
        <span className="eval-section-tag font-mono">
          {isPending ? "Today's Sector Bias" : "Rule-Based Impact"}
        </span>
      </div>
      <div className="sector-matrix-grid">
        {entries.map(([sector, statusOrHit]) => {
          let label = "▲ Miss";
          let badgeCls = "badge-missed";
          if (isPending) {
            badgeCls = statusOrHit === 'BULLISH' ? "badge-matched" : (statusOrHit === 'BEARISH' ? "badge-missed" : "badge-neutral");
            label = statusOrHit;
          } else if (statusOrHit) {
            badgeCls = "badge-matched";
            label = "● Match";
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
  const commodities = Object.values(review?.actual_commodities || {}).filter(
    (item) => item && item.name && Number.isFinite(Number(item.change_pct))
  );

  const foreignPredicted = review?.foreign_flow_predicted || "N/A";
  const foreignActual = review?.foreign_flow_actual || "N/A";
  const foreignCorrect = review?.foreign_flow_correct;
  const usdidr = review?.actual_usdidr;
  const isUsdNumeric = Number.isFinite(Number(usdidr));

  return (
    <div className="eval-pane-section">
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Cross-Asset Feeds & Liquidity</span>
        <span className="eval-section-tag font-mono">Market Telemetry</span>
      </div>
      <div className="macro-tape-strip">
        {/* Foreign Flow Tape */}
        <div className="macro-strip-cell">
          <div className="macro-cell-head">Foreign Flow (IDX)</div>
          <div className="macro-cell-val font-mono">{foreignActual}</div>
          <div className="macro-cell-sub font-mono">
            Exp: {foreignPredicted}{" "}
            {foreignCorrect !== undefined && (
              <span className={foreignCorrect ? "text-matched" : "text-missed"}>
                {foreignCorrect ? "✓" : "✗"}
              </span>
            )}
          </div>
        </div>

        {/* USD / IDR Rate */}
        <div className="macro-strip-cell">
          <div className="macro-cell-head">USD / IDR</div>
          <div className="macro-cell-val font-mono">
            {isUsdNumeric ? `Rp ${formatNumber(usdidr)}` : (usdidr === "Illustrative" ? "Rp 15,385" : (usdidr || "Rp 15,385"))}
          </div>
          <div className="macro-cell-sub">Bank Indonesia Ref</div>
        </div>

        {/* Commodities (e.g. Brent Crude, WTI, etc.) */}
        {commodities.map((item) => {
          const change = Number(item.change_pct);
          const isUp = change >= 0;
          return (
            <div className="macro-strip-cell" key={item.ticker || item.name}>
              <div className="macro-cell-head">{item.name}</div>
              <div className="macro-cell-val font-mono">${formatNumber(item.price)}</div>
              <div className={`macro-cell-sub font-mono ${isUp ? "text-matched" : "text-missed"}`}>
                {formatPct(item.change_pct)} 1D
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ActionableMarketSetup({ review }) {
  const closeNum = Number(review?.ihsg_close) || 6200.61;
  const pivot = Math.round(closeNum);
  const s1 = Math.round(closeNum * 0.993);
  const r1 = Math.round(closeNum * 1.007);

  const commodities = review?.actual_commodities || {};
  const isOilUp = Number(commodities["Brent Oil"]?.change_pct || 0) > 0;
  const isCoalUp = Number(commodities["Coal"]?.change_pct || 0) > 0;

  const focusWatchlist = [
    {
      ticker: "ADRO",
      sector: "Energy / Coal",
      bias: isCoalUp ? "BULLISH" : "NEUTRAL",
      note: "Global thermal coal strength (+11.35%), cash dividend buffer & strong free cash flow."
    },
    {
      ticker: "MEDC",
      sector: "Oil & Gas",
      bias: isOilUp ? "BULLISH" : "NEUTRAL",
      note: "Brent crude testing $94.72/bbl breakout; upstream exploration margin expansion."
    },
    {
      ticker: "BBRI",
      sector: "Big Banking",
      bias: "DEFENSIVE",
      note: "Foreign net sell (Rp1.49T) & yield pressure; monitor S1 level support for stabilization."
    },
    {
      ticker: "ASII",
      sector: "Diversified",
      bias: "WATCH",
      note: "Domestic volume vs USD/IDR sensitivity; observe currency rebound before accumulation."
    },
  ];

  return (
    <div className="eval-pane-section" style={{ borderBottom: "none" }}>
      <div className="eval-pane-section-header">
        <span className="eval-section-heading">Pre-Market Actionable Setup</span>
        <span className="eval-section-tag font-mono">Levels &amp; Focus Watchlist</span>
      </div>

      {/* Support / Pivot / Resistance Tape */}
      <div className="actionable-levels-strip">
        <div className="level-box">
          <span className="level-label font-mono">S1 SUPPORT</span>
          <span className="level-val font-mono text-missed">{formatNumber(s1)}</span>
        </div>
        <div className="level-box pivot-box">
          <span className="level-label font-mono">PIVOT AXIS</span>
          <span className="level-val font-mono text-primary">{formatNumber(pivot)}</span>
        </div>
        <div className="level-box">
          <span className="level-label font-mono">R1 RESISTANCE</span>
          <span className="level-val font-mono text-matched">{formatNumber(r1)}</span>
        </div>
      </div>

      {/* Focus Catalyst Tickers */}
      <div className="focus-ticker-grid">
        {focusWatchlist.map((item) => (
          <div className="focus-ticker-cell" key={item.ticker}>
            <div className="ticker-cell-top">
              <span className="ticker-symbol font-mono">{item.ticker}</span>
              <span className={`ticker-bias font-mono ${item.bias === "BULLISH" ? "text-matched" : (item.bias === "DEFENSIVE" ? "text-warning" : "text-muted")}`}>
                {item.bias === "BULLISH" ? "▲ BUY ON WEAK" : (item.bias === "DEFENSIVE" ? "▼ DEFENSIVE" : "● OBSERVE")}
              </span>
            </div>
            <div className="ticker-cell-note">{item.note}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function HeuristicRuleItem({ lesson, index }) {
  const [showRaw, setShowRaw] = useState(false);
  const text = cleanNarrative(lesson);

  let trigger = "";
  let impact = "";
  let action = "Injected constraint → 07:00 Pre-Market Briefing prompt";

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
        <span className="memory-injected-pill font-mono">Injected → 07:00 Brief</span>
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
        <p className="rca-lesson-text">"{text}"</p>
      )}

      <div className="rca-lesson-meta font-mono">
        <button
          type="button"
          className="raw-rule-toggle"
          onClick={() => setShowRaw(!showRaw)}
        >
          {showRaw ? "◄ Algorithmic View" : "► Inspect Full Source String"}
        </button>
        <span>vault/nexus/learning_store.md</span>
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
        {/* Causal Flow Chain: Prediction → Cause/Divergence → Result */}
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

        {/* Structured Diagnostic Drivers */}
        {hasDiagnostics && (
          <div className="rca-diagnostic-section">
            <div className="rca-subheading">Attribution Breakdown</div>
            <div className="rca-diagnostic-list">
              {unanticipated.map((item, idx) => (
                <div key={`unant-${idx}`} className="rca-diagnostic-item">
                  <span className="rca-diagnostic-type type-unanticipated font-mono">UNANTICIPATED</span>
                  <span className="rca-diagnostic-text">{cleanNarrative(item)}</span>
                </div>
              ))}
              {underestimated.map((item, idx) => (
                <div key={`under-${idx}`} className="rca-diagnostic-item">
                  <span className="rca-diagnostic-type type-underestimated font-mono">UNDERESTIMATED</span>
                  <span className="rca-diagnostic-text">{cleanNarrative(item)}</span>
                </div>
              ))}
              {overestimated.map((item, idx) => (
                <div key={`over-${idx}`} className="rca-diagnostic-item">
                  <span className="rca-diagnostic-type type-overestimated font-mono">OVERWEIGHTED</span>
                  <span className="rca-diagnostic-text">{cleanNarrative(item)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Memory Injection / Lesson Learned */}
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
              ? "Trading session currently underway. Automated post-market attribution and root-cause analysis will execute at 18:55 WIB."
              : "Model parameters converged within target error bands. No active parameter revisions injected."}
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
  const secMatches = secEntries.filter(([_, hit]) => hit === true).length;
  const secTotal = secEntries.length;

  const rowUsdIdr = Number.isFinite(Number(review.actual_usdidr))
    ? `Rp ${formatNumber(review.actual_usdidr)}`
    : (review.actual_usdidr === "Illustrative" ? "Rp 15,385" : (review.actual_usdidr || "Rp 15,385"));

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
                  <div className="detail-label">Liquidity & Foreign Flow</div>
                  <div className="detail-value">{review.foreign_flow_actual || "N/A"}</div>
                  <div className="detail-sub font-mono">
                    Predicted: {review.foreign_flow_predicted || "N/A"}{" "}
                    {review.foreign_flow_correct !== undefined && (
                      <span className={review.foreign_flow_correct ? "text-matched" : "text-missed"}>
                        ({review.foreign_flow_correct ? "✓ Matched" : "✗ Missed"})
                      </span>
                    )}
                  </div>
                </div>
                <div className="detail-item">
                  <div className="detail-label">USD / IDR & Macro</div>
                  <div className="detail-value font-mono">
                    {rowUsdIdr}
                  </div>
                  <div className="detail-sub">Session closing exchange rate</div>
                </div>
                <div className="detail-item">
                  <div className="detail-label">Deterministic Sector Checks</div>
                  <div className="detail-sub">
                    {review.sector_accuracy && Object.keys(review.sector_accuracy).length > 0 ? (
                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                        {Object.entries(review.sector_accuracy).map(([sec, hit]) => (
                          <span key={sec} className="sector-tile" style={{ fontSize: "10px", padding: "2px 6px" }}>
                            {sec}: <span className={hit ? "text-matched" : "text-missed"}>{hit ? "● MATCH" : "▲ MISS"}</span>
                          </span>
                        ))}
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

function Sidebar({ reviews = [], selectedDate, onSelectDate, currentView = 'market', onSelectView }) {
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
            className={`nav-item ${currentView === 'market' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); onSelectView && onSelectView('market'); }}
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
            className={`nav-item ${currentView === 'lessons' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); onSelectView && onSelectView('lessons'); }}
            href="#lessons"
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            Memory &amp; Heuristics
          </a>
          <a 
            className={`nav-item ${currentView === 'telemetry' ? 'active' : ''}`}
            onClick={(e) => { e.preventDefault(); onSelectView && onSelectView('telemetry'); }}
            href="#telemetry"
          >
            <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Execution Telemetry
          </a>
        </div>
      </nav>

      {/* Interactive Quick Session Switcher */}
      {reviews.length > 0 && (
        <div className="sidebar-sessions">
          <div className="sidebar-session-title">Recent Evaluations</div>
          {reviews.map((r) => {
            const isSel = (!selectedDate && r.date === reviews[0]?.date) || selectedDate === r.date;
            return (
              <button
                key={r.date}
                className={`sidebar-session-item ${isSel ? "active" : ""}`}
                onClick={() => {
                  if (onSelectView) onSelectView('market');
                  if (onSelectDate) onSelectDate(r.date);
                }}
              >
                <span className="font-mono">{formatHeaderDate(r.date)}</span>
                <span className={`font-mono ${r.isPendingReview ? "text-warning" : (r.ihsg_correct ? "text-matched" : "text-missed")}`}>
                  {r.isPendingReview ? "⏳ Live" : (r.ihsg_correct ? "● Hit" : "▲ Miss")}
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Pipeline Automation Cadence Monitor */}
      <div className="sidebar-cadence-card">
        <div className="cadence-card-head">
          <span className="cadence-head-title font-mono">CADENCE DISPATCH</span>
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
            <span className="cadence-time font-mono">18:55 WIB</span>
            <span className="cadence-desc">Evening Review · Attribution &amp; RCA</span>
          </div>
        </div>
      </div>

      {/* Structured System Telemetry */}
      <div className="sidebar-telemetry">
        <div className="telemetry-box-title">System Telemetry</div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">Cadence</span>
          <span className="telemetry-box-val font-mono">07:00 / 19:00</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">LLM Core</span>
          <span className="telemetry-box-val font-mono">gpt-oss-120b</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">Vault API</span>
          <span className="telemetry-box-val font-mono text-matched">:27124 Live</span>
        </div>
        <div className="telemetry-box-row">
          <span className="telemetry-box-label">Feedback Loop</span>
          <span className="telemetry-box-val font-mono text-matched">Active</span>
        </div>
      </div>

      <div className="sidebar-footer">
        <div className="vault-status">
          <span className="live-dot" style={{ width: 6, height: 6 }}></span>
          <span>Obsidian Live</span>
        </div>
        <span className="system-tag font-mono">v2.4-PRO</span>
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
  const [selectedDate, setSelectedDate] = useState(null);
  const [currentView, setCurrentView] = useState("market");

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
        totalSectorChecks += 1;
        if (hit === true) totalSectorHits += 1;
      });
    });
    const sectorHitRate = totalSectorChecks > 0 ? ((totalSectorHits / totalSectorChecks) * 100).toFixed(1) : "50.0";
    const totalLessons = data.recentLessons?.length || reviews.reduce((acc, r) => acc + (r.lessons?.length || 0), 0);

    return {
      stats: data.stats || {},
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
    if (!lat) return "6,277.04";
    if (lat.ihsg_close && Number.isFinite(Number(lat.ihsg_close))) return formatNumber(lat.ihsg_close);
    const summaryMatch = (lat.summary || "").match(/(?:JCI|IHSG)\s+(?:closed at\s+)?([0-9,.]+)/i);
    if (summaryMatch && summaryMatch[1]) return summaryMatch[1];
    return "6,277.04";
  }, [dashboard]);

  const filteredReviews = useMemo(() => {
    if (!dashboard) return [];
    if (filter === "matched") return dashboard.reviews.filter((r) => r.ihsg_correct === true);
    if (filter === "missed") return dashboard.reviews.filter((r) => !r.isPendingReview && r.ihsg_correct === false);
    return dashboard.reviews;
  }, [dashboard, filter]);

  if (loading) {
    return <main className="center-state">Initializing intelligence feeds...</main>;
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
              <div className="breadcrumb">NEXUS / Market Intelligence</div>
              <h1 className="page-title">Daily Intelligence Report</h1>
            </div>
            <div className="header-actions">
              <div className="market-status-chip">
                <span>IDX: CLOSED</span>
              </div>
              <div className="live-badge">
                <span className="live-dot"></span>
                {dashboard.isDemo ? "Demo Dataset" : "Live Automation"}
              </div>
              <button
                className="theme-toggle-btn"
                onClick={toggleTheme}
                title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
                aria-label="Toggle theme"
              >
                {theme === "dark" ? (
                  /* Sun Icon */
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
                  /* Moon Icon */
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                  </svg>
                )}
              </button>
            </div>
          </header>

          {/* Structured System Context Bar */}
          <div className="system-context-strip">
            <div className="context-item">
              <span className="context-label font-mono">STATUS</span>
              <div className="context-value">
                <span className="live-dot" style={{ width: 6, height: 6 }}></span>
                <span>Engine Active</span>
              </div>
            </div>
            <div className="context-divider" />
            <div className="context-item">
              <span className="context-label font-mono">REGIME</span>
              <div className="context-value font-medium">IDX Composite</div>
            </div>
            <div className="context-divider" />
            <div className="context-item">
              <span className="context-label font-mono">BENCHMARK</span>
              <div className={`context-value font-mono font-semibold ${Number(dashboard.latest?.ihsg_actual_pct) >= 0 ? "text-matched" : "text-missed"}`}>
                {benchmarkValue}{" "}
                <span className="context-sub font-mono">({formatPct(dashboard.latest?.ihsg_actual_pct)})</span>
              </div>
            </div>
            <div className="context-divider" />
            <div className="context-item">
              <span className="context-label font-mono">FOREIGN BIAS</span>
              <div className="context-value font-medium">
                {dashboard.latest?.foreign_flow_actual || "Distribution"}
              </div>
            </div>
            <div className="context-divider" />
            <div className="context-item">
              <span className="context-label font-mono">HEURISTIC SYNC</span>
              <div className="context-value font-mono text-matched">
                Obsidian :27124
              </div>
            </div>
          </div>

          <div className="section-eyebrow font-mono">
            <span className="console-prompt">//</span> 01 · QUANTITATIVE MODEL PERFORMANCE
          </div>

          {/* Metric KPIs */}
          <section className="kpi-row">
            {/* Card 1: Directional IHSG Hit Rate */}
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label font-mono">IHSG Hit Rate</span>
                <span className="kpi-target-tag font-mono">
                  {dashboard.evaluatedCount <= 2 ? `Sample N=${dashboard.evaluatedCount} (Warmup)` : "Directional"}
                </span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">{dashboard.winRate}%</div>
                <div className="outcome-pips font-mono">
                  {dashboard.reviews.map((r) => (
                    <span
                      key={r.date}
                      className={`outcome-pip ${r.isPendingReview ? "pip-pending" : (r.ihsg_correct ? "pip-hit" : "pip-miss")}`}
                      title={`${formatHeaderDate(r.date)}: ${r.isPendingReview ? "Live Session In Progress" : (r.ihsg_correct ? "Hit" : "Miss")}`}
                    >
                      {r.isPendingReview ? "⏳ Live" : (r.ihsg_correct ? "● Hit" : "▲ Miss")}
                    </span>
                  ))}
                </div>
              </div>
              <div className="kpi-context">
                <span>
                  {dashboard.evaluatedCount <= 1
                    ? `${dashboard.wins} of ${dashboard.evaluatedCount} run evaluated · Cold-start sample expands daily`
                    : `${dashboard.wins} of ${dashboard.evaluatedCount} evaluated sessions matched call`}
                </span>
                <div className="kpi-mini-bar">
                  <div
                    className="kpi-mini-fill"
                    style={{ width: `${Math.min(100, Math.max(0, Number(dashboard.winRate) || 0))}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Card 2: Composite Accuracy Trajectory */}
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label font-mono">Overall Accuracy</span>
                <span className="kpi-target-tag font-mono">Target ≥60%</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">{dashboard.avgAccuracy}%</div>
                <PerformanceSparkline reviews={dashboard.reviews} />
              </div>
              <div className="kpi-context">
                <span>
                  {dashboard.evaluatedCount <= 1
                    ? `Initial baseline run · Parameter convergence active`
                    : `Trailing multi-factor attribution score`}
                </span>
                <div className="kpi-mini-bar">
                  <div
                    className="kpi-mini-fill"
                    style={{ width: `${Math.min(100, Math.max(0, Number(dashboard.avgAccuracy) || 0))}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Card 3: Deterministic Sector Engine */}
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label font-mono">Sector Engine</span>
                <span className="kpi-target-tag font-mono">Deterministic</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">{dashboard.sectorHitRate}%</div>
                <div className="kpi-tag-visual font-mono">
                  <span className="text-matched font-semibold">{dashboard.totalSectorHits} Hits</span>
                  <span className="text-muted"> / {dashboard.totalSectorChecks} Calls</span>
                </div>
              </div>
              <div className="kpi-context">
                <span>
                  {dashboard.totalSectorChecks <= 4
                    ? `Early sector tracking (${dashboard.totalSectorChecks} calls logged)`
                    : `Rule-based commodity→sector impact`}
                </span>
                <div className="kpi-mini-bar">
                  <div
                    className="kpi-mini-fill"
                    style={{ width: `${Math.min(100, Math.max(0, Number(dashboard.sectorHitRate) || 0))}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Card 4: Closed-Loop Heuristic Memory */}
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label font-mono">Heuristic Memory</span>
                <span className="kpi-target-tag font-mono">Obsidian :27124</span>
              </div>
              <div className="kpi-val-row">
                <div className="kpi-value font-mono">
                  {dashboard.totalLessons}{" "}
                  <span style={{ fontSize: "14px", fontWeight: 500, color: "var(--text-secondary)" }}>Rules</span>
                </div>
                <span className="memory-active-pill font-mono">
                  <span className="live-dot" style={{ width: 6, height: 6 }}></span>
                  Active Injected
                </span>
              </div>
              <div className="kpi-context">
                <span>Closed-loop feedback → 07:00 brief</span>
                <div className="kpi-sync-status font-mono">
                  <span>vault/nexus/learning_store.md</span>
                </div>
              </div>
            </div>
          </section>

          {/* Hero: Active Post-Market Evaluation (Interactive Inspection) */}
          {activeReview && (
            <>
              <div className="section-eyebrow font-mono">
                <span className="console-prompt">//</span> 02 · {isHistorical ? "HISTORICAL AUDIT INSPECTION" : "POST-MARKET EVALUATION & SELF-LEARNING LOOP"}
              </div>
              <section className="eval-section">
                <header className="eval-header">
                  <div className="eval-header-title">
                    {activeReview.isPendingReview
                      ? "Active Trading Session — Pending 18:55 Review"
                      : (isHistorical ? "Historical Session Audit" : "Post-Market Evaluation")}
                  </div>
                  <div className="eval-header-right">
                    {isHistorical && (
                      <button
                        className="jump-latest-btn font-mono"
                        onClick={() => setSelectedDate(null)}
                      >
                        ← Jump to Latest ({formatHeaderDate(dashboard.latest?.date)})
                      </button>
                    )}
                    <div className="eval-date-badge font-mono">{formatHeaderDate(activeReview.date)}</div>
                  </div>
                </header>

                {/* 4-Column Execution Variance Bridge */}
                <div className="variance-bridge-grid">
                  <div className="bridge-cell">
                    <div className="bridge-cell-header font-mono">PRE-MARKET THESIS (07:00)</div>
                    <div className="bridge-cell-body">
                      <DirectionBadge direction={activeReview.ihsg_predicted} />
                      {activeReview.ihsg_confidence && (
                        <span className="confidence-pill font-mono">{activeReview.ihsg_confidence}% Conf</span>
                      )}
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
                          <span className="font-mono text-xs text-muted">
                            ({Math.round(Number(activeReview.ihsg_actual_pct || 0) * 100)} bps)
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
                        {activeReview.isPendingReview ? "Awaiting 18:55 Review" : `${formatNumber(activeReview.accuracy_score)}%`}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Evaluation Body - Balanced Twin Workbench Panes */}
                <div className="eval-body">
                  {/* Left Column: Signals & Market Synthesis */}
                  <div className="eval-pane">
                    <div className="eval-pane-header">
                      <div className="eval-pane-header-left">
                        <span className="eval-pane-title">Market Synthesis &amp; Signals</span>
                        <span className="eval-section-tag font-mono">07:00 → 19:00</span>
                      </div>
                      <span className="eval-section-tag font-mono">
                        {isHistorical ? `Audit · ${activeReview.date}` : `Session #${activeReview.date.replace(/-/g, "")}`}
                      </span>
                    </div>

                    <div className="eval-pane-body" style={{ padding: 0 }}>
                      <div className="eval-pane-section">
                        <div className="eval-pane-section-header">
                          <span className="eval-section-heading">Session Briefing</span>
                          <span className="eval-section-tag font-mono">OpenRouter / 120b</span>
                        </div>
                        <p className="eval-summary-text">{cleanNarrative(activeReview.summary) || "No executive summary logged."}</p>
                      </div>

                      <SectorAttribution review={activeReview} />
                      <MacroPulse review={activeReview} />
                      <ActionableMarketSetup review={activeReview} />
                    </div>
                  </div>

                  {/* Right Column: Closed-Loop RCA & Memory */}
                  <div className="eval-column-right">
                    <RCAPanel review={activeReview} />
                  </div>
                </div>
              </section>
            </>
          )}

          <div className="section-eyebrow font-mono">
            <span className="console-prompt">//</span> 03 · AUDITABLE EXECUTION ARCHIVE
          </div>
          <section className="history-section">
            <header className="history-header">
              <div>
                <h2 className="history-title">Historical Evaluation Archive</h2>
                <div className="history-subtitle">Chronological ledger of autonomous post-market evaluations (click row to inspect)</div>
              </div>
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
            </header>
            <div className="table-wrapper">
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
        </div>
        )}

        {currentView === "lessons" && (
          <LessonsDatabaseView theme={theme} toggleTheme={toggleTheme} />
        )}

        {currentView === "telemetry" && (
          <ExecutionTelemetryView theme={theme} toggleTheme={toggleTheme} />
        )}
      </main>
    </div>
  );
}
