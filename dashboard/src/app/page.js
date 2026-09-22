"use client";

import { useEffect, useMemo, useState } from "react";

const formatPct = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0.0%";
  return `${num > 0 ? "+" : ""}${num.toFixed(1)}%`;
};

const formatNumber = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return "N/A";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(num);
};

function StatusBadge({ correct }) {
  return (
    <span className={`status-badge ${correct ? "is-win" : "is-loss"}`}>
      {correct ? "Matched" : "Missed"}
    </span>
  );
}

function MetricCard({ label, value, detail, tone = "neutral" }) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}

function DataRow({ review }) {
  const [expanded, setExpanded] = useState(false);
  const rcaCount = [
    review.rca_unanticipated,
    review.rca_overestimated,
    review.rca_underestimated,
    review.rca_info_delay,
    review.rca_inverse_correlation,
  ].reduce((sum, item) => sum + (Array.isArray(item) ? item.length : 0), 0);

  return (
    <article className={`outcome-row ${review.ihsg_correct ? "is-win" : "is-loss"}`}>
      <button
        className="outcome-summary"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
      >
        <span className="outcome-date">{review.date}</span>
        <span className="outcome-market">
          <strong>{review.ihsg_actual}</strong>
          <span>{formatPct(review.ihsg_actual_pct)}</span>
        </span>
        <span className="outcome-prediction">
          Predicted {review.ihsg_predicted || "N/A"}
        </span>
        <StatusBadge correct={review.ihsg_correct} />
        <span className="chevron" aria-hidden="true" />
      </button>

      {expanded && (
        <div className="outcome-detail">
          <p>{review.summary || "No review summary was captured for this session."}</p>

          <div className="detail-grid">
            <div>
              <span className="field-label">Foreign flow</span>
              <strong>{review.foreign_flow_actual || "N/A"}</strong>
              <small>Predicted {review.foreign_flow_predicted || "N/A"}</small>
            </div>
            <div>
              <span className="field-label">USD/IDR</span>
              <strong>{formatNumber(review.actual_usdidr)}</strong>
              <small>Closing snapshot</small>
            </div>
            <div>
              <span className="field-label">Accuracy</span>
              <strong>{formatNumber(review.accuracy_score)}%</strong>
              <small>{rcaCount} RCA points logged</small>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

function LessonItem({ lesson }) {
  return (
    <article className="lesson-item">
      <time>{lesson.date}</time>
      <p>{lesson.text}</p>
    </article>
  );
}

function CommodityTape({ review }) {
  const commodities = Object.values(review?.actual_commodities || {}).filter(
    (item) => item && item.name && Number.isFinite(Number(item.change_pct))
  );

  if (commodities.length === 0) {
    return (
      <div className="commodity-empty">
        Commodity tape will populate after the next evening review.
      </div>
    );
  }

  return (
    <div className="commodity-tape">
      {commodities.map((item) => {
        const isUp = Number(item.change_pct) >= 0;
        return (
          <div className="commodity-pill" key={item.ticker || item.name}>
            <span>{item.name}</span>
            <strong>{formatNumber(item.price)}</strong>
            <em className={isUp ? "is-up" : "is-down"}>{formatPct(item.change_pct)}</em>
          </div>
        );
      })}
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
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

  const dashboard = useMemo(() => {
    if (!data) return null;

    const reviews = data.reviews || [];
    const latest = reviews[0];
    const wins = reviews.filter((review) => review.ihsg_correct).length;
    const winRate = reviews.length ? ((wins / reviews.length) * 100).toFixed(1) : "0.0";
    const avgAccuracy = Number(data.stats?.avgAccuracy || 0).toFixed(1);
    const latestTone = latest?.ihsg_correct ? "positive" : "negative";

    return {
      stats: data.stats || {},
      reviews,
      latest,
      latestTone,
      lessons: data.recentLessons || [],
      avgAccuracy,
      winRate,
      wins,
    };
  }, [data]);

  if (loading) {
    return (
      <main className="center-state">
        <div className="loading-mark" />
        <p>Loading Nexus dashboard</p>
      </main>
    );
  }

  if (error || !dashboard) {
    return (
      <main className="center-state">
        <p className="error-copy">{error || "Unable to load dashboard data."}</p>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Nexus IHSG intelligence</p>
          <h1>Market Review Console</h1>
        </div>
        <div className="session-chip">
          <span />
          Weekday automation live
        </div>
      </header>

      <section className="overview-grid" aria-label="Performance overview">
        <MetricCard
          label="Average Accuracy"
          value={`${dashboard.avgAccuracy}%`}
          detail={`${dashboard.stats.totalDays || 0} reviewed market days`}
          tone="positive"
        />
        <MetricCard
          label="IHSG Hit Rate"
          value={`${dashboard.winRate}%`}
          detail={`${dashboard.wins} matched directional calls`}
          tone={dashboard.wins ? "positive" : "neutral"}
        />
        <MetricCard
          label="Pipeline Runs"
          value={dashboard.stats.totalRuns || 0}
          detail="Briefs, reviews, and checks executed"
        />
      </section>

      <section className="workbench">
        <article className={`latest-panel ${dashboard.latestTone}`}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Latest review</p>
              <h2>{dashboard.latest?.date || "No review yet"}</h2>
            </div>
            {dashboard.latest && <StatusBadge correct={dashboard.latest.ihsg_correct} />}
          </div>

          {dashboard.latest ? (
            <>
              <div className="latest-callout">
                <div>
                  <span>IHSG actual</span>
                  <strong>{dashboard.latest.ihsg_actual}</strong>
                  <small>{formatPct(dashboard.latest.ihsg_actual_pct)}</small>
                </div>
                <div>
                  <span>Forecast</span>
                  <strong>{dashboard.latest.ihsg_predicted}</strong>
                  <small>{dashboard.latest.ihsg_confidence || 0}% confidence</small>
                </div>
              </div>
              <p className="latest-summary">{dashboard.latest.summary}</p>
              <CommodityTape review={dashboard.latest} />
            </>
          ) : (
            <p className="latest-summary">The first evening review will appear here once it is generated.</p>
          )}
        </article>

        <aside className="lessons-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Self correction</p>
              <h2>Lessons</h2>
            </div>
            <span className="count-pill">{dashboard.lessons.length}</span>
          </div>
          <div className="lesson-list">
            {dashboard.lessons.length > 0 ? (
              dashboard.lessons.map((lesson, index) => <LessonItem key={`${lesson.date}-${index}`} lesson={lesson} />)
            ) : (
              <p className="muted-copy">No corrective lessons logged yet.</p>
            )}
          </div>
        </aside>
      </section>

      <section className="history-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Prediction history</p>
            <h2>Daily Outcomes</h2>
          </div>
          <span className="count-pill">{dashboard.reviews.length}</span>
        </div>
        <div className="outcome-list">
          {dashboard.reviews.length > 0 ? (
            dashboard.reviews.map((review) => <DataRow key={review.date} review={review} />)
          ) : (
            <p className="muted-copy">No evening reviews available.</p>
          )}
        </div>
      </section>
    </main>
  );
}
