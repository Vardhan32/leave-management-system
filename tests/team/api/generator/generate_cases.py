"""Test data generator for the LeaveDesk API tests.

Reads the OpenAPI spec and writes one JSON file of test cases:

  * equivalence partitions (EP) for every request-body field and query
    parameter, one invalid value per case
  * 3-point boundary values (BVA) for every limit the spec declares:
    minLength, maxLength, minimum, maximum, the x-lookup-max id range,
    date limits (x-min-relative, x-min-field) and the balance allocations
    in x-business-rules

The API tests never hard-code these values. They load generated/cases.json,
so changing a constraint in the spec and running the generator again changes
what the tests send and what they expect back.

Usage (from the repository root):

    python tests/team/api/generator/generate_cases.py
    python tests/team/api/generator/generate_cases.py --spec other.yaml --out other.json
    python tests/team/api/generator/generate_cases.py --compare old_cases.json

Values that depend on the run date are written as tokens and resolved by the
tests at run time, for example "{today-1}" or "{start_date+1}". See
tests/team/api/support/tokens.py for the full list.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE.parent / "spec" / "openapi.yaml"
DEFAULT_OUT = HERE.parent / "generated" / "cases.json"

MISSING = {"$missing": True}

# a token that resolves to a valid string of exactly n characters
def text_of(length):
    return {"$text": length}


def resolve_ref(spec, node):
    """Follow a local $ref such as #/components/schemas/LeaveRequestInput."""
    while isinstance(node, dict) and "$ref" in node:
        parts = node["$ref"].lstrip("#/").split("/")
        target = spec
        for part in parts:
            target = target[part]
        node = target
    return node


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CaseBuilder:
    """Keeps the running list of cases and gives each one a stable id."""

    def __init__(self):
        self.cases = []

    def add(self, operation, location, field, technique, partition, value,
            valid, expected_status, error_field=None, **extra):
        case_id = "{}.{}.{}.{}".format(operation["operationId"], field, technique, partition)
        case_id = case_id.replace(" ", "_")
        case = {
            "id": case_id,
            "operation": operation["operationId"],
            "method": operation["method"],
            "path": operation["path"],
            "location": location,
            "field": field,
            "technique": technique,
            "partition": partition,
            "value": value,
            "valid": valid,
            "expected_status": expected_status,
        }
        if error_field:
            case["expected_error_field"] = error_field
        case.update(extra)
        self.cases.append(case)


def operations(spec):
    """Yield every operation with its method and path attached."""
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            operation = dict(operation)
            operation["method"] = method.upper()
            operation["path"] = path
            yield operation


def success_status(operation):
    for code in operation["responses"]:
        if str(code).startswith("2"):
            return int(code)
    raise ValueError("No 2xx response for " + operation["operationId"])


def body_schema(spec, operation):
    body = operation.get("requestBody")
    if not body:
        return None
    schema = body["content"]["application/json"]["schema"]
    return resolve_ref(spec, schema)


def baseline_body(spec, operation):
    """A body built from every property's example. Tests change one field at a time."""
    schema = body_schema(spec, operation)
    if schema is None:
        return None
    return {
        name: prop["example"]
        for name, prop in schema["properties"].items()
        if "example" in prop
    }


def string_cases(builder, operation, location, name, prop, required, invalid_status):
    """EP and BVA for a string field."""
    error = name if location == "body" else None
    ok = success_status(operation)
    # values other than the example that still pass validation
    passing = prop.get("x-valid-status", ok)
    enum = prop.get("enum")
    trimmed = prop.get("x-trimmed", False)
    min_len = prop.get("minLength")
    max_len = prop.get("maxLength")

    # --- equivalence partitions ---------------------------------------------
    builder.add(operation, location, name, "EP", "valid example",
                prop.get("example"), True, ok)

    if required:
        builder.add(operation, location, name, "EP", "missing",
                    MISSING, False, invalid_status, error)
        builder.add(operation, location, name, "EP", "empty string",
                    "", False, invalid_status, error)
        if trimmed:
            builder.add(operation, location, name, "EP", "whitespace only",
                        "          ", False, invalid_status, error)
    else:
        builder.add(operation, location, name, "EP", "missing (optional)",
                    MISSING, True, ok)

    if location == "body":
        nonstring_status = prop.get("x-nonstring-status", invalid_status)
        builder.add(operation, location, name, "EP", "not a string",
                    12345678901, nonstring_status == ok, nonstring_status,
                    error if nonstring_status == invalid_status else None)

    if enum:
        for item in enum:
            if item == prop.get("example"):
                continue
            builder.add(operation, location, name, "EP", "enum value " + item,
                        item, True, ok)
        builder.add(operation, location, name, "EP", "outside enum",
                    "unknown", False, invalid_status, error)
        builder.add(operation, location, name, "EP", "enum wrong case",
                    enum[0].upper(), False, invalid_status, error)
        if trimmed:
            builder.add(operation, location, name, "EP", "enum with padding",
                        "  " + enum[0] + "  ", True, ok)

    if trimmed and min_len:
        # padding does not count towards the length after trimming
        builder.add(operation, location, name, "EP", "padded below minLength",
                    {"$text": min_len - 1, "$pad": 3}, False, invalid_status, error)

    # --- boundary values ----------------------------------------------------
    def length_case(partition, length, inside):
        if enum:
            # any text outside the enum is rejected, whatever its length
            builder.add(operation, location, name, "BVA", partition,
                        text_of(length), False, invalid_status, error, limit_length=length)
        elif inside:
            builder.add(operation, location, name, "BVA", partition,
                        text_of(length), True, passing, limit_length=length)
        else:
            builder.add(operation, location, name, "BVA", partition,
                        text_of(length), False, invalid_status, error, limit_length=length)

    if min_len:
        length_case("minLength-1 ({})".format(min_len - 1), min_len - 1, False)
        length_case("minLength ({})".format(min_len), min_len, True)
        length_case("minLength+1 ({})".format(min_len + 1), min_len + 1, True)
    if max_len:
        length_case("maxLength-1 ({})".format(max_len - 1), max_len - 1, True)
        length_case("maxLength ({})".format(max_len), max_len, True)
        length_case("maxLength+1 ({})".format(max_len + 1), max_len + 1, False)


def date_cases(builder, operation, name, prop, required, invalid_status):
    """EP and BVA for a YYYY-MM-DD body field."""
    ok = success_status(operation)
    builder.add(operation, "body", name, "EP", "valid example",
                prop.get("example"), True, ok)
    if required:
        builder.add(operation, "body", name, "EP", "missing",
                    MISSING, False, invalid_status, name)
        builder.add(operation, "body", name, "EP", "empty string",
                    "", False, invalid_status, name)
    builder.add(operation, "body", name, "EP", "wrong separator",
                "2027/03/01", False, invalid_status, name)
    builder.add(operation, "body", name, "EP", "impossible date",
                "2027-02-30", False, invalid_status, name)
    builder.add(operation, "body", name, "EP", "not a date",
                "next monday", False, invalid_status, name)

    anchor = prop.get("x-min-relative")
    if anchor == "today":
        # end_date is moved next to the start so the range stays short and
        # inside one year; only start_date is under test here
        overrides = {"end_date": "{today+6}"}
        builder.add(operation, "body", name, "BVA", "today-1", "{today-1}",
                    False, invalid_status, name, overrides=overrides)
        builder.add(operation, "body", name, "BVA", "today", "{today}",
                    True, ok, overrides=overrides)
        builder.add(operation, "body", name, "BVA", "today+1", "{today+1}",
                    True, ok, overrides=overrides)

    other = prop.get("x-min-field")
    if other:
        builder.add(operation, "body", name, "BVA", other + "-1",
                    "{" + other + "-1}", False, invalid_status, name)
        builder.add(operation, "body", name, "BVA", other,
                    "{" + other + "}", True, ok)
        builder.add(operation, "body", name, "BVA", other + "+1",
                    "{" + other + "+1}", True, ok)


def integer_cases(builder, operation, location, name, prop, required, invalid_status):
    """EP and BVA for an integer field or query parameter."""
    error = name if location == "body" else None
    ok = success_status(operation)
    clamped = prop.get("x-clamped", False)
    minimum = prop.get("minimum")
    maximum = prop.get("maximum")

    builder.add(operation, location, name, "EP", "valid example",
                prop.get("example"), True, ok)
    builder.add(operation, location, name, "EP", "not a number",
                "abc", False, invalid_status, error)

    if location == "body":
        if required:
            builder.add(operation, location, name, "EP", "missing",
                        MISSING, False, invalid_status, error)
            builder.add(operation, location, name, "EP", "null",
                        None, False, invalid_status, error)
        builder.add(operation, location, name, "EP", "boolean",
                    True, False, invalid_status, error)
        # Validator.integer() calls int(value), so "2" is accepted as 2
        builder.add(operation, location, name, "EP", "numeric string",
                    "2", True, ok)
    else:
        builder.add(operation, location, name, "EP", "omitted",
                    MISSING, True, ok)

    def bound_case(partition, value, inside, clamp_to=None):
        if inside:
            builder.add(operation, location, name, "BVA", partition, value, True, ok)
        elif clamped:
            # out-of-range values are silently clamped instead of rejected
            builder.add(operation, location, name, "BVA", partition, value, True, ok,
                        expected_echo=clamp_to)
        else:
            builder.add(operation, location, name, "BVA", partition, value,
                        False, invalid_status, error)

    if minimum is not None:
        bound_case("minimum-1 ({})".format(minimum - 1), minimum - 1, False, minimum)
        bound_case("minimum ({})".format(minimum), minimum, True)
        bound_case("minimum+1 ({})".format(minimum + 1), minimum + 1, True)
    if maximum is not None:
        bound_case("maximum-1 ({})".format(maximum - 1), maximum - 1, True)
        bound_case("maximum ({})".format(maximum), maximum, True)
        bound_case("maximum+1 ({})".format(maximum + 1), maximum + 1, False, maximum)

    lookup_max = prop.get("x-lookup-max")
    if lookup_max is not None:
        builder.add(operation, location, name, "BVA",
                    "lookup-max-1 ({})".format(lookup_max - 1), lookup_max - 1, True, ok)
        builder.add(operation, location, name, "BVA",
                    "lookup-max ({})".format(lookup_max), lookup_max, True, ok)
        # passes validation, then the id lookup fails
        builder.add(operation, location, name, "BVA",
                    "lookup-max+1 ({})".format(lookup_max + 1), lookup_max + 1, False, 404)


def field_cases(builder, operation, location, name, prop, required, invalid_status):
    kind = prop.get("type")
    if kind == "string" and prop.get("format") == "date":
        date_cases(builder, operation, name, prop, required, invalid_status)
    elif kind == "string":
        string_cases(builder, operation, location, name, prop, required, invalid_status)
    elif kind == "integer":
        integer_cases(builder, operation, location, name, prop, required, invalid_status)
    else:
        raise ValueError("No generator rule for type " + str(kind))


def path_cases(builder, operation, param):
    """EP for an integer path id. Every invalid class ends in 404."""
    ok = success_status(operation)
    name = param["name"]
    builder.add(operation, "path", name, "EP", "existing id", "{existing_id}", True, ok)
    builder.add(operation, "path", name, "EP", "unknown id", "999999", False, 404)
    builder.add(operation, "path", name, "EP", "zero", "0", False, 404)
    builder.add(operation, "path", name, "EP", "negative", "-1", False, 404)
    builder.add(operation, "path", name, "EP", "not a number", "abc", False, 404)


def balance_rule_cases(spec, builder):
    """BVA on BR1 (working days vs remaining balance), at submission and at approval."""
    rules = spec.get("x-business-rules", {})
    rule = rules.get("balance-limit")
    if not rule:
        return
    ops = {op["operationId"]: op for op in operations(spec)}
    create = ops["createLeaveRequest"]
    review = ops["reviewLeaveRequest"]

    for code, allocation in rule["allocations"].items():
        # stage 1: the request itself is A-1, A and A+1 working days long
        for label, days, valid in (
            ("allocation-1", allocation - 1, True),
            ("allocation", allocation, True),
            ("allocation+1", allocation + 1, False),
        ):
            builder.add(create, "rule", code, "BVA", "{} ({} days)".format(label, days),
                        {"working_days": days}, valid, 201 if valid else 422,
                        None if valid else "leave_type_id",
                        rule=rule["rule"], leave_type_code=code, allocation=allocation)

        # stage 2: approval re-checks the balance. A first request is approved,
        # then a 2-day request is reviewed with 3, 2 or 1 day(s) left.
        request_days = 2
        for label, remaining, valid in (
            ("remaining=need+1", request_days + 1, True),
            ("remaining=need", request_days, True),
            ("remaining=need-1", request_days - 1, False),
        ):
            prior = allocation - remaining
            builder.add(review, "rule", code, "BVA", "{} ({} left)".format(label, remaining),
                        {"prior_days": prior, "request_days": request_days},
                        valid, 200 if valid else 422,
                        None if valid else "leave_type_id",
                        rule=rule["rule"], leave_type_code=code, allocation=allocation)


def generate(spec_path):
    spec = yaml.safe_load(Path(spec_path).read_text(encoding="utf-8"))
    builder = CaseBuilder()
    baselines = {}

    for operation in operations(spec):
        invalid_status = operation.get("x-invalid-status", 422)
        schema = body_schema(spec, operation)
        if schema is not None:
            baselines[operation["operationId"]] = baseline_body(spec, operation)
            required = set(schema.get("required", []))
            builder.add(operation, "body", "(body)", "EP", "body is a JSON array",
                        [], False, 400)
            for name, prop in schema["properties"].items():
                field_cases(builder, operation, "body", name, prop,
                            name in required, invalid_status)

        for param in operation.get("parameters", []):
            if param["in"] == "path":
                path_cases(builder, operation, param)
                continue
            prop = dict(param["schema"])
            for key in ("x-role", "x-clamped"):
                if key in param:
                    prop[key] = param[key]
            before = len(builder.cases)
            field_cases(builder, operation, "query", param["name"], prop,
                        param.get("required", False), invalid_status)
            for case in builder.cases[before:]:
                case["role"] = prop.get("x-role", "employee")

    balance_rule_cases(spec, builder)

    ids = [case["id"] for case in builder.cases]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise ValueError("Duplicate case ids: " + ", ".join(duplicates))

    return {
        "generated_from": Path(spec_path).name,
        "spec_sha256": sha256_of(spec_path),
        "baselines": baselines,
        "cases": builder.cases,
    }


def compare(old, new):
    """Print what changed between two generated files, keyed by case id."""
    old_cases = {case["id"]: case for case in old["cases"]}
    new_cases = {case["id"]: case for case in new["cases"]}
    added = sorted(set(new_cases) - set(old_cases))
    removed = sorted(set(old_cases) - set(new_cases))
    changed = sorted(
        key for key in set(old_cases) & set(new_cases)
        if old_cases[key] != new_cases[key]
    )
    print("Cases before:", len(old_cases), " after:", len(new_cases))
    print("Added:", len(added))
    for key in added:
        print("  +", key, "->", new_cases[key]["expected_status"])
    print("Removed:", len(removed))
    for key in removed:
        print("  -", key, "->", old_cases[key]["expected_status"])
    print("Changed:", len(changed))
    for key in changed:
        print("  ~", key)
        for attr in sorted(set(old_cases[key]) | set(new_cases[key])):
            if old_cases[key].get(attr) != new_cases[key].get(attr):
                print("      ", attr + ":", old_cases[key].get(attr), "->", new_cases[key].get(attr))
    return added, removed, changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--compare", help="earlier cases.json to diff against")
    args = parser.parse_args(argv)

    result = generate(args.spec)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    by_technique = {}
    for case in result["cases"]:
        key = (case["operation"], case["technique"])
        by_technique[key] = by_technique.get(key, 0) + 1
    print("Wrote", len(result["cases"]), "cases to", out)
    for (operation, technique), count in sorted(by_technique.items()):
        print("  ", operation, technique, count)

    if args.compare:
        old = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        compare(old, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
