export default function PageLoader({ label = "Loading…" }) {
  return (
    <div className="page-loader" role="status">
      <span className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}
