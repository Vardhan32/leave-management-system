import { Link } from "react-router-dom";
import { ArrowLeft, Palmtree } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export default function NotFoundPage() {
  const { user } = useAuth();

  return (
    <main className="not-found">
      <div className="not-found__mark">
        <Palmtree size={30} />
      </div>
      <span className="eyebrow">404 · Page not found</span>
      <h1>This page took a leave day.</h1>
      <p>
        The link may be old, or the page may have moved. It should be back at
        its desk tomorrow.
      </p>
      <div className="not-found__actions">
        <Link to={user ? "/" : "/login"} className="btn btn--primary">
          <ArrowLeft size={16} />
          {user ? "Back to dashboard" : "Back to sign in"}
        </Link>
        {!user && (
          <Link to="/register" className="btn btn--ghost">
            Create an account
          </Link>
        )}
      </div>
      <span className="not-found__foot">LeaveDesk</span>
    </main>
  );
}
