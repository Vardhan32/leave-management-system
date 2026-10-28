import { RefreshCw, TriangleAlert } from "lucide-react";

export default function ErrorState({
  message = "Something went wrong.",
  onRetry,
  compact = false,
}) {
  return (
    <div className={`error-state ${compact ? "error-state--compact" : ""}`}>
      <span className="error-state__icon">
        <TriangleAlert size={20} />
      </span>
      <div>
        <h3>We hit a snag</h3>
        <p>{message}</p>
      </div>
      {onRetry && (
        <button type="button" className="btn btn--ghost btn--sm" onClick={onRetry}>
          <RefreshCw size={14} />
          Try again
        </button>
      )}
    </div>
  );
}
