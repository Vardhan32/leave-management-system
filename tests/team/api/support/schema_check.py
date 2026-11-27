"""A small response checker for the subset of OpenAPI 3.0 schemas used in our spec.

It supports $ref, type, nullable, required, properties, items and enum.
That is enough to catch a missing field, a wrong type or an unexpected enum
value in a response, without adding another dependency.
"""

TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
}


def resolve(spec, schema):
    while isinstance(schema, dict) and "$ref" in schema:
        target = spec
        for part in schema["$ref"].lstrip("#/").split("/"):
            target = target[part]
        schema = target
    return schema


def type_matches(expected, value):
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[expected])


def validate(spec, schema, value, where="$"):
    """Return a list of problems. An empty list means the value fits the schema."""
    schema = resolve(spec, schema)
    problems = []

    if value is None:
        if not schema.get("nullable", False):
            problems.append(where + ": null is not allowed")
        return problems

    expected = schema.get("type")
    if expected and not type_matches(expected, value):
        problems.append("{}: expected {}, got {}".format(where, expected, type(value).__name__))
        return problems

    if "enum" in schema and value not in schema["enum"]:
        problems.append("{}: {!r} is not one of {}".format(where, value, schema["enum"]))

    if expected == "object":
        for name in schema.get("required", []):
            if name not in value:
                problems.append("{}: missing required property {}".format(where, name))
        for name, sub in schema.get("properties", {}).items():
            if name in value:
                problems.extend(validate(spec, sub, value[name], where + "." + name))

    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            problems.extend(validate(spec, schema["items"], item, "{}[{}]".format(where, index)))

    return problems


def top_level_properties(spec, schema):
    schema = resolve(spec, schema)
    return set(schema.get("properties", {}))
