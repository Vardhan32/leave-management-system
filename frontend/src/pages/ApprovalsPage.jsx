import { useCallback, useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Eye,
  Search,
  X,
} from "lucide-react";
import { useSearchParams } from "react-router-dom";
import api, { apiError } from "../api/client";
import Avatar from "../components/Avatar";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import InlineAlert from "../components/InlineAlert";
import LeaveTypeTag from "../components/LeaveTypeTag";
import PageLoader from "../components/PageLoader";
import RequestDetailModal from "../components/RequestDetailModal";
import ReviewModal from "../components/ReviewModal";
import StatusBadge from "../components/StatusBadge";
import {
  formatDate,
  formatRange,
  pluralize,
  relativeStart,
} from "../utils/format";

const TABS = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "cancelled", label: "Cancelled" },
];

const PAGE_SIZE = 8;

const COPY = {
  pending: "Requests waiting for a decision, newest first.",
  approved: "Approved leave across the team this year.",
  rejected: "Requests that were declined, with the reason on record.",
  cancelled: "Withdrawn requests and the days returned to balance.",
};

export default function ApprovalsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = TABS.some(
    (tab) => tab.value === searchParams.get("status")
  )
    ? searchParams.get("status")
    : "pending";

  const [status, setStatus] = useState(initialStatus);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [items, setItems] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [reviewTarget, setReviewTarget] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query.trim());
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const fromUrl = searchParams.get("status");
    if (fromUrl && TABS.some((tab) => tab.value === fromUrl) && fromUrl !== status) {
      setStatus(fromUrl);
      setPage(1);
    }
  }, [searchParams, status]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    api
      .get("/leave-requests", {
        params: {
          status,
          page,
          per_page: PAGE_SIZE,
          ...(debouncedQuery ? { q: debouncedQuery } : {}),
        },
      })
      .then(({ data }) => {
        if (!cancelled) {
          setItems(data.items);
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
  }, [status, page, debouncedQuery, revision]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(""), 5500);
    return () => clearTimeout(timer);
  }, [notice]);

  function changeStatus(value) {
    setStatus(value);
    setPage(1);
    setNotice("");
    const next = new URLSearchParams(searchParams);
    next.set("status", value);
    setSearchParams(next, { replace: true });
  }

  function handleReviewed(request, decision) {
    setNotice(
      `${request.employee.name}'s request was ${
        decision === "approve" ? "approved" : "rejected"
      }.`
    );
    setRevision((current) => current + 1);
  }

  const emptyCopy = {
    pending: {
      title: "No requests waiting",
      description: "The approval queue is clear. Enjoy the quiet.",
    },
    approved: {
      title: "No approved leave",
      description: "Approved requests will appear here.",
    },
    rejected: {
      title: "No rejected requests",
      description: "Nothing has been declined for these dates.",
    },
    cancelled: {
      title: "No cancelled requests",
      description: "Withdrawn requests will appear here.",
    },
  }[status];

  const searchActive = Boolean(debouncedQuery);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <span className="eyebrow">People ops</span>
          <h1>Leave approvals</h1>
          <p>Review requests with the context you need, minus the email chain.</p>
        </div>
        <div className="page-head__count">
          <span>In this view</span>
          <strong>{meta?.total ?? "—"}</strong>
          <small>{status === "pending" ? "awaiting review" : "requests"}</small>
        </div>
      </header>

      <section className="panel">
        <header className="panel__head panel__head--toolbar approvals-toolbar">
          <div
            className="filter-tabs"
            role="tablist"
            aria-label="Filter approvals by status"
          >
            {TABS.map((tab) => (
              <button
                type="button"
                key={tab.value}
                role="tab"
                aria-selected={status === tab.value}
                className={`filter-tab ${
                  status === tab.value ? "is-active" : ""
                }`}
                onClick={() => changeStatus(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <label className="search-field">
            <Search size={16} />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search employee or reason"
              aria-label="Search leave requests"
            />
            {query && (
              <button
                type="button"
                className="search-field__clear"
                onClick={() => setQuery("")}
                aria-label="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </label>
        </header>

        <div className="panel__subhead">
          <p>{COPY[status]}</p>
        </div>

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
          <PageLoader label="Checking the approval queue…" />
        ) : items.length ? (
          <>
            <div className="table-wrap">
              <table className="data-table approvals-table">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Leave</th>
                    <th>Dates</th>
                    <th>Days</th>
                    <th>Status</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((request) => (
                    <tr key={request.id}>
                      <td>
                        <div className="person-cell">
                          <Avatar name={request.employee.name} size="sm" />
                          <div>
                            <strong>{request.employee.name}</strong>
                            <span>
                              {request.employee.department || "Unassigned"}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <LeaveTypeTag type={request.leave_type} />
                        <span className="cell-sub cell-sub--clamp">
                          {request.reason}
                        </span>
                      </td>
                      <td>
                        <span className="cell-strong">
                          {formatRange(request.start_date, request.end_date)}
                        </span>
                        <span className="cell-sub">
                          {request.status === "pending"
                            ? `Requested ${formatDate(
                                request.created_at?.slice(0, 10)
                              )}`
                            : `Reviewed ${formatDate(
                                request.reviewed_at?.slice(0, 10)
                              )}`}
                        </span>
                      </td>
                      <td>{request.days}</td>
                      <td>
                        <StatusBadge status={request.status} />
                        {request.reviewed_by && (
                          <span className="cell-sub">
                            by {request.reviewed_by.name}
                          </span>
                        )}
                      </td>
                      <td className="cell-actions">
                        {request.status === "pending" ? (
                          <button
                            type="button"
                            className="btn btn--primary btn--xs"
                            onClick={() => setReviewTarget(request)}
                          >
                            <ClipboardCheck size={14} />
                            Review
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="link-button"
                            onClick={() => setDetail(request)}
                          >
                            <Eye size={15} />
                            View
                          </button>
                        )}
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
          </>
        ) : (
          <EmptyState
            icon={ClipboardCheck}
            title={searchActive ? "No matches found" : emptyCopy.title}
            description={
              searchActive
                ? `Nothing matches “${debouncedQuery}” in this view. Try another name or clear the search.`
                : emptyCopy.description
            }
            action={
              searchActive ? (
                <button
                  type="button"
                  className="btn btn--soft btn--sm"
                  onClick={() => setQuery("")}
                >
                  Clear search
                </button>
              ) : null
            }
          />
        )}
      </section>

      <ReviewModal
        request={reviewTarget}
        onClose={() => setReviewTarget(null)}
        onReviewed={handleReviewed}
      />

      <RequestDetailModal
        request={detail}
        onClose={() => setDetail(null)}
      />
    </div>
  );
}
