// Date helpers. Tests use dates far in the future so the seeded requests
// (which sit around today) never collide with them.

function iso(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const SLOTS_PER_YEAR = 14;
const SLOT_LENGTH_DAYS = 21; // three weeks, enough room for the longest range used (13 working days)

/** First Monday of March in the given year (UTC). */
function firstMondayOfMarch(year: number): Date {
  const d = new Date(Date.UTC(year, 2, 1));
  while (d.getUTCDay() !== 1) d.setUTCDate(d.getUTCDate() + 1);
  return d;
}

export function nextYear(): number {
  return new Date().getFullYear() + 1;
}

/**
 * A Monday-to-weekday range with the requested number of working days.
 * Every test uses its own slot number, so two tests never share dates.
 */
export function workWindow(slot: number, workingDays: number) {
  const year = nextYear() + Math.floor(slot / SLOTS_PER_YEAR);
  const start = firstMondayOfMarch(year);
  start.setUTCDate(start.getUTCDate() + (slot % SLOTS_PER_YEAR) * SLOT_LENGTH_DAYS);

  const end = new Date(start);
  let counted = 1;
  while (counted < workingDays) {
    end.setUTCDate(end.getUTCDate() + 1);
    if (end.getUTCDay() !== 0 && end.getUTCDay() !== 6) counted += 1;
  }
  return { start: iso(start), end: iso(end), year: start.getUTCFullYear() };
}

/** Friday to the following Monday: four calendar days, two working days. */
export function weekendWindow(slot: number) {
  const base = workWindow(slot, 1); // a Monday
  const friday = new Date(base.start + 'T00:00:00Z');
  friday.setUTCDate(friday.getUTCDate() + 4);
  const monday = new Date(friday);
  monday.setUTCDate(monday.getUTCDate() + 3);
  return { start: iso(friday), end: iso(monday), year: friday.getUTCFullYear() };
}

export function yesterday(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** The text the app shows for a range, matching frontend/src/utils/format.js (en-IN). */
export function uiRange(start: string, end: string): string {
  const fmt = (v: string, opts: Intl.DateTimeFormatOptions) =>
    new Intl.DateTimeFormat('en-IN', opts).format(new Date(v + 'T00:00:00'));
  const full: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short', year: 'numeric' };
  if (start === end) return fmt(start, full);
  const s = new Date(start + 'T00:00:00');
  const e = new Date(end + 'T00:00:00');
  if (s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear()) {
    return `${s.getDate()} – ${fmt(end, full)}`;
  }
  return `${fmt(start, { day: 'numeric', month: 'short' })} – ${fmt(end, full)}`;
}
