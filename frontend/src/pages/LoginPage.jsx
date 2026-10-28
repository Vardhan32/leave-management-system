import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  Lock,
  Mail,
  Palmtree,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { apiError } from "../api/client";
import Avatar from "../components/Avatar";
import InlineAlert from "../components/InlineAlert";

const DEMO = {
  employee: { email: "demo@leavedesk.in", password: "demo1234" },
  admin: { email: "admin@leavedesk.in", password: "admin1234" },
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (event) => setForm({ ...form, [field]: event.target.value });
  }

  function fillDemo(account) {
    setForm(DEMO[account]);
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(form.email.trim(), form.password);
      navigate("/");
    } catch (requestError) {
      setError(apiError(requestError).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <aside className="auth-aside">
        <span className="auth-aside__orb auth-aside__orb--one" />
        <span className="auth-aside__orb auth-aside__orb--two" />

        <Link className="brand brand--light" to="/">
          <span className="brand__mark">
            <Palmtree size={20} strokeWidth={2.2} />
          </span>
          <span className="brand__name">
            Leave<span>Desk</span>
          </span>
        </Link>

        <div className="auth-aside__copy">
          <span className="eyebrow eyebrow--light">
            People ops, minus the spreadsheets
          </span>
          <h1>Time off, without the paperwork.</h1>
          <p>
            LeaveDesk gives every employee a clear view of their balance and
            gives managers one calm place to approve time away.
          </p>
          <ul className="auth-list">
            <li>
              <Check size={15} /> Live balances for casual, sick, and earned leave
            </li>
            <li>
              <Check size={15} /> Approvals with context, not email threads
            </li>
            <li>
              <Check size={15} /> A team view that respects weekends
            </li>
          </ul>
        </div>

        <div className="away-card">
          <header>
            <span className="away-card__title">Out of office today</span>
            <span className="away-card__count">2 away</span>
          </header>
          <div className="away-card__people">
            <div className="away-person">
              <Avatar name="Isha Verma" size="sm" />
              <div>
                <strong>Isha Verma</strong>
                <span>Design · back Thursday</span>
              </div>
            </div>
            <div className="away-person">
              <Avatar name="Priya Deshpande" size="sm" />
              <div>
                <strong>Priya Deshpande</strong>
                <span>Marketing · back tomorrow</span>
              </div>
            </div>
          </div>
        </div>

        <span className="auth-aside__foot">LeaveDesk · Built for small teams</span>
      </aside>

      <main className="auth-panel">
        <div className="auth-form">
          <header className="auth-form__head">
            <span className="eyebrow">Welcome back</span>
            <h2>Sign in to LeaveDesk</h2>
            <p>Pick up where you left off with your team's time off.</p>
          </header>

          {error && <InlineAlert tone="error">{error}</InlineAlert>}

          <form onSubmit={handleSubmit} noValidate>
            <label className="field">
              <span className="field__label">Work email</span>
              <span className="input-wrap">
                <Mail size={17} className="input-wrap__icon" />
                <input
                  type="email"
                  value={form.email}
                  onChange={update("email")}
                  placeholder="you@company.in"
                  autoComplete="email"
                  required
                />
              </span>
            </label>

            <label className="field">
              <span className="field__label">Password</span>
              <span className="input-wrap">
                <Lock size={17} className="input-wrap__icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  value={form.password}
                  onChange={update("password")}
                  placeholder="At least 8 characters"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  className="input-wrap__action"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </span>
            </label>

            <button
              type="submit"
              className="btn btn--primary btn--block"
              disabled={submitting}
            >
              {submitting ? "Signing in…" : "Sign in"}
              {!submitting && <ArrowRight size={17} />}
            </button>
          </form>

          <div className="demo-box">
            <div className="demo-box__copy">
              <strong>Just exploring?</strong>
              <span>Load one of the seeded accounts.</span>
            </div>
            <div className="demo-box__actions">
              <button
                type="button"
                className="btn btn--soft btn--sm"
                onClick={() => fillDemo("employee")}
              >
                Employee
              </button>
              <button
                type="button"
                className="btn btn--soft btn--sm"
                onClick={() => fillDemo("admin")}
              >
                HR admin
              </button>
            </div>
          </div>

          <p className="auth-switch">
            New to LeaveDesk? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
