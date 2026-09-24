'use client';
import { useState } from 'react';
import SideSheet from '../common/SideSheet';
import { LoadingSkeleton, ErrorState, UnavailableState } from '../common/StateViews';

function formatHeaderDate(d) {
  if (!d) return '';
  const parts = d.split('-');
  if (parts.length === 3) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const m = months[parseInt(parts[1], 10) - 1];
    return `${m} ${parts[2]}, ${parts[0]}`;
  }
  return d;
}

export default function MorningBriefEntry({ activeReview }) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [markdown, setMarkdown] = useState(null);
  const [is404, setIs404] = useState(false);

  const sessionDate = activeReview?.date;

  const handleOpenBrief = async () => {
    setIsOpen(true);
    if (!sessionDate) return;
    setLoading(true);
    setError(null);
    setIs404(false);

    try {
      const res = await fetch(`/api/brief/${sessionDate}`);
      if (res.status === 404) {
        setIs404(true);
        setMarkdown(null);
      } else if (!res.ok) {
        throw new Error(`Failed to load brief (HTTP ${res.status})`);
      } else {
        const data = await res.json();
        setMarkdown(data.markdown || '');
      }
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const previewText = activeReview?.summary
    ? activeReview.summary.replace(/\[src_[^\]]+\]/g, '').trim()
    : 'Morning research briefing note compiled by institutional multi-agent pipeline.';

  return (
    <>
      <div className="brief-entry-card">
        <div className="brief-entry-content">
          <div className="brief-entry-meta">
            <span className="brief-entry-tag font-mono">Institutional Briefing</span>
            <span className="brief-entry-date font-mono">{formatHeaderDate(sessionDate)}</span>
          </div>
          <p className="brief-entry-summary">{previewText}</p>
        </div>
        <button 
          className="brief-read-btn font-mono"
          onClick={handleOpenBrief}
        >
          Read Full Brief →
        </button>
      </div>

      <SideSheet
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title={`Morning Brief — ${sessionDate}`}
        subtitle="Autonomous Pre-Market Intelligence Document"
        tag="Markdown Reader"
        maxWidth="720px"
      >
        {loading && <LoadingSkeleton message="Retrieving morning intelligence document from vault..." />}

        {is404 && (
          <UnavailableState 
            label="Brief Unavailable" 
            description={`No morning brief document was generated or recorded for session date ${sessionDate}.`}
          />
        )}

        {error && !is404 && (
          <ErrorState 
            title="Unable to Load Document" 
            message={error} 
            onRetry={handleOpenBrief} 
          />
        )}

        {!loading && !error && !is404 && markdown && (
          <article className="markdown-document-body">
            <pre className="markdown-document-pre font-mono">{markdown}</pre>
          </article>
        )}
      </SideSheet>
    </>
  );
}
