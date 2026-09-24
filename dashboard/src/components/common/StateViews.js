'use client';

export function LoadingSkeleton({ message = 'Loading institutional telemetry feeds...' }) {
  return (
    <div className="state-container state-loading">
      <div className="skeleton-pulse-dot" />
      <span className="font-mono text-sm text-muted">{message}</span>
    </div>
  );
}

export function EmptyState({ title = 'No Data Available', message = 'No records match the current criteria or pipeline run.', actionText, onAction }) {
  return (
    <div className="state-container state-empty">
      <div className="state-icon font-mono">∅</div>
      <div className="state-title">{title}</div>
      <p className="state-message font-mono text-xs">{message}</p>
      {actionText && onAction && (
        <button className="state-action-btn font-mono" onClick={onAction}>
          {actionText}
        </button>
      )}
    </div>
  );
}

export function ErrorState({ title = 'Pipeline Query Error', message = 'Unable to fetch data from backend service.', onRetry }) {
  return (
    <div className="state-container state-error">
      <div className="state-icon text-missed font-mono">⚠</div>
      <div className="state-title text-missed">{title}</div>
      <p className="state-message font-mono text-xs">{message}</p>
      {onRetry && (
        <button className="state-action-btn state-retry-btn font-mono" onClick={onRetry}>
          ↻ Retry Connection
        </button>
      )}
    </div>
  );
}

export function UnavailableState({ label = 'Unavailable', description = 'Data was not captured or session review is still in progress.' }) {
  return (
    <div className="state-unavailable-inline">
      <span className="state-unavailable-tag font-mono">{label}</span>
      <span className="state-unavailable-desc font-mono text-xs">{description}</span>
    </div>
  );
}
