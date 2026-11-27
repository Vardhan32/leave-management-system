"""Records every API call the tests make and measures it against the spec.

Criteria (after Martin-Lopez, Segura and Ruiz-Cortes, "Test Coverage Criteria
for RESTful Web APIs", 2019):

  path            every path in the spec was called
  operation       every method on every path was called
  parameter       every query and path parameter was sent at least once
  parameter value every enum value of a parameter or body field was sent
  content type    every operation with a JSON body was called with JSON
  status class    every documented 2xx and 4xx class was seen per operation
  status code     every documented status code was seen per operation
  response body   every top-level property of every documented response
                  schema appeared in at least one response

Every response is also checked against its schema while the test runs, and a
status code the spec does not document fails the test straight away.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

from .schema_check import resolve, top_level_properties, validate

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


class SpecIndex:
    def __init__(self, spec):
        self.spec = spec
        self.operations = {}
        self.matchers = []
        for path, item in spec["paths"].items():
            pattern = "^" + re.sub(r"\{[^/]+\}", "[^/]+", path) + "$"
            self.matchers.append((re.compile(pattern), path))
            for method, operation in item.items():
                if method in HTTP_METHODS:
                    self.operations[(method.upper(), path)] = operation
        # literal paths before templated ones, so /api/leave-requests wins over
        # /api/leave-requests/{id} when both could match
        self.matchers.sort(key=lambda pair: pair[1].count("{"))

    def find(self, method, url_path):
        for regex, template in self.matchers:
            if regex.match(url_path) and (method, template) in self.operations:
                return template, self.operations[(method, template)]
        return None, None

    def response_schema(self, operation, status):
        response = operation["responses"].get(str(status))
        if response is None:
            return None, False
        response = resolve(self.spec, response)
        content = response.get("content", {}).get("application/json")
        return (content or {}).get("schema"), True


class CoverageTracker:
    def __init__(self, spec):
        self.index = SpecIndex(spec)
        self.calls = 0
        self.seen_ops = set()
        self.seen_status = defaultdict(set)
        self.seen_params = defaultdict(set)
        self.seen_values = defaultdict(set)
        self.seen_json_body = set()
        self.seen_properties = defaultdict(set)
        self.unmatched = []

    def record(self, method, url_path, query, body, status, payload):
        """Store one call and return a list of problems with the response."""
        self.calls += 1
        template, operation = self.index.find(method, url_path)
        if operation is None:
            self.unmatched.append("{} {}".format(method, url_path))
            return ["{} {} is not in the spec".format(method, url_path)]

        key = (method, template)
        self.seen_ops.add(key)
        self.seen_status[key].add(int(status))

        for param in operation.get("parameters", []):
            if param["in"] == "path":
                self.seen_params[key].add(param["name"])
            elif param["in"] == "query" and param["name"] in (query or {}):
                self.seen_params[key].add(param["name"])
                self.seen_values[(key, param["name"])].add(str(query[param["name"]]))

        if isinstance(body, dict):
            self.seen_json_body.add(key)
            for name, value in body.items():
                self.seen_values[(key, name)].add(str(value))
        elif body is not None:
            self.seen_json_body.add(key)

        schema, documented = self.index.response_schema(operation, status)
        if not documented:
            return ["status {} is not documented for {} {}".format(status, method, template)]
        if schema is None:
            return []
        problems = validate(self.index.spec, schema, payload)
        if isinstance(payload, dict):
            self.seen_properties[(key, int(status))].update(payload)
        return problems

    # -- reporting -----------------------------------------------------------
    def criteria(self):
        spec = self.index.spec
        rows = {}

        def ratio(name, covered, total, missing):
            rows[name] = {
                "covered": covered,
                "total": total,
                "percent": round(100.0 * covered / total, 1) if total else 100.0,
                "missing": sorted(missing),
            }

        paths = {template for _, template in self.index.operations}
        seen_paths = {template for _, template in self.seen_ops}
        ratio("path", len(paths & seen_paths), len(paths), paths - seen_paths)

        ops = set(self.index.operations)
        ratio("operation", len(ops & self.seen_ops), len(ops),
              {"{} {}".format(*op) for op in ops - self.seen_ops})

        params, missing_params = 0, set()
        values, missing_values = 0, set()
        bodies, missing_bodies = 0, set()
        classes, missing_classes = 0, set()
        codes, missing_codes = 0, set()
        props, missing_props = 0, set()

        for key, operation in self.index.operations.items():
            label = "{} {}".format(*key)
            for param in operation.get("parameters", []):
                params += 1
                if param["name"] not in self.seen_params[key]:
                    missing_params.add(label + " " + param["name"])
                enum = resolve(spec, param.get("schema", {})).get("enum")
                for item in enum or []:
                    values += 1
                    if item not in self.seen_values[(key, param["name"])]:
                        missing_values.add("{} {}={}".format(label, param["name"], item))

            if "requestBody" in operation:
                bodies += 1
                if key not in self.seen_json_body:
                    missing_bodies.add(label)
                schema = resolve(spec, operation["requestBody"]["content"]["application/json"]["schema"])
                for name, prop in schema.get("properties", {}).items():
                    for item in prop.get("enum", []):
                        values += 1
                        if item not in self.seen_values[(key, name)]:
                            missing_values.add("{} {}={}".format(label, name, item))

            documented = {int(code) for code in operation["responses"]}
            for status_class in {code // 100 for code in documented}:
                classes += 1
                if not any(code // 100 == status_class for code in self.seen_status[key]):
                    missing_classes.add("{} {}xx".format(label, status_class))
            for code in documented:
                codes += 1
                if code not in self.seen_status[key]:
                    missing_codes.add("{} {}".format(label, code))
                schema, _ = self.index.response_schema(operation, code)
                if schema is not None:
                    for name in top_level_properties(spec, schema):
                        props += 1
                        if name not in self.seen_properties[(key, code)]:
                            missing_props.add("{} {} .{}".format(label, code, name))

        ratio("parameter", params - len(missing_params), params, missing_params)
        ratio("parameter value", values - len(missing_values), values, missing_values)
        ratio("content type", bodies - len(missing_bodies), bodies, missing_bodies)
        ratio("status code class", classes - len(missing_classes), classes, missing_classes)
        ratio("status code", codes - len(missing_codes), codes, missing_codes)
        ratio("response body property", props - len(missing_props), props, missing_props)
        return rows

    def write_reports(self, folder):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        rows = self.criteria()
        observed = {
            "{} {}".format(*key): sorted(codes) for key, codes in sorted(self.seen_status.items())
        }
        (folder / "api_coverage.json").write_text(
            json.dumps({"calls": self.calls, "criteria": rows, "observed_status": observed,
                        "unmatched_calls": self.unmatched}, indent=2) + "\n",
            encoding="utf-8",
        )

        lines = [
            "# API coverage",
            "",
            "Generated by tests/team/api/support/api_coverage.py from {} calls.".format(self.calls),
            "",
            "| Criterion | Covered | Total | % |",
            "| --- | --- | --- | --- |",
        ]
        for name, row in rows.items():
            lines.append("| {} | {} | {} | {} |".format(name, row["covered"], row["total"], row["percent"]))
        lines.append("")
        for name, row in rows.items():
            if row["missing"]:
                lines.append("## Not covered: " + name)
                lines.extend("- " + item for item in row["missing"])
                lines.append("")
        lines.append("## Status codes observed per operation")
        lines.extend("- {}: {}".format(op, ", ".join(str(code) for code in codes))
                     for op, codes in observed.items())
        (folder / "api_coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return rows
