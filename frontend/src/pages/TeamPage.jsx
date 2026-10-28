import { useEffect, useState } from "react";
import {
  CalendarClock,
  ClipboardCheck,
  Palmtree,
  Search,
  Users,
  X,
} from "lucide-react";
import api, { apiError } from "../api/client";
import Avatar from "../components/Avatar";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import PageLoader from "../components/PageLoader";
import {
  formatDate,
  formatRange,
  pluralize,
  shortLeaveType,
} from "../utils/format";

const BALANCE_TONES = {
  CASUAL: "coral",
  SICK: "sage",
  EARNED: "gold",
};

export default function TeamPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [department, setDepartment] = useState("all");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    api
      .get("/team")
      .then(({ data: body }) => {
        if (!cancelled) setData(body);
      })
      .catch((requestError) => {
        if (!cancelled) setError(apiError(requestError).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [revision]);

  if (loading) {
    return (
      <div className="page">
        <PageLoader label="Gathering the team…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <ErrorState
          message={error}
          onRetry={() => setRevision((current) => current + 1)}
        />
      </div>
    );
  }

  const totalPending = data.items.reduce(
    (sum, employee) => sum + employee.pending_requests,
    0
  );
  const awayToday = data.items.filter(
    (employee) => employee.on_leave_today
  ).length;
  const term = search.trim().toLowerCase();
  const filtered = data.items.filter((employee) => {
    const haystack = [
      employee.name,
      employee.email,
      employee.job_title,
      employee.department,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch = !term || haystack.includes(term);
    const matchesDepartment =
      department === "all" || employee.department === department;
    return matchesSearch && matchesDepartment;
  });

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">People ops</span>
          <h1>Team directory</h1>
          <p>
            Leave balances and availability for {pluralize(data.count, "person", "people")}{" "}
            across {pluralize(data.departments.length, "department")}.
          </p>
        </div>
      </header>

      <section className="team-summary" aria-label="Team summary">
        <div className="team-summary__item">
          <span className="team-summary__icon team-summary__icon--ink">
            <Users size={18} />
          </span>
          <div>
            <strong>{data.count}</strong>
            <span>People</span>
          </div>
        </div>
        <div className="team-summary__item">
          <span className="team-summary__icon team-summary__icon--sage">
            <Palmtree size={18} />
          </span>
          <div>
            <strong>{awayToday}</strong>
            <span>Away today</span>
          </div>
        </div>
        <div className="team-summary__item">
          <span className="team-summary__icon team-summary__icon--coral">
            <ClipboardCheck size={18} />
          </span>
          <div>
            <strong>{totalPending}</strong>
            <span>Pending requests</span>
          </div>
        </div>
        <div className="team-summary__item">
          <span className="team-summary__icon team-summary__icon--gold">
            <CalendarClock size={18} />
          </span>
          <div>
            <strong>{data.departments.length}</strong>
            <span>Departments</span>
          </div>
        </div>
      </section>

      <div className="team-toolbar">
        <label className="search-field search-field--wide">
          <Search size={16} />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by name, role, or email"
            aria-label="Search the team"
          />
          {search && (
            <button
              type="button"
              className="search-field__clear"
              onClick={() => setSearch("")}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </label>

        <div className="filter-tabs filter-tabs--scroll" role="tablist" aria-label="Filter by department">
          <button
            type="button"
            role="tab"
            aria-selected={department === "all"}
            className={`filter-tab ${department === "all" ? "is-active" : ""}`}
            onClick={() => setDepartment("all")}
          >
            All departments
          </button>
          {data.departments.map((name) => (
            <button
              type="button"
              key={name}
              role="tab"
              aria-selected={department === name}
              className={`filter-tab ${department === name ? "is-active" : ""}`}
              onClick={() => setDepartment(name)}
            >
              {name}
            </button>
          ))}
        </div>
      </div>

      {filtered.length ? (
        <div className="team-grid">
          {filtered.map((employee) => (
            <article className="team-card" key={employee.id}>
              <header className="team-card__head">
                <Avatar name={employee.name} size="lg" />
                <div className="team-card__identity">
                  <h2>{employee.name}</h2>
                  <p>{employee.job_title || "Team member"}</p>
                </div>
                <span
                  className={`availability ${
                    employee.on_leave_today ? "availability--away" : ""
                  }`}
                >
                  {employee.on_leave_today ? "Away today" : "Available"}
                </span>
              </header>

              <div className="team-card__meta">
                <span className="dept-pill">
                  {employee.department || "Unassigned"}
                </span>
                <span>Joined {formatDate(employee.joined_on)}</span>
              </div>

              <div className="team-balances">
                {employee.balances.map((balance) => {
                  const tone =
                    BALANCE_TONES[balance.leave_type.code] || "coral";
                  const percent =
                    balance.allocated_days > 0
                      ? Math.min(
                          Math.round(
                            (balance.used_days / balance.allocated_days) * 100
                          ),
                          100
                        )
                      : 0;
                  return (
                    <div
                      className={`team-balance team-balance--${tone}`}
                      key={balance.id}
                    >
                      <div className="team-balance__head">
                        <span>{shortLeaveType(balance.leave_type.name)}</span>
                        <strong>
                          {balance.remaining_days}
                          <small>/{balance.allocated_days}</small>
                        </strong>
                      </div>
                      <div className="micro-bar">
                        <span style={{ width: `${percent}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              <footer className="team-card__foot">
                <div>
                  <span>Pending</span>
                  <strong>{employee.pending_requests}</strong>
                </div>
                <div>
                  <span>Approved</span>
                  <strong>{pluralize(employee.approved_days, "day")}</strong>
                </div>
                <div className="team-card__next">
                  <span>Next leave</span>
                  <strong>
                    {employee.next_leave
                      ? formatRange(
                          employee.next_leave.start_date,
                          employee.next_leave.end_date
                        )
                      : "None booked"}
                  </strong>
                </div>
              </footer>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Users}
          title="No one matches that"
          description="Try a different name or department, or clear the filters."
          action={
            <button
              type="button"
              className="btn btn--soft btn--sm"
              onClick={() => {
                setSearch("");
                setDepartment("all");
              }}
            >
              Clear filters
            </button>
          }
        />
      )}
    </div>
  );
}
