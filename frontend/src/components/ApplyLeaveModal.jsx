import { useEffect, useState } from "react";
import { CalendarDays, Info, Sun } from "lucide-react";
import api, { apiError } from "../api/client";
import InlineAlert from "./InlineAlert";
import Modal from "./Modal";
import {
  formatRange,
  pluralize,
  shortLeaveType,
  todayISO,
  workingDaysBetween,
} from "../utils/format";

const EMPTY_FORM = {
  leave_type_id: "",
  start_date: "",
  end_date: "",
  reason: "",
};

export default function ApplyLeaveModal({
  open,
  onClose,
  leaveTypes,
  balances,
  onCreated,
}) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({
        ...EMPTY_FORM,
        leave_type_id: leaveTypes[0]?.id || "",
      });
      setErrors({});
      setMessage("");
      setSubmitting(false);
    }
  }, [open, leaveTypes]);

  const selectedType = leaveTypes.find(
    (type) => String(type.id) === String(form.leave_type_id)
  );
  const selectedBalance = balances.find(
    (balance) => balance.leave_type.id === Number(form.leave_type_id)
  );
  const days = workingDaysBetween(form.start_date, form.end_date);
  const remainingAfter = selectedBalance
    ? Math.max(selectedBalance.remaining_days - days, 0)
    : null;
  const exceedsBalance =
    Boolean(selectedBalance) && days > 0 && days > selectedBalance.remaining_days;

  function update(field) {
    return (event) => {
      const value = event.target.value;
      setForm((current) => {
        const next = { ...current, [field]: value };
        if (field === "start_date" && next.end_date && next.end_date < value) {
          next.end_date = value;
        }
        return next;
      });
      setErrors((current) => ({ ...current, [field]: undefined }));
      setMessage("");
    };
  }

  function validate() {
    const next = {};
    if (!form.leave_type_id) next.leave_type_id = "Choose a leave type.";
    if (!form.start_date) next.start_date = "Pick a start date.";
    if (!form.end_date) next.end_date = "Pick an end date.";
    if (form.start_date && form.end_date && form.end_date < form.start_date) {
      next.end_date = "The end date cannot be before the start date.";
    } else if (form.start_date && form.end_date && days === 0) {
      next.end_date = "This range has no working days (Mon–Fri).";
    }
    if (form.reason.trim().length < 10) {
      next.reason = "Add a little more detail (at least 10 characters).";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    if (!validate()) return;

    setSubmitting(true);
    try {
      const { data } = await api.post("/leave-requests", {
        leave_type_id: Number(form.leave_type_id),
        start_date: form.start_date,
        end_date: form.end_date,
        reason: form.reason.trim(),
      });
      onCreated(data);
      onClose();
    } catch (requestError) {
      const parsed = apiError(requestError);
      setMessage(parsed.message);
      setErrors(parsed.errors);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Request time off"
      subtitle="Pick your dates and tell your manager what it's for."
      size="lg"
      footer={
        <>
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form="apply-leave-form"
            className="btn btn--primary"
            disabled={submitting}
          >
            {submitting ? "Sending request…" : "Send request"}
          </button>
        </>
      }
    >
      <form id="apply-leave-form" onSubmit={handleSubmit} noValidate>
        {message && <InlineAlert tone="error">{message}</InlineAlert>}

        <div className="form-grid">
          <label
            className={`field field--span-2 ${
              errors.leave_type_id ? "field--invalid" : ""
            }`}
          >
            <span className="field__label">Leave type</span>
            <span className="input-wrap">
              <Sun size={17} className="input-wrap__icon" />
              <select value={form.leave_type_id} onChange={update("leave_type_id")}>
                <option value="" disabled>
                  Select a leave type
                </option>
                {leaveTypes.map((type) => (
                  <option key={type.id} value={type.id}>
                    {type.name} · {type.default_days} days a year
                  </option>
                ))}
              </select>
            </span>
            {selectedType && (
              <span className="field__hint">{selectedType.description}</span>
            )}
            {errors.leave_type_id && (
              <span className="field__error">{errors.leave_type_id}</span>
            )}
          </label>

          <label className={`field ${errors.start_date ? "field--invalid" : ""}`}>
            <span className="field__label">Start date</span>
            <span className="input-wrap">
              <input
                type="date"
                value={form.start_date}
                onChange={update("start_date")}
                min={todayISO()}
              />
            </span>
            {errors.start_date && (
              <span className="field__error">{errors.start_date}</span>
            )}
          </label>

          <label className={`field ${errors.end_date ? "field--invalid" : ""}`}>
            <span className="field__label">End date</span>
            <span className="input-wrap">
              <input
                type="date"
                value={form.end_date}
                onChange={update("end_date")}
                min={form.start_date || todayISO()}
              />
            </span>
            {errors.end_date && (
              <span className="field__error">{errors.end_date}</span>
            )}
          </label>
        </div>

        <div className="leave-preview">
          <span className="leave-preview__icon">
            <CalendarDays size={19} />
          </span>
          <div className="leave-preview__copy">
            <strong>
              {days > 0
                ? `${pluralize(days, "working day")} selected`
                : "Weekends are skipped automatically"}
            </strong>
            <span>
              {form.start_date && form.end_date && days > 0
                ? `${formatRange(form.start_date, form.end_date)}${
                    selectedType ? ` · ${shortLeaveType(selectedType.name)} leave` : ""
                  }`
                : "Choose a start and end date to see the working-day count."}
            </span>
          </div>
          {selectedBalance && days > 0 && (
            <div className="leave-preview__balance">
              <span>{remainingAfter} left after</span>
              <strong>
                {selectedBalance.remaining_days}/{selectedBalance.allocated_days}
              </strong>
            </div>
          )}
        </div>

        {exceedsBalance && (
          <InlineAlert tone="warning">
            This request needs {pluralize(days, "day")}, but you only have{" "}
            {pluralize(selectedBalance.remaining_days, "day")} of{" "}
            {shortLeaveType(selectedType.name)} leave left this year. Try a
            shorter range or another leave type.
          </InlineAlert>
        )}

        {selectedBalance && (
          <p className="balance-note">
            <Info size={14} /> {selectedBalance.remaining_days} of{" "}
            {selectedBalance.allocated_days} {shortLeaveType(selectedType.name)}{" "}
            days remain for {selectedBalance.year}. Pending requests don't reduce
            your balance until they're approved.
          </p>
        )}

        <label className={`field ${errors.reason ? "field--invalid" : ""}`}>
          <span className="field__label">Reason</span>
          <textarea
            rows={3}
            value={form.reason}
            onChange={update("reason")}
            maxLength={500}
            placeholder="A short note for your manager — travel plans, a family event, or an appointment."
          />
          <span className="field__hint field__hint--row">
            <span>This helps your manager plan cover for your work.</span>
            <span>{form.reason.length}/500</span>
          </span>
          {errors.reason && <span className="field__error">{errors.reason}</span>}
        </label>
      </form>
    </Modal>
  );
}
