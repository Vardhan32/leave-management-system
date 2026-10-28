export default function ProgressBar({ used = 0, total = 0, tone = "coral" }) {
  const percent = total > 0 ? Math.min(Math.round((used / total) * 100), 100) : 0;
  return (
    <div
      className={`progress progress--${tone}`}
      role="progressbar"
      aria-valuenow={used}
      aria-valuemin={0}
      aria-valuemax={total}
      aria-label={`${used} of ${total} days used`}
    >
      <span className="progress__fill" style={{ width: `${percent}%` }} />
    </div>
  );
}
