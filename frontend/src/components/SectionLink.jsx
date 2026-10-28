import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function SectionLink({ to, children }) {
  return (
    <Link className="section-link" to={to}>
      {children}
      <ArrowRight size={14} />
    </Link>
  );
}
