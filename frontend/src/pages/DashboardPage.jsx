import { useCallback, useEffect, useState } from "react";
import {
  CalendarCheck2,
  CalendarDays,
  CalendarPlus,
  ClipboardCheck,
  HeartPulse,
  Palmtree,
  Plane,
  Plus,
  Sun,
  Users,
} from "lucide-react";
import { Link } from "react-router-dom";
import api, { apiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Avatar from "../components/Avatar";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import LeaveTypeTag from "../components/LeaveTypeTag";
import PageLoader from "../components/PageLoader";
import ProgressBar from "../components/ProgressBar";
import SectionLink from "../components/SectionLink";
import StatusBadge from "../components/StatusBadge";
import {
  calendarParts,
  firstName,
  formatDate,
  formatDateTime,
  formatLongDate,
  formatRange,
  greeting,
  pluralize,
  relativeStart,
  shortLeaveType,
  todayISO,
} from "../utils/format";

const BALANCE_STYLES = {
  CASUAL: { icon: Sun, tone: "coral" },
  SICK: { icon: HeartPulse, tone: "sage" },
  EARNED: { icon: Plane, tone: "gold" },
};

function BalanceCard({ balance }) {
  const style = BALANCE_STYLES[balance.leave_type.code] || {
    icon: Palmtree,
    tone: "coral",
  };
  const Icon = style.icon;

  return (
    <article className={`balance-card balance-card--${style.tone}`}>
      <header className="balance-card__head">
        <span className={`balance-card__icon balance-card__icon--${style.tone}`}>
          <Icon size={18} strokeWidth={2} />
        </span>
        <span className="balance-card__label">
          {shortLeaveType(balance.leave_type.name)} leave
        </span>
        <span className="balance-card__year">{balance.year}</span>
      </header>
      <div className="balance-card__value">
        <strong>{balance.remaining_days}</strong>
        <span>days left</span>
      </div>
      <ProgressBar
        used={balance.used_days}
        total={balance.allocated_days}
        tone={style.tone}
      />
      <footer className="balance-card__meta">
        <span>{balance.used_days} used</span>
        <span>{balance.allocated_days} allocated</span>
      </footer>
    </article>
  );
}

function UpcomingItem({ request }) {
  const parts = calendarParts(request.start_date);
  return (
    <div className="upcoming-item">
      <div className="date-tile">
        <span>{parts.month}</span>
        <strong>{parts.day}</strong>
      </div>
      <div className="upcoming-item__copy">
        <div className="upcoming-item__title">
          <LeaveTypeTag type={request.leave_type} />
          <span>{pluralize(request.days, "day")}</span>
        </div>
        <p>{formatRange(request.start_date, request.end_date)}</p>
        <small>{relativeStart(request.start_date)}</small>
      </div>
      <StatusBadge status={request.status} />
    </div>
  );
}

function EmployeeDashboard({ data }) {
  const { user } = useAuth();
  const stats = data.stats;
  const next = data.upcoming[0];

  return (
    <>
      <section className="hero hero--employee">
        <div className="hero__content">
          <span className="eyebrow eyebrow--light">
            {formatLongDate(todayISO())}
          </span>
          <h1>
            {greeting()}, {firstName(user.name)}.
          </h1>
          <p>
            {stats.on_leave_today
              ? "You're on leave today — switch off and recharge. The team has it covered."
              : next
                ? `Your next break starts ${relativeStart(next.start_date).toLowerCase()} — ${formatRange(next.start_date, next.end_date)}.`
                : "No approved leave on the calendar yet. Your next break is only a few clicks away."}
          </p>
          <div className="hero__actions">
            <Link to="/leave?apply=1" className="btn btn--coral">
              <Plus size={16} />
              Request time off
            </Link>
            <Link to="/leave" className="btn btn--ghost-light">
              View my leave
            </Link>
          </div>
        </div>
        <div className="hero__stat" aria-label={`${stats.remaining_days} leave days remaining`}>
          <span className="hero__stat-label">Days left in {data.year}</span>
          <strong>{stats.remaining_days}</strong>
          <span className="hero__stat-note">across three leave types</span>
          <span className="hero__stat-orbit" aria-hidden="true" />
        </div>
      </section>

      <section className="balance-grid" aria-label="Leave balances">
        {data.balances.map((balance) => (
          <BalanceCard key={balance.id} balance={balance} />
        ))}
      </section>

      <div className="dashboard-columns">
        <section className="panel">
          <header className="panel__head">
            <div>
              <h2>Upcoming time off</h2>
              <p>Approved leave on your calendar.</p>
            </div>
            <SectionLink to="/leave">All requests</SectionLink>
          </header>

          {data.upcoming.length ? (
            <div className="upcoming-list">
              {data.upcoming.map((request) => (
                <UpcomingItem key={request.id} request={request} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={CalendarPlus}
              title="Nothing booked yet"
              description="When a request is approved, it will show up here."
              action={
                <Link to="/leave?apply=1" className="btn btn--soft btn--sm">
                  Plan some time off
                </Link>
              }
            />
          )}
        </section>

        <aside className="panel panel--glance">
          <header className="panel__head">
            <div>
              <h2>This year at a glance</h2>
              <p>Your {data.year} leave snapshot.</p>
            </div>
          </header>
          <div className="glance-stats">
            <div>
              <strong>{stats.pending_requests}</strong>
              <span>Pending</span>
            </div>
            <div>
              <strong>{stats.approved_days}</strong>
              <span>Approved days</span>
            </div>
            <div>
              <strong>{stats.on_leave_today ? "Yes" : "No"}</strong>
              <span>On leave today</span>
            </div>
          </div>
          <div className="glance-note">
            <CalendarDays size={17} />
            <p>
              Your leave year runs from January to December. Balances refresh on
              1 January {data.year + 1}.
            </p>
          </div>
        </aside>
      </div>

      <section className="panel">
        <header className="panel__head">
          <div>
            <h2>Recent requests</h2>
            <p>Your last five submissions, newest first.</p>
          </div>
          <SectionLink to="/leave">View all</SectionLink>
        </header>

        {data.recent_requests.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Leave type</th>
                  <th>Dates</th>
                  <th>Days</th>
                  <th>Status</th>
                  <th>Applied on</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_requests.map((request) => (
                  <tr key={request.id}>
                    <td>
                      <LeaveTypeTag type={request.leave_type} />
                    </td>
                    <td>{formatRange(request.start_date, request.end_date)}</td>
                    <td>{request.days}</td>
                    <td>
                      <StatusBadge status={request.status} />
                    </td>
                    <td className="cell-muted">
                      {formatDate(request.created_at?.slice(0, 10))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={CalendarDays}
            title="No requests yet"
            description="Your leave history will appear here once you apply."
          />
        )}
      </section>
    </>
  );
}

function StatCard({ icon: Icon, label, value, note, tone }) {
  return (
    <article className={`stat-card stat-card--${tone}`}>
      <span className="stat-card__icon">
        <Icon size={19} />
      </span>
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
        <small>{note}</small>
      </div>
    </article>
  );
}

function AdminDashboard({ data }) {
  const { user } = useAuth();
  const stats = data.stats;
  const maxHeadcount = Math.max(
    ...data.departments.map((department) => department.headcount),
    1
  );

  return (
    <>
      <section className="hero hero--admin">
        <div className="hero__content">
          <span className="eyebrow eyebrow--light">
            {formatLongDate(todayISO())} · People Ops
          </span>
          <h1>
            {greeting()}, {firstName(user.name)}.
          </h1>
          <p>
            {stats.pending_requests > 0
              ? `${pluralize(stats.pending_requests, "request")} waiting for a decision, and ${pluralize(stats.on_leave_today, "teammate")} away today.`
              : `The approval queue is clear, and ${pluralize(stats.on_leave_today, "teammate")} away today.`}
          </p>
          <div className="hero__actions">
            <Link to="/approvals" className="btn btn--coral">
              <ClipboardCheck size={16} />
              Review requests
            </Link>
            <Link to="/team" className="btn btn--ghost-light">
              Team directory
            </Link>
          </div>
        </div>
        <div className="hero__stat" aria-label={`${stats.pending_requests} pending requests`}>
          <span className="hero__stat-label">Waiting on you</span>
          <strong>{stats.pending_requests}</strong>
          <span className="hero__stat-note">pending approvals</span>
          <span className="hero__stat-orbit" aria-hidden="true" />
        </div>
      </section>

      <section className="stat-grid" aria-label="Company leave summary">
        <StatCard
          icon={Users}
          label="People"
          value={stats.headcount}
          note="Active employees"
          tone="ink"
        />
        <StatCard
          icon={ClipboardCheck}
          label="Pending"
          value={stats.pending_requests}
          note="Awaiting your review"
          tone="coral"
        />
        <StatCard
          icon={Palmtree}
          label="Away today"
          value={stats.on_leave_today}
          note="Across the team"
          tone="sage"
        />
        <StatCard
          icon={CalendarCheck2}
          label="Approved days"
          value={stats.approved_days}
          note={`Booked in ${data.year}`}
          tone="gold"
        />
      </section>

      <div className="dashboard-columns">
        <section className="panel">
          <header className="panel__head">
            <div>
              <h2>Waiting for a decision</h2>
              <p>The oldest requests are at the top.</p>
            </div>
            <SectionLink to="/approvals">Open queue</SectionLink>
          </header>

          {data.pending_requests.length ? (
            <div className="approval-list">
              {data.pending_requests.map((request) => (
                <Link
                  className="approval-row"
                  key={request.id}
                  to="/approvals"
                >
                  <Avatar name={request.employee.name} size="sm" />
                  <div className="approval-row__person">
                    <strong>{request.employee.name}</strong>
                    <span>
                      {request.employee.department || "Unassigned"} ·{" "}
                      {pluralize(request.days, "day")}
                    </span>
                  </div>
                  <div className="approval-row__dates">
                    <LeaveTypeTag type={request.leave_type} />
                    <span>{formatRange(request.start_date, request.end_date)}</span>
                  </div>
                  <span className="approval-row__link">Review</span>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={ClipboardCheck}
              title="All caught up"
              description="There are no pending leave requests right now."
            />
          )}
        </section>

        <aside className="panel">
          <header className="panel__head">
            <div>
              <h2>Out of office today</h2>
              <p>Who's away right now.</p>
            </div>
          </header>

          {data.on_leave.length ? (
            <div className="away-list">
              {data.on_leave.map((request) => (
                <div className="away-row" key={request.id}>
                  <Avatar name={request.employee.name} size="sm" />
                  <div>
                    <strong>{request.employee.name}</strong>
                    <span>
                      {request.employee.department || "Unassigned"} · until{" "}
                      {formatDate(request.end_date)}
                    </span>
                  </div>
                  <LeaveTypeTag type={request.leave_type} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Palmtree}
              title="Everyone's in today"
              description="No approved leave covers today."
            />
          )}

          {data.upcoming.length > 0 && (
            <div className="next-away">
              <span className="next-away__label">Next scheduled</span>
              <div className="next-away__row">
                <Avatar name={data.upcoming[0].employee.name} size="sm" />
                <div>
                  <strong>{data.upcoming[0].employee.name}</strong>
                  <span>
                    from {formatDate(data.upcoming[0].start_date)} ·{" "}
                    {pluralize(data.upcoming[0].days, "day")}
                  </span>
                </div>
              </div>
            </div>
          )}
        </aside>
      </div>

      <div className="dashboard-split">
        <section className="panel">
          <header className="panel__head">
            <div>
              <h2>Headcount by department</h2>
              <p>Where the team sits today.</p>
            </div>
            <SectionLink to="/team">Team directory</SectionLink>
          </header>

          <div className="department-list">
            {data.departments.map((department) => (
              <div className="department-row" key={department.name}>
                <div className="department-row__head">
                  <span>{department.name}</span>
                  <span>{pluralize(department.headcount, "person", "people")}</span>
                </div>
                <div className="department-row__bar">
                  <span
                    style={{
                      width: `${Math.round(
                        (department.headcount / maxHeadcount) * 100
                      )}%`,
                    }}
                  />
                </div>
                <div className="department-row__meta">
                  <span>{department.on_leave} away today</span>
                  <span>{department.pending} pending</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel">
          <header className="panel__head">
            <div>
              <h2>Recent decisions</h2>
              <p>The latest approvals and rejections.</p>
            </div>
            <SectionLink to="/approvals?status=approved">See all</SectionLink>
          </header>

          {data.recent_decisions.length ? (
            <div className="decision-list">
              {data.recent_decisions.map((request) => (
                <div className="decision-row" key={request.id}>
                  <Avatar name={request.employee.name} size="sm" />
                  <div className="decision-row__copy">
                    <div>
                      <strong>{request.employee.name}</strong>
                      <StatusBadge status={request.status} />
                    </div>
                    <span>
                      {shortLeaveType(request.leave_type.name)} leave ·{" "}
                      {formatRange(request.start_date, request.end_date)}
                    </span>
                    {request.review_note && <p>{request.review_note}</p>}
                  </div>
                  <small>{formatDateTime(request.reviewed_at)}</small>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={CalendarCheck2}
              title="No decisions yet"
              description="Approvals and rejections will appear here."
            />
          )}
        </section>
      </div>
    </>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/dashboard");
      setData(response.data);
    } catch (requestError) {
      setError(apiError(requestError).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="page">
        <PageLoader label="Putting your leave in order…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="page dashboard-page">
      {data.role === "admin" ? (
        <AdminDashboard data={data} />
      ) : (
        <EmployeeDashboard data={data} />
      )}
    </div>
  );
}
