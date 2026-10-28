import { CalendarDays } from "lucide-react";
import Avatar from "./Avatar";
import LeaveTypeTag from "./LeaveTypeTag";
import Modal from "./Modal";
import StatusBadge from "./StatusBadge";
import {
  formatDate,
  formatDateTime,
  formatRange,
  pluralize,
  todayISO,
} from "../utils/format";

export default function RequestDetailModal({ request, onClose, onCancel }) {
  if (!request) return null;

  const canCancel =
    (request.status === "pending" || request.status === "approved") &&
    request.start_date > todayISO();

  return (
    <Modal
      open={Boolean(request)}
      onClose={onClose}
      title="Leave request"
      subtitle={`Request #${request.id} · ${formatDate(request.created_at?.slice(0, 10))}`}
      footer={
        <>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Close
          </button>
          {canCancel && onCancel && (
            <button
              type="button"
              className="btn btn--danger-soft"
              onClick={() => onCancel(request)}
            >
              Cancel request
            </button>
          )}
        </>
      }
    >
      <div className="review-person">
        <Avatar name={request.employee.name} />
        <div>
          <strong>{request.employee.name}</strong>
          <span>{request.employee.department || "Unassigned"}</span>
        </div>
        <StatusBadge status={request.status} />
      </div>

      <dl className="detail-list">
        <div>
          <dt>
            <CalendarDays size={15} /> Dates
          </dt>
          <dd>{formatRange(request.start_date, request.end_date)}</dd>
        </div>
        <div>
          <dt>Working days</dt>
          <dd>{pluralize(request.days, "day")}</dd>
        </div>
        <div>
          <dt>Leave type</dt>
          <dd>
            <LeaveTypeTag type={request.leave_type} />
          </dd>
        </div>
        <div>
          <dt>Applied on</dt>
          <dd>{formatDateTime(request.created_at)}</dd>
        </div>
      </dl>

      <div className="quote-block">
        <span>Reason</span>
        <p>{request.reason}</p>
      </div>

      {request.reviewed_by && (
        <div className="decision-block">
          <div className="decision-block__head">
            <span>Decision</span>
            <StatusBadge status={request.status} />
          </div>
          <p>
            {request.status === "approved" ? "Approved" : "Reviewed"} by{" "}
            <strong>{request.reviewed_by.name}</strong>
            {request.reviewed_at ? ` on ${formatDateTime(request.reviewed_at)}` : ""}.
          </p>
          {request.review_note && <blockquote>{request.review_note}</blockquote>}
        </div>
      )}

      {request.status === "pending" && (
        <p className="modal-note">
          Your manager hasn't reviewed this request yet. You can cancel it any
          time before it starts.
        </p>
      )}
    </Modal>
  );
}
