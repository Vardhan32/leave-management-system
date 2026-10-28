import { useCallback, useEffect, useState } from "react";
import {
  CalendarPlus,
  CalendarX2,
  ChevronLeft,
  ChevronRight,
  Eye,
  HeartPulse,
  Palmtree,
  Plane,
  Plus,
  Sun,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import api, { apiError } from "../api/client";
import ApplyLeaveModal from "../components/ApplyLeaveModal";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import InlineAlert from "../components/InlineAlert";
import LeaveTypeTag from "../components/LeaveTypeTag";
import Modal from "../components/Modal";
import PageLoader from "../components/PageLoader";
import ProgressBar from "../components/ProgressBar";
import RequestDetailModal from "../components/RequestDetailModal";
import StatusBadge from "../components/StatusBadge";
import {
  formatDate,
  formatRange,
  pluralize,
  relativeStart,
  shortLeaveType,
} from "../utils/format";

const BALANCE_STYLES = {
  CASUAL: { icon: Sun, tone: "coral" },
  SICK: { icon: HeartPulse, tone: "sage" },
  EARNED: { icon: Plane, tone: "gold" },
};

const FILTERS = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "cancelled", label: "Cancelled" },
];

const PAGE_SIZE = 6;

export default function MyLeavePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [balances, setBalances] = useState([]);
  const [metaReady, setMetaReady] = useState(false);
  const [metaError, setMetaError] = useState("");

  const [requests, setRequests] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [notice, setNotice] = useState("");

  const [applyOpen, setApplyOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [cancelTarget, setCancelTarget] = useState(null);
  const [cancelError, setCancelError] = useState("");
  const [cancelling, setCancelling] = useState(false);

  const loadMeta = useCallback(async () => {
    setMetaError("");
    try {
      const [typesResponse, balancesResponse] = await Promise.all([
        api.get("/leave-types"),
        api.get("/leave-balances"),
      ]);
      setLeaveTypes(typesResponse.data.leave_types);
      setBalances(balancesResponse.data.balances);
    } catch (requestError) {
      setMetaError(apiError(requestError).message);
    } finally {
      setMetaReady(true);
    }
  }, []);

  const refreshBalances = useCallback(async () => {
    try {
      const { data } = await api.get("/leave-balances");
      setBalances(data.balances);
    } catch {
      // A stale balance strip is harmless; the request list is the source of truth.
    }
  }, []);

  useEffect(() => {
    loadMeta();
  }, [loadMeta]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    api
      .get("/leave-requests", {
        params: {
          page,
          per_page: PAGE_SIZE,
          ...(status === "all" ? {} : { status }),
        },
      })
      .then(({ data }) => {
        if (!cancelled) {
          setRequests(data.items);
          setMeta(data);
        }
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
  }, [status, page, revision]);

  useEffect(() => {
    if (metaReady && searchParams.get("apply") === "1") {
      setApplyOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("apply");
      setSearchParams(next, { replace: true });
    }
  }, [metaReady, searchParams, setSearchParams]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(""), 5500);
    return () => clearTimeout(timer);
  }, [notice]);

  function changeStatus(value) {
    setStatus(value);
    setPage(1);
    setNotice("");
  }

  function handleCreated() {
    setNotice("Request sent. Your manager will review it shortly.");
    setStatus("all");
    setPage(1);
    setRevision((current) => current + 1);
    refreshBalances();
  }

  async function handleCancel() {
    if (!cancelTarget) return;
    setCancelError("");
    setCancelling(true);
    try {
      await api.post(`/leave-requests/${cancelTarget.id}/cancel`);
      setNotice(
        cancelTarget.status === "approved"
          ? "Request cancelled. Those days are back in your balance."
          : "Request withdrawn. You can apply again any time."
      );
      setCancelTarget(null);
      setRevision((current) => current + 1);
      refreshBalances();
    } catch (requestError) {
      setCancelError(apiError(requestError).message);
    } finally {
      setCancelling(false);
    }
  }

  if (!metaReady) {
    return (
      <div className="page">
        <PageLoader label="Fetching your leave balances…" />
      </div>
    );
  }

  if (metaError) {
    return (
      <div className="page">
        <ErrorState message={metaError} onRetry={loadMeta} />
      </div>
    );
  }

  const emptyContent = {
    all: {
      title: "No leave requests yet",
      description: "Your applications and decisions will live here.",
      action: (
        <button
          type="button"
          className="btn btn--soft btn--sm"
          onClick={() => setApplyOpen(true)}
        >
          Request time off
        </button>
      ),
    },
    pending: {
      title: "Nothing pending",
      description: "You're all caught up on the approval queue.",
    },
    approved: {
      title: "No approved leave yet",
      description: "Approved requests will appear here once your manager signs off.",
    },
    rejected: {
      title: "No rejected requests",
      description: "That's a good sign.",
    },
    cancelled: {
      title: "No cancelled requests",
      description: "Withdrawn applications will show up here.",
    },
  }[status];

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">Your time off</span>
          <h1>My leave</h1>
          <p>Track balances, review decisions, and plan your next break.</p>
        </div>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => setApplyOpen(true)}
          disabled={!leaveTypes.length}
        >
          <Plus size={16} />
          Request leave
        </button>
      </header>

      <section className="mini-balance-grid" aria-label="Leave balance summary">
        {balances.map((balance) => {
          const style = BALANCE_STYLES[balance.leave_type.code] || {
            icon: Palmtree,
            tone: "coral",
          };
          const Icon = style.icon;
          return (
            <article
              className={`mini-balance mini-balance--${style.tone}`}
              key={balance.id}
            >
              <span className={`mini-balance__icon mini-balance__icon--${style.tone}`}>
                <Icon size={17} />
              </span>
              <div className="mini-balance__copy">
                <span>{shortLeaveType(balance.leave_type.name)}</span>
                <strong>
                  {balance.remaining_days}
                  <small> / {balance.allocated_days} days left</small>
                </strong>
                <ProgressBar
                  used={balance.used_days}
                  total={balance.allocated_days}
                  tone={style.tone}
                />
              </div>
            </article>
          );
        })}
      </section>

      <section className="panel">
        <header className="panel__head panel__head--toolbar">
          <div className="filter-tabs" role="tablist" aria-label="Filter requests by status">
            {FILTERS.map((filter) => (
              <button
                type="button"
                key={filter.value}
                role="tab"
                aria-selected={status === filter.value}
                className={`filter-tab ${
                  status === filter.value ? "is-active" : ""
                }`}
                onClick={() => changeStatus(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
          {meta && (
            <span className="toolbar-count">
              {pluralize(meta.total, "request")}
            </span>
          )}
        </header>

        {notice && (
          <div className="panel__notice">
            <InlineAlert tone="success">{notice}</InlineAlert>
          </div>
        )}

        {error ? (
          <ErrorState
            compact
            message={error}
            onRetry={() => setRevision((current) => current + 1)}
          />
        ) : loading ? (
          <PageLoader label="Loading your requests…" />
        ) : requests.length ? (
          <>
            <div className="table-wrap leave-table">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Leave type</th>
                    <th>Dates</th>
                    <th>Days</th>
                    <th>Applied on</th>
                    <th>Status</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {requests.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <LeaveTypeTag type={request.leave_type} />
                      </td>
                      <td>
                        <span className="cell-strong">
                          {formatRange(request.start_date, request.end_date)}
                        </span>
                        <span className="cell-sub">
                          {relativeStart(request.start_date)}
                        </span>
                      </td>
                      <td>{request.days}</td>
                      <td className="cell-muted">
                        {formatDate(request.created_at?.slice(0, 10))}
                      </td>
                      <td>
                        <StatusBadge status={request.status} />
                      </td>
                      <td className="cell-actions">
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => setDetail(request)}
                        >
                          <Eye size={15} />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {meta && meta.pages > 1 && (
              <div className="pagination">
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={!meta.has_prev}
                  onClick={() => setPage((current) => current - 1)}
                >
                  <ChevronLeft size={15} />
                  Previous
                </button>
                <span>
                  Page {meta.page} of {meta.pages}
                </span>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  disabled={!meta.has_next}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Next
                  <ChevronRight size={15} />
                </button>
              </div>
            )}

            <div className="m-card-list">
              {requests.map((request) => (
                <article className="m-card" key={request.id}>
                  <header>
                    <LeaveTypeTag type={request.leave_type} />
                    <StatusBadge status={request.status} />
                  </header>
                  <strong>{formatRange(request.start_date, request.end_date)}</strong>
                  <p>
                    {pluralize(request.days, "day")} · applied{" "}
                    {formatDate(request.created_at?.slice(0, 10))}
                  </p>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setDetail(request)}
                  >
                    <Eye size={15} />
                    View request
                  </button>
                </article>
              ))}
            </div>
          </>
        ) : (
          <EmptyState
            icon={CalendarX2}
            title={emptyContent.title}
            description={emptyContent.description}
            action={emptyContent.action}
          />
        )}
      </section>

      <div className="timeline-note">
        <CalendarPlus size={17} />
        <p>
          Planning a longer break? Earned leave gives you{" "}
          {balances.find((item) => item.leave_type.code === "EARNED")
            ?.allocated_days || 15}{" "}
          days a year, and weekends never count against it.
        </p>
        <Link to="/leave?apply=1" className="link-button">
          Plan a break
        </Link>
      </div>

      <ApplyLeaveModal
        open={applyOpen}
        onClose={() => setApplyOpen(false)}
        leaveTypes={leaveTypes}
        balances={balances}
        onCreated={handleCreated}
      />

      <RequestDetailModal
        request={detail}
        onClose={() => setDetail(null)}
        onCancel={(request) => {
          setDetail(null);
          setCancelError("");
          setCancelTarget(request);
        }}
      />

      <Modal
        open={Boolean(cancelTarget)}
        onClose={() => setCancelTarget(null)}
        title="Cancel this leave request?"
        subtitle={
          cancelTarget
            ? `${formatRange(cancelTarget.start_date, cancelTarget.end_date)} · ${pluralize(
                cancelTarget.days,
                "day"
              )}`
            : ""
        }
        footer={
          <>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setCancelTarget(null)}
            >
              Keep it
            </button>
            <button
              type="button"
              className="btn btn--danger"
              onClick={handleCancel}
              disabled={cancelling}
            >
              {cancelling ? "Cancelling…" : "Yes, cancel request"}
            </button>
          </>
        }
      >
        {cancelError && <InlineAlert tone="error">{cancelError}</InlineAlert>}
        <p className="confirm-copy">
          {cancelTarget?.status === "approved"
            ? "This request is already approved. Cancelling it will return the days to your balance."
            : "This request is still pending. Cancelling it withdraws the application."}{" "}
          Leave that has already started cannot be cancelled.
        </p>
      </Modal>
    </div>
  );
}
