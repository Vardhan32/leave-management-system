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
  UserRound,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { apiError } from "../api/client";
import InlineAlert from "../components/InlineAlert";

const DEPARTMENTS = [
  "Design",
  "Engineering",
  "Finance",
  "Marketing",
  "Operations",
  "People Ops",
  "Sales",
];

const EMPTY_FORM = {
  name: "",
  email: "",
  password: "",
  department: "",
  job_title: "",
};

const STARTING_BALANCES = [
  { name: "Casual", days: 12, tone: "coral" },
  { name: "Sick", days: 10, tone: "sage" },
  { name: "Earned", days: 15, tone: "gold" },
];

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function update(field) {
    return (event) => {
      setForm({ ...form, [field]: event.target.value });
      if (errors[field]) setErrors({ ...errors, [field]: undefined });
    };
  }

  function validate() {
    const next = {};
    if (!form.name.trim()) next.name = "Tell us your full name.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) {
      next.email = "Enter a valid work email.";
    }
    if (form.password.length < 8) {
      next.password = "Use at least 8 characters.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!validate()) return;

    setSubmitting(true);
    try {
      await register({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        department: form.department.trim() || null,
        job_title: form.job_title.trim() || null,
      });
      navigate("/");
    } catch (requestError) {
      const parsed = apiError(requestError);
      setError(parsed.message);
      setErrors(parsed.errors);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-shell">
      <aside className="auth-aside auth-aside--register">
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
          <span className="eyebrow eyebrow--light">Your first day, sorted</span>
          <h1>A fresh start, with the boring bits handled.</h1>
          <p>
            Create an account and your leave balances are ready before your
            first cup of chai. No setup calls, no shared spreadsheets.
          </p>
          <ul className="auth-list">
            <li>
              <Check size={15} /> Three leave types, configured for you
            </li>
            <li>
              <Check size={15} /> Weekends never count against your balance
            </li>
            <li>
              <Check size={15} /> A clean audit trail for every decision
            </li>
          </ul>
        </div>

        <div className="starting-card">
          <header>
            <span>Your starting balance</span>
            <span className="starting-card__year">
              {new Date().getFullYear()}
            </span>
          </header>
          {STARTING_BALANCES.map((item) => (
            <div className="starting-row" key={item.name}>
              <span className={`starting-row__dot starting-row__dot--${item.tone}`} />
              <span>{item.name} leave</span>
              <span className="starting-row__days">{item.days} days</span>
            </div>
          ))}
          <p>Ready to use from day one.</p>
        </div>

        <span className="auth-aside__foot">LeaveDesk · Built for small teams</span>
      </aside>

      <main className="auth-panel auth-panel--register">
        <div className="auth-form">
          <header className="auth-form__head">
            <span className="eyebrow">Create your account</span>
            <h2>Join your team on LeaveDesk</h2>
            <p>Two minutes now, fewer email threads later.</p>
          </header>

          {error && <InlineAlert tone="error">{error}</InlineAlert>}

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-grid">
              <label className={`field ${errors.name ? "field--invalid" : ""}`}>
                <span className="field__label">Full name</span>
                <span className="input-wrap">
                  <UserRound size={17} className="input-wrap__icon" />
                  <input
                    type="text"
                    value={form.name}
                    onChange={update("name")}
                    placeholder="Ananya Rao"
                    autoComplete="name"
                  />
                </span>
                {errors.name && <span className="field__error">{errors.name}</span>}
              </label>

              <label className={`field ${errors.email ? "field--invalid" : ""}`}>
                <span className="field__label">Work email</span>
                <span className="input-wrap">
                  <Mail size={17} className="input-wrap__icon" />
                  <input
                    type="email"
                    value={form.email}
                    onChange={update("email")}
                    placeholder="you@company.in"
                    autoComplete="email"
                  />
                </span>
                {errors.email && <span className="field__error">{errors.email}</span>}
              </label>

              <label
                className={`field field--span-2 ${errors.password ? "field--invalid" : ""}`}
              >
                <span className="field__label">Password</span>
                <span className="input-wrap">
                  <Lock size={17} className="input-wrap__icon" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={form.password}
                    onChange={update("password")}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
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
                {errors.password ? (
                  <span className="field__error">{errors.password}</span>
                ) : (
                  <span className="field__hint">
                    Use at least 8 characters. You can change it later.
                  </span>
                )}
              </label>

              <label className="field">
                <span className="field__label">Department</span>
                <span className="input-wrap">
                  <input
                    type="text"
                    list="departments"
                    value={form.department}
                    onChange={update("department")}
                    placeholder="Design"
                  />
                </span>
                <datalist id="departments">
                  {DEPARTMENTS.map((department) => (
                    <option key={department} value={department} />
                  ))}
                </datalist>
              </label>

              <label className="field">
                <span className="field__label">Job title</span>
                <span className="input-wrap">
                  <input
                    type="text"
                    value={form.job_title}
                    onChange={update("job_title")}
                    placeholder="Product Designer"
                  />
                </span>
              </label>
            </div>

            <button
              type="submit"
              className="btn btn--primary btn--block"
              disabled={submitting}
            >
              {submitting ? "Creating account…" : "Create account"}
              {!submitting && <ArrowRight size={17} />}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
