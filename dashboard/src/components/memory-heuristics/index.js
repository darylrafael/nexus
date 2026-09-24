'use client';
import { useState, useEffect } from 'react';
import MemoryKPIs from './MemoryKPIs';
import BlindSpotMatrix from './BlindSpotMatrix';
import HeuristicList from './HeuristicList';
import { LoadingSkeleton, ErrorState, EmptyState } from '../common/StateViews';

export default function MemoryHeuristics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMemory = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/memory');
      if (!res.ok) throw new Error(`Failed to load memory vault (HTTP ${res.status})`);
      const json = await res.json();
      if (!json.success) throw new Error(json.error || 'Failed to parse memory feed');
      setData(json);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, []);

  if (loading) {
    return <LoadingSkeleton message="Retrieving knowledge heuristics and blind spots from vault..." />;
  }

  if (error) {
    return <ErrorState title="Memory Vault Error" message={error} onRetry={fetchMemory} />;
  }

  if (!data || (data.heuristics?.length === 0 && data.blindSpots?.length === 0)) {
    return (
      <EmptyState
        title="Memory Store Empty"
        message="No reflective heuristics or blind spots have been stored in the vault yet."
        actionText="Refresh Feeds"
        onAction={fetchMemory}
      />
    );
  }

  return (
    <div className="tab-pane-root">
      <div className="section-eyebrow font-mono">01 · AUTONOMOUS REFLECTION &amp; KNOWLEDGE OVERVIEW</div>
      <MemoryKPIs stats={data.stats} />

      <div className="section-eyebrow font-mono" style={{ marginTop: '28px' }}>
        02 · RECURRING MACRO BLIND SPOTS
      </div>
      <BlindSpotMatrix blindSpots={data.blindSpots} />

      <div className="section-eyebrow font-mono" style={{ marginTop: '28px' }}>
        03 · ACTIVE &amp; VALIDATED HEURISTICS VAULT
      </div>
      <HeuristicList heuristics={data.heuristics} />
    </div>
  );
}
