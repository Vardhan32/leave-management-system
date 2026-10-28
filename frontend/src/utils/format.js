const dateFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
});

const longDateFormatter = new Intl.DateTimeFormat("en-IN", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function parseISODate(value) {
  if (!value) return null;
  const [year, month, day] = String(value).split("-").map(Number);
  if (!year || !month || !day) return null;
  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function toISODate(value) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayISO() {
  return toISODate(new Date());
}

export function formatDate(value) {
  const parsed = parseISODate(value);
  return parsed ? dateFormatter.format(parsed) : "—";
}

export function formatLongDate(value) {
  const parsed = parseISODate(value);
  return parsed ? longDateFormatter.format(parsed) : "—";
}

export function formatDateTime(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "—" : dateTimeFormatter.format(parsed);
}

export function formatRange(startValue, endValue) {
  const start = parseISODate(startValue);
  const end = parseISODate(endValue);
  if (!start) return "—";
  if (!end || startValue === endValue) return dateFormatter.format(start);

  const sameMonth =
    start.getMonth() === end.getMonth() &&
    start.getFullYear() === end.getFullYear();
  const sameYear = start.getFullYear() === end.getFullYear();

  if (sameMonth) {
    return `${start.getDate()} – ${dateFormatter.format(end)}`;
  }
  if (sameYear) {
    const startShort = new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      month: "short",
    }).format(start);
    return `${startShort} – ${dateFormatter.format(end)}`;
  }
  return `${dateFormatter.format(start)} – ${dateFormatter.format(end)}`;
}

export function calendarParts(value) {
  const parsed = parseISODate(value);
  if (!parsed) return { day: "—", month: "—" };
  return {
    day: String(parsed.getDate()),
    month: new Intl.DateTimeFormat("en-IN", { month: "short" }).format(parsed),
  };
}

export function workingDaysBetween(startValue, endValue) {
  const start = parseISODate(startValue);
  const end = parseISODate(endValue);
  if (!start || !end || end < start) return 0;

  let total = 0;
  const cursor = new Date(start);
  let guard = 0;
  while (cursor <= end && guard < 400) {
    const weekday = cursor.getDay();
    if (weekday !== 0 && weekday !== 6) total += 1;
    cursor.setDate(cursor.getDate() + 1);
    guard += 1;
  }
  return total;
}

export function daysUntil(value) {
  const target = parseISODate(value);
  if (!target) return null;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target - today) / 86400000);
}

export function relativeStart(value) {
  const days = daysUntil(value);
  if (days === null) return "";
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  if (days > 1) return `In ${days} days`;
  if (days === -1) return "Yesterday";
  return `${Math.abs(days)} days ago`;
}

export function greeting(date = new Date()) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function firstName(name) {
  return name?.trim().split(/\s+/)[0] || "there";
}

export function initials(name) {
  if (!name) return "?";
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function shortLeaveType(name) {
  return (name || "").replace(/\s*Leave$/i, "");
}

export function pluralize(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural || `${singular}s`}`;
}
