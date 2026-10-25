"use client";

import React, { useEffect } from "react";

function formatPct(val) {
  if (val === null || val === undefined || isNaN(val)) return "0.0%";
  const num = Number(val);
  return `${num > 0 ? "+" : ""}${num.toFixed(2)}%`;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const d = new Date(parts[0], parts[1] - 1, parts[2]);
      return d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
    }
    return dateStr;
  } catch (e) {
    return dateStr;
  }
}

export default function KpiDetailModal({
  isOpen,
  onClose,
  type,
  dashboard,
  data,
  onSelectDate,
  onSwitchView,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !type || !dashboard) return null;

  const nexusStats = data?.nexusStats || data?.stats || {};
  const reviews = dashboard.reviews || [];
  const evaluatedReviews = dashboard.evaluatedReviews || reviews.filter((r) => !r.isPendingReview);

  // Directional metrics
  const bearishSessions = evaluatedReviews.filter((r) => (r.ihsg_predicted || "").toLowerCase().includes("bearish"));
  const bearishHits = bearishSessions.filter((r) => r.ihsg_correct).length;
  const bearishWinRate = bearishSessions.length > 0 ? ((bearishHits / bearishSessions.length) * 100).toFixed(1) : "0.0";

  const bullishSessions = evaluatedReviews.filter((r) => (r.ihsg_predicted || "").toLowerCase().includes("bullish"));
  const bullishHits = bullishSessions.filter((r) => r.ihsg_correct).length;
  const bullishWinRate = bullishSessions.length > 0 ? ((bullishHits / bullishSessions.length) * 100).toFixed(1) : "0.0";

  const neutralSessions = evaluatedReviews.filter((r) => {
    const pred = (r.ihsg_predicted || "").toLowerCase();
    return !pred.includes("bearish") && !pred.includes("bullish");
  });

  // Foreign Flow computed stats
  const ffEvaluated = evaluatedReviews.filter((r) => r.foreign_flow_correct !== undefined && r.foreign_flow_correct !== null);
  const ffHits = ffEvaluated.filter((r) => r.foreign_flow_correct).length;
  const ffMatchRate = ffEvaluated.length > 0 ? ((ffHits / ffEvaluated.length) * 100).toFixed(1) : null;

  // Baselines
  const baselines = nexusStats.baselines || {};
  const alwaysBearishPct = baselines.always_bearish_pct ?? "?";
  const persistencePct = baselines.persistence_pct ?? "?";
  const ciLower = nexusStats?.direction_ci_95?.lower_pct ?? "?";
  const ciUpper = nexusStats?.direction_ci_95?.upper_pct ?? "?";
  const avgStatedConf = nexusStats?.calibration?.average_stated_confidence_pct ?? "?";
  const quarantinedCount = (nexusStats?.rejected_lessons || []).length;

  // Sector aggregated breakdown from genuine review sessions
  const sectorMap = {
    "Energy (Oil, Gas & Coal)": { calls: 0, hits: 0, proxies: "Newcastle Coal, Brent Crude, WTI" },
    "Basic Materials (Metals & Mining)": { calls: 0, hits: 0, proxies: "LME Cash Nickel, Copper, Gold" },
    "Consumer Non-Cyclicals (Agri & CPO)": { calls: 0, hits: 0, proxies: "FCPO Malaysia, Kemendag CPO" },
    "Financials & Banking": { calls: 0, hits: 0, proxies: "BI 7-Day Reverse Repo, USD/IDR, Bond Yield" },
    "Technology & Infrastructure": { calls: 0, hits: 0, proxies: "US 10Y Yield, Global Risk-Off" },
    "Property & Cyclicals": { calls: 0, hits: 0, proxies: "Mortgage Rate, Consumer Confidence" },
  };

  evaluatedReviews.forEach((r) => {
    const secAcc = r.sector_accuracy || {};
    Object.entries(secAcc).forEach(([secName, hit]) => {
      const lower = secName.toLowerCase();
      let targetCat = "Property & Cyclicals";
      if (lower.includes("energy") || lower.includes("coal") || lower.includes("oil") || lower.includes("gas")) {
        targetCat = "Energy (Oil, Gas & Coal)";
      } else if (lower.includes("basic") || lower.includes("metal") || lower.includes("nickel") || lower.includes("mining")) {
        targetCat = "Basic Materials (Metals & Mining)";
      } else if (lower.includes("cpo") || lower.includes("consumer") || lower.includes("agri") || lower.includes("staples")) {
        targetCat = "Consumer Non-Cyclicals (Agri & CPO)";
      } else if (lower.includes("bank") || lower.includes("finan")) {
        targetCat = "Financials & Banking";
      } else if (lower.includes("tech") || lower.includes("infra") || lower.includes("telecom")) {
        targetCat = "Technology & Infrastructure";
      }

      if (hit === true || hit === false) {
        sectorMap[targetCat].calls += 1;
        if (hit === true) sectorMap[targetCat].hits += 1;
      }
    });
  });

  // Dynamic Heuristic rules from nexus_stats
  const dynamicRules = (nexusStats.all_lessons || []).slice(0, 5);

  let title = "";
  let subtitle = "";
  let badgeTag = "";

  if (type === "hit_rate") {
    title = "IHSG Directional Hit Rate";
    subtitle = "Directional Accuracy Breakdown vs Naive Baselines & Confidence Interval";
    badgeTag = "Directional Alpha";
  } else if (type === "accuracy") {
    title = "Multi-Factor Composite Accuracy";
    subtitle = "Attribution Weight Decomposition & Calibration Error Model";
    badgeTag = "Scoring Model";
  } else if (type === "sector") {
    title = "Deterministic Sector Engine";
    subtitle = "Commodity Transmission Rules & Sector Win Rate Matrix";
    badgeTag = "Hardcoded Logic";
  } else if (type === "memory") {
    title = "Heuristic Memory Feedback Loop";
    subtitle = "Closed-Loop RCA Rules Injected into 06:55 WIB Pre-Market Prompt";
    badgeTag = "Synced Artifact Vault";
  }

  return (
    <div className="kpi-modal-overlay" onClick={onClose}>
      <div
        className="kpi-modal-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="kpi-modal-header">
          <div>
            <div className="kpi-modal-title-row">
              <h2 className="kpi-modal-title">{title}</h2>
              <span className="kpi-modal-tag font-mono">{badgeTag}</span>
            </div>
            <p className="kpi-modal-subtitle font-mono">{subtitle}</p>
          </div>
          <button
            type="button"
            className="kpi-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="kpi-modal-body">
          {/* ══════════════════════════════════════════════════════════════════════
              TAB 1: HIT RATE BREAKDOWN
             ══════════════════════════════════════════════════════════════════════ */}
          {type === "hit_rate" && (
            <div className="kpi-modal-content">
              {/* Primary KPI Row */}
              <div className="kpi-modal-kpi-grid">
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">REALIZED HIT RATE</div>
                  <div className="modal-metric-val font-mono text-matched">{dashboard.winRate}%</div>
                  <div className="modal-metric-sub font-mono">
                    {dashboard.wins} of {dashboard.evaluatedCount} evaluated sessions
                  </div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">95% CONFIDENCE INTERVAL</div>
                  <div className="modal-metric-val font-mono">
                    [{ciLower}%, {ciUpper}%]
                  </div>
                  <div className="modal-metric-sub font-mono">Wilson score interval (n = {dashboard.evaluatedCount})</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">ALWAYS BEARISH BASELINE</div>
                  <div className="modal-metric-val font-mono">{alwaysBearishPct}%</div>
                  <div className="modal-metric-sub font-mono">Naive benchmark (downtrend regime)</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">PERSISTENCE BASELINE</div>
                  <div className="modal-metric-val font-mono">{persistencePct}%</div>
                  <div className="modal-metric-sub font-mono">Lag-1 persistence benchmark</div>
                </div>
              </div>

              {/* Directional Split Cards */}
              <div className="kpi-modal-section">
                <div className="modal-section-title font-mono">{"// "}DIRECTIONAL BIAS SPLIT</div>
                <div className="directional-split-grid">
                  <div className="split-box">
                    <div className="split-head">
                      <span className="font-mono text-xs font-semibold" style={{ color: "var(--missed-text)" }}>
                        ▼ BEARISH CALLS
                      </span>
                      <span className="font-mono text-xs font-bold">{bearishWinRate}%</span>
                    </div>
                    <div className="split-bar-track">
                      <div className="split-bar-fill fill-bearish" style={{ width: `${bearishWinRate}%` }}></div>
                    </div>
                    <div className="split-foot font-mono text-xs">
                      {bearishHits} matched of {bearishSessions.length} bearish calls
                    </div>
                  </div>

                  <div className="split-box">
                    <div className="split-head">
                      <span className="font-mono text-xs font-semibold" style={{ color: "var(--matched-text)" }}>
                        ▲ BULLISH CALLS
                      </span>
                      <span className="font-mono text-xs font-bold">{bullishWinRate}%</span>
                    </div>
                    <div className="split-bar-track">
                      <div className="split-bar-fill fill-bullish" style={{ width: `${bullishWinRate}%` }}></div>
                    </div>
                    <div className="split-foot font-mono text-xs">
                      {bullishHits} matched of {bullishSessions.length} bullish calls
                    </div>
                  </div>
                </div>
              </div>

              {/* Institutional Note */}
              <div className="institutional-callout">
                <span className="callout-icon">💡</span>
                <div className="callout-text text-xs">
                  <strong>Quantitative Attribution:</strong> Model menunjukkan akurasi tinggi ({bearishWinRate}%) pada kondisi tren melemah (bearish regime), namun memiliki kecenderungan *lag* pada titik pembalikan arah tajam (*rebound*) akibat sensitivitas berlebih terhadap sentimen inflasi AS.
                </div>
              </div>

              {/* Interactive Sessions List */}
              <div className="kpi-modal-section">
                <div className="modal-section-title font-mono">{"// "}SESSION LOG (CLICK TO INSPECT)</div>
                <div className="modal-sessions-table-wrapper">
                  <table className="modal-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Predicted Call</th>
                        <th>Actual Close</th>
                        <th>Outcome</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reviews.map((r) => {
                        const isHit = r.ihsg_correct;
                        const isUp = Number(r.ihsg_actual_pct) >= 0;
                        return (
                          <tr
                            key={r.date}
                            className="clickable-session-row"
                            onClick={() => onSelectDate && onSelectDate(r.date)}
                            title="Click to view full intelligence brief for this date"
                          >
                            <td className="font-mono font-semibold">{formatDate(r.date)}</td>
                            <td className="font-mono">{r.ihsg_predicted || "Neutral"}</td>
                            <td className="font-mono">
                              {r.isPendingReview ? (
                                <span className="text-secondary">In Progress</span>
                              ) : (
                                <span className={isUp ? "text-matched" : "text-missed"}>
                                  {formatPct(r.ihsg_actual_pct)}
                                </span>
                              )}
                            </td>
                            <td>
                              {r.isPendingReview ? (
                                <span className="outcome-pill pip-pending">Pending</span>
                              ) : isHit ? (
                                <span className="outcome-pill pip-hit">● Hit</span>
                              ) : (
                                <span className="outcome-pill pip-miss">▲ Miss</span>
                              )}
                            </td>
                            <td>
                              <span className="table-jump-btn font-mono">View →</span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 2: ACCURACY & MULTI-FACTOR ENGINE
             ══════════════════════════════════════════════════════════════════════ */}
          {type === "accuracy" && (
            <div className="kpi-modal-content">
              {/* Primary Score Strip */}
              <div className="kpi-modal-kpi-grid">
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">TRAILING ACCURACY</div>
                  <div className="modal-metric-val font-mono">{dashboard.avgAccuracy}%</div>
                  <div className="modal-metric-sub font-mono">Target threshold: ≥60.0%</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">BRIER ERROR SCORE</div>
                  <div className="modal-metric-val font-mono">
                    {nexusStats?.calibration?.brier_score != null ? Number(nexusStats.calibration.brier_score).toFixed(2) : "N/A"}
                  </div>
                  <div className="modal-metric-sub font-mono">Probabilistic error (0.25 = random)</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">SHRINKAGE CONFIDENCE</div>
                  <div className="modal-metric-val font-mono">
                    {nexusStats?.calibration?.calibrated_confidence_pct != null ? `${nexusStats.calibration.calibrated_confidence_pct}%` : "N/A"}
                  </div>
                  <div className="modal-metric-sub font-mono">Calibrated vs Stated ({avgStatedConf}%)</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">EVALUATION SAMPLE</div>
                  <div className="modal-metric-val font-mono">{dashboard.evaluatedCount} Sessions</div>
                  <div className="modal-metric-sub font-mono">Continuous closed-loop evaluation</div>
                </div>
              </div>

              {/* Multi-Factor Weight Matrix */}
              <div className="kpi-modal-section">
                <div className="modal-section-title font-mono">{"// "}3-PILLAR DYNAMIC SCORABLE ATTRIBUTION (50 / 30 / 20)</div>
                <div className="factor-weights-list">
                  <div className="factor-weight-row">
                    <div className="factor-info">
                      <span className="factor-title">1. IHSG Index Direction</span>
                      <span className="factor-desc">Kesesuaian arah penutupan IHSG terhadap pita toleransi &plusmn;0.20% (Bullish / Bearish / Neutral)</span>
                    </div>
                    <div className="factor-stats font-mono">
                      <span className="factor-weight-tag">Bobot 50%</span>
                      <span className="factor-score text-matched">{dashboard.winRate}% Hit</span>
                    </div>
                  </div>

                  <div className="factor-weight-row">
                    <div className="factor-info">
                      <span className="factor-title">2. Deterministic Sector Breakdown</span>
                      <span className="factor-desc">Ketepatan proyeksi sektor terhadap 11 indeks sektoral resmi IDX-IC pada penutupan</span>
                    </div>
                    <div className="factor-stats font-mono">
                      <span className="factor-weight-tag">Bobot 30%</span>
                      <span className="factor-score">{dashboard.sectorHitRate}% Hit</span>
                    </div>
                  </div>

                  <div className="factor-weight-row">
                    <div className="factor-info">
                      <span className="factor-title">3. Verified Foreign Flow Alignment</span>
                      <span className="factor-desc">Deteksi akumulasi (&gt; +Rp1T) vs distribusi (&lt; -Rp1T) pasar reguler berverifikasi tanggal D/M/Y</span>
                    </div>
                    <div className="factor-stats font-mono">
                      <span className="factor-weight-tag">Bobot 20%</span>
                      <span className="factor-score">{ffEvaluated.length >= 5 && ffMatchRate ? `${ffMatchRate}% Match` : `n=${ffEvaluated.length} (Unscored <5)`}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Honest Root Cause Diagnosis */}
              <div className="institutional-callout">
                <span className="callout-icon">i</span>
                <div className="callout-text text-xs">
                  <strong>Evaluasi Kuantitatif Terbuka:</strong> Skor komposit saat ini ({dashboard.avgAccuracy}%) menggunakan normalisasi dinamis hanya pada komponen yang terverifikasi (tanpa mengarang data jika Foreign Flow tidak tersedia). Setiap sesi dievaluasi secara deterministik pada pukul 20:00 WIB tanpa intervensi manual.
                </div>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 3: SECTOR ENGINE & CAUSAL RULES
             ══════════════════════════════════════════════════════════════════════ */}
          {type === "sector" && (
            <div className="kpi-modal-content">
              {/* Primary Stats */}
              <div className="kpi-modal-kpi-grid">
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">AGGREGATE SECTOR ACCURACY</div>
                  <div className="modal-metric-val font-mono">{dashboard.sectorHitRate}%</div>
                  <div className="modal-metric-sub font-mono">
                    {dashboard.totalSectorHits} Hits dari {dashboard.totalSectorChecks} Calls
                  </div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">ENGINE ARCHITECTURE</div>
                  <div className="modal-metric-val font-mono" style={{ fontSize: "16px" }}>
                    Deterministic
                  </div>
                  <div className="modal-metric-sub font-mono">Rule-based, zero LLM hallucination</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">TRACKED SECTORS</div>
                  <div className="modal-metric-val font-mono">11 IDX Sectors</div>
                  <div className="modal-metric-sub font-mono">Energy, Basic, Bank, Tech, Consumer</div>
                </div>
              </div>

              {/* Sector Performance Table */}
              <div className="kpi-modal-section">
                <div className="modal-section-title font-mono">{"// "}SECTOR PERFORMANCE MATRIX</div>
                <div className="modal-sessions-table-wrapper">
                  <table className="modal-table">
                    <thead>
                      <tr>
                        <th>Sector Category</th>
                        <th>Commodity / Macro Proxy</th>
                        <th>Logged Calls</th>
                        <th>Verified Hits</th>
                        <th>Realized Win Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(sectorMap).map(([sectorName, stat]) => {
                        const winPct = stat.calls > 0 ? Math.round((stat.hits / stat.calls) * 100) : 0;
                        return (
                          <tr key={sectorName}>
                            <td className="font-semibold">{sectorName}</td>
                            <td className="font-mono text-xs text-muted">{stat.proxies}</td>
                            <td className="font-mono">{stat.calls > 0 ? stat.calls : "—"}</td>
                            <td className="font-mono">{stat.hits > 0 ? stat.hits : "—"}</td>
                            <td>
                              {stat.calls > 0 ? (
                                <div className="table-acc-bar">
                                  <span className="font-mono text-xs font-semibold">{winPct}%</span>
                                  <div className="acc-track">
                                    <div
                                      className={`acc-fill ${winPct >= 40 ? "fill-green" : "fill-neutral"}`}
                                      style={{ width: `${winPct}%` }}
                                    ></div>
                                  </div>
                                </div>
                              ) : (
                                <span className="font-mono text-xs text-muted">Awaiting Sample</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Deterministic Hardcoded Causal Rules */}
              <div className="kpi-modal-section">
                <div className="modal-section-title font-mono">{"// "}HARDCODED CAUSAL MAPPING RULES</div>
                <div className="causal-rules-grid">
                  <div className="causal-rule-card">
                    <span className="causal-rule-head font-mono">COAL (ICE NEWCASTLE) → IDXENERGY</span>
                    <p className="causal-rule-desc">
                      Harga batubara naik &gt; 1.0% secara deterministik memicu bias Bullish pada saham tambang produsen (ADRO, PTBA, BUMI, BYAN).
                    </p>
                  </div>
                  <div className="causal-rule-card">
                    <span className="causal-rule-head font-mono">BRENT / WTI CRUDE OIL → IDXENERGY</span>
                    <p className="causal-rule-desc">
                      Lonjakan harga minyak mentah diterjemahkan menjadi sentimen defensif produsen migas (MEDC, ENRG, ELSA).
                    </p>
                  </div>
                  <div className="causal-rule-card">
                    <span className="causal-rule-head font-mono">LME CASH NICKEL → IDXBASIC</span>
                    <p className="causal-rule-desc">
                      Pergerakan harga nikel dan tembaga global langsung ditransmisikan ke sektor barang baku (INCO, ANTM, NCKL).
                    </p>
                  </div>
                  <div className="causal-rule-card">
                    <span className="causal-rule-head font-mono">FCPO MALAYSIA → IDXNONCYC</span>
                    <p className="causal-rule-desc">
                      Kenaikan harga CPO global diterjemahkan Bullish untuk perkebunan sawit (AALI, LSIP, TAPG) dan Bearish bagi konsumen CPO (ICBP, INDF).
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════════
              TAB 4: HEURISTIC MEMORY & DYNAMIC RULES
             ══════════════════════════════════════════════════════════════════════ */}
          {type === "memory" && (
            <div className="kpi-modal-content">
              {/* Primary Stats */}
              <div className="kpi-modal-kpi-grid">
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">VALIDATED RULES STORED</div>
                  <div className="modal-metric-val font-mono">{dashboard.totalLessons} Rules</div>
                  <div className="modal-metric-sub font-mono">Passed 5-stage quality gate</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">QUARANTINED LESSONS</div>
                  <div className="modal-metric-val font-mono text-warning" style={{ fontSize: "18px" }}>
                    {quarantinedCount} Rejected
                  </div>
                  <div className="modal-metric-sub font-mono">Blocked sign/numeric/boilerplate errors</div>
                </div>
                <div className="kpi-modal-card">
                  <div className="modal-metric-label font-mono">EXECUTION INJECTION</div>
                  <div className="modal-metric-val font-mono text-matched" style={{ fontSize: "15px" }}>
                    06:55 WIB Daily
                  </div>
                  <div className="modal-metric-sub font-mono">agents/market_agent.py prompt</div>
                </div>
              </div>

              {/* Dynamic Heuristic Rules List */}
              <div className="kpi-modal-section">
                <div className="modal-section-title font-mono">{"// "}SAMPLE VALIDATED CAUSAL RULES (ARTIFACT VAULT)</div>
                <div className="memory-rules-feed">
                  {dynamicRules.length > 0 ? (
                    dynamicRules.map((ruleText, idx) => (
                      <div className="memory-rule-card" key={idx}>
                        <div className="memory-rule-top">
                          <span className="rule-badge font-mono">RULE #{idx + 1}</span>
                          <span className="rule-status font-mono">Active Injected</span>
                        </div>
                        <p className="rule-body-text">{ruleText}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-secondary font-mono text-xs" style={{ padding: "16px", textAlign: "center" }}>
                      Synchronizing with Obsidian Local REST API...
                    </div>
                  )}
                </div>
              </div>

              {/* Direct Link to Lessons Database */}
              <div className="memory-modal-action-box">
                <div>
                  <div className="font-semibold text-sm">Full Lessons &amp; Root Cause Analysis Archive</div>
                  <div className="text-secondary text-xs" style={{ marginTop: "2px" }}>
                    Pelajari seluruh database aturan diagnostik, blind-spot matrix, dan riwayat revisi parameter.
                  </div>
                </div>
                <button
                  type="button"
                  className="open-database-btn font-mono"
                  onClick={() => {
                    if (onSwitchView) onSwitchView("lessons");
                  }}
                >
                  Open Lessons Database →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
