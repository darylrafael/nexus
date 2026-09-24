'use client';
import { useState, useEffect } from 'react';
import PipelineHealth from './PipelineHealth';
import AgentBreakdownTable from './AgentBreakdownTable';
import ExecutionLedger from './ExecutionLedger';
import { LoadingSkeleton, ErrorState, EmptyState } from '../common/StateViews';

export default function ExecutionTelemetry() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchTelemetry = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/telemetry');
      if (!res.ok) throw new Error(`Failed to load telemetry store (HTTP ${res.status})`);
      const json = await res.json();
      if (!json.success) throw new Error(json.error || 'Failed to parse telemetry feed');
      setData(json);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  if (loading) {
    return <LoadingSkeleton message="Querying SQLite session database and execution metrics..." />;
  }

  if (error) {
    return <ErrorState title="Telemetry Database Error" message={error} onRetry={fetchTelemetry} />;
  }

  if (!data || !data.isAvailable) {
    return (
      <EmptyState
        title="SQLite Store Unavailable"
        message="The SQLite session ledger (nexus_sessions.db) is not accessible or has not logged any runs yet."
        actionText="Retry Connection"
        onAction={fetchTelemetry}
      />
    );
  }

  return (
    <div className="tab-pane-root">
      <div className="section-eyebrow font-mono">01 · PIPELINE RELIABILITY &amp; HEALTH OVERVIEW</div>
      <PipelineHealth stats={data.stats} />

      <div className="section-eyebrow font-mono" style={{ marginTop: '28px' }}>
        02 · DETERMINISTIC AGENT PERFORMANCE
      </div>
      <AgentBreakdownTable breakdown={data.agentBreakdown} />

      <div className="section-eyebrow font-mono" style={{ marginTop: '28px' }}>
        03 · TRANSACTIONAL EXECUTION AUDIT
      </div>
      <ExecutionLedger sessions={data.sessions} />
    </div>
  );
}
