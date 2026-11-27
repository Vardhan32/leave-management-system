"""Turns the placeholders written by the generator into real request values.

The generator cannot write fixed dates, because "start must be today or later"
depends on the day the suite runs. It writes tokens instead:

  {today}, {today+N}, {today-N}      relative to date.today()
  {base}, {base+N}                   a Monday early in March of next year,
                                     far enough ahead that requests never hit
                                     the past-date or cross-year rules
  {next_working_monday}, {next_working_monday+N}
                                     same as {base}; the name used in the spec
  {start_date+N}, {start_date-N}     relative to the start_date in the same body
  {self_id}, {existing_id}           ids supplied by the test (context)
  {"$text": n}                       a valid string of exactly n characters
  {"$text": n, "$pad": k}            the same string with k spaces on each side
  {"$missing": true}                 the field is left out of the body
"""

import re
from datetime import date, timedelta

TOKEN_RE = re.compile(r"^\{([a-z_]+)(?:([+-])(\d+))?\}$")
FILLER = "Annual family visit and travel arrangements. "


def base_monday(today=None):
    """First Monday on or after 1 March of next year."""
    today = today or date.today()
    first = date(today.year + 1, 3, 1)
    return first + timedelta(days=(7 - first.weekday()) % 7)


def text_of_length(length):
    if length <= 0:
        return ""
    repeated = FILLER * (length // len(FILLER) + 1)
    # avoid a trailing space being trimmed away by the API
    value = repeated[:length]
    if value.endswith(" "):
        value = value[:-1] + "."
    return value


def is_missing(value):
    return isinstance(value, dict) and value.get("$missing") is True


def resolve_value(value, context, today=None):
    """Resolve one token. Anything that is not a token is returned unchanged."""
    today = today or date.today()

    if isinstance(value, dict) and "$text" in value:
        pad = " " * value.get("$pad", 0)
        return pad + text_of_length(value["$text"]) + pad

    if not isinstance(value, str):
        return value

    match = TOKEN_RE.match(value)
    if not match:
        return value

    name, sign, amount = match.groups()
    offset = int(amount) if amount else 0
    if sign == "-":
        offset = -offset

    if name == "today":
        return (today + timedelta(days=offset)).isoformat()
    if name in ("base", "next_working_monday"):
        return (base_monday(today) + timedelta(days=offset)).isoformat()
    if name in context:
        anchor = context[name]
        if offset == 0:
            return anchor
        return (date.fromisoformat(anchor) + timedelta(days=offset)).isoformat()
    raise KeyError("Unknown token " + value)


def resolve_body(body, context=None, today=None):
    """Resolve every field of a request body.

    start_date is resolved first so end_date can refer to it. Fields marked
    as missing are dropped.
    """
    context = dict(context or {})
    if not isinstance(body, dict):
        return body

    resolved = {}
    order = sorted(body, key=lambda key: 0 if key == "start_date" else 1)
    for key in order:
        value = body[key]
        if is_missing(value):
            continue
        resolved[key] = resolve_value(value, context, today)
        if key == "start_date" and isinstance(resolved[key], str):
            context["start_date"] = resolved[key]
    return {key: resolved[key] for key in body if key in resolved}


def add_working_days(start, count):
    """End date of a range that starts on start and holds count weekdays.

    start is expected to be a weekday. count must be at least 1.
    """
    if count < 1:
        raise ValueError("count must be at least 1")
    cursor = start
    seen = 1 if cursor.weekday() < 5 else 0
    while seen < count:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            seen += 1
    return cursor
