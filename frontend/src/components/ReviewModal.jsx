import { useEffect, useState } from "react";
import { CalendarRange, CircleCheck, CircleX, Info } from "lucide-react";
import api, { apiError } from "../api/client";
import Avatar from "./Avatar";
import InlineAlert from "./InlineAlert";
import LeaveTypeTag from "./LeaveTypeTag";
import Modal from "./Modal";
import {
  formatDate,
  formatDateTime,
  formatRange,
  pluralize,
  shortLeaveType,
} from "../utils/format";

export default function ReviewModal({ request, onClose, onReviewed }) {
  const [balances, setBalances] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!request) return undefined;

    let cancelled = false;
    setBalances(null);
    setLoadError("");
    setNote("");
    setErrors({});
    setMessage("");
    setSubmitting(false);
    setLoading(true);

    api
      .get("/leave-balances", { params: { user_id: request.employee.id } })
      .then(({ data }) => {
        if (!cancelled) setBalances(data.balances);
      })
      .catch((error) => {
        if (!cancelled) setLoadError(apiError(error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [request]);

  if (!request) return null;

  const balance = balances?.find(
    (item) => item.leave_type.id === request.leave_type.id
  );
  const insufficient = balance && balance.remaining_days < request.days;

  async function submit(decision) {
    setMessage("");
    if (decision === "reject" && !note.trim()) {
      setErrors({ note: "Add a short note before rejecting this request." });
      return;
    }

    setSubmitting(true);
    try {
      const { data } = await api.post(`/leave-requests/${request.id}/review`, {
        decision,
        note: note.trim() || undefined,
      });
      onReviewed(data, decision);
      onClose();
    } catch (requestError) {
      const parsed = apiError(requestError);
      setMessage(parsed.message);
      setErrors(parsed.errors || {});
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={Boolean(request)}
      onClose={onClose}
      title="Review leave request"
      subtitle={`Request #${request.id} · submitted ${formatDate(request.created_at?.slice(0, 10))}`}
      size="lg"
      footer={
        <>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="btn btn--danger-soft"
            onClick={() => submit("reject")}
            disabled={submitting}
          >
            <CircleX size={16} />
            Reject
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => submit("approve")}
            disabled={submitting || Boolean(insufficient)}
          >
            <CircleCheck size={16} />
            {submitting ? "Saving…" : "Approve"}
          </button>
        </>
      }
    >
      <div className="review-person">
        <Avatar name={request.employee.name} />
        <div>
          <strong>{request.employee.name}</strong>
          <span>
            {request.employee.job_title || "Team member"} ·{" "}
            {request.employee.department || "Unassigned"}
          </span>
        </div>
        <LeaveTypeTag type={request.leave_type} />
      </div>

      {message && <InlineAlert tone="error">{message}</InlineAlert>}

      <dl className="detail-list">
        <div>
          <dt>
            <CalendarRange size={15} /> Dates
          </dt>
          <dd>{formatRange(request.start_date, request.end_date)}</dd>
        </div>
        <div>
          <dt>Working days</dt>
          <dd>{pluralize(request.days, "day")}</dd>
        </div>
        <div>
          <dt>Leave type</dt>
          <dd>{request.leave_type.name}</dd>
        </div>
        <div>
          <dt>Requested</dt>
          <dd>{formatDateTime(request.created_at)}</dd>
        </div>
      </dl>

      <div className="quote-block">
        <span>Reason</span>
        <p>{request.reason}</p>
      </div>

      <div className={`balance-context ${insufficient ? "balance-context--low" : ""}`}>
        <span className="balance-context__icon">
          <Info size={17} />
        </span>
        {loading ? (
          <p>Checking {shortLeaveType(request.leave_type.name)} balance…</p>
        ) : loadError ? (
          <p>{loadError}</p>
        ) : balance ? (
          <div>
            <p>
              <strong>{pluralize(balance.remaining_days, "day")}</strong> of{" "}
              {request.leave_type.name.toLowerCase()} left this year, from an
              allocation of {balance.allocated_days}.
            </p>
            <span>
              Approving this request will leave{" "}
              {pluralize(Math.max(balance.remaining_days - request.days, 0), "day")}.
            </span>
          </div>
        ) : (
          <p>No balance record found for this leave type.</p>
        )}
      </div>

      {insufficient && (
        <InlineAlert tone="warning">
          This request needs {pluralize(request.days, "day")}, but only{" "}
          {pluralize(balance.remaining_days, "day")} remain. Reject it or ask the
          employee to amend the dates.
        </InlineAlert>
      )}

      <label className={`field ${errors.note ? "field--invalid" : ""}`}>
        <span className="field__label">Decision note</span>
        <textarea
          rows={3}
          value={note}
          onChange={(event) => {
            setNote(event.target.value);
            setErrors((current) => ({ ...current, note: undefined }));
          }}
          maxLength={500}
          placeholder="Optional when approving. Required when rejecting — be specific and kind."
        />
        <span className="field__hint field__hint--row">
          <span>Both the employee and the audit trail will see this note.</span>
          <span>{note.length}/500</span>
        </span>
        {errors.note && <span className="field__error">{errors.note}</span>}
      </label>
    </Modal>
  );
}
