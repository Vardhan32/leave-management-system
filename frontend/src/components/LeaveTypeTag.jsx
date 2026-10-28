import { shortLeaveType } from "../utils/format";

export default function LeaveTypeTag({ type }) {
  if (!type) return null;
  return (
    <span className={`type-tag type-tag--${type.code.toLowerCase()}`}>
      <span className="type-tag__dot" aria-hidden="true" />
      {shortLeaveType(type.name)}
    </span>
  );
}
