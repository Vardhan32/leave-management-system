const LABELS = {
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export default function StatusBadge({ status, withDot = true }) {
  return (
    <span className={`status status--${status}`}>
      {withDot && <span className="status__dot" aria-hidden="true" />}
      {LABELS[status] || status}
    </span>
  );
}
