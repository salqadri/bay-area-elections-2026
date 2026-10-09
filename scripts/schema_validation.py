"""Focused schema-keyword checks, not a certified general JSON Schema validator.

The runtime has no Draft 2020-12 validator package. This local checker implements
every assertion keyword actually used in elections.schema.json, checks the
current data, and exercises malformed examples. A downstream consumer should
also validate with a standard Draft 2020-12 implementation.
"""
import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((HERE / "elections.schema.json").read_text())
ANNOTATIONS = {"$schema", "$comment", "title", "description", "$defs"}
ASSERTIONS = {"$ref", "type", "additionalProperties", "properties", "required", "minLength", "maxLength", "minItems", "maxItems", "uniqueItems", "items", "oneOf", "anyOf", "allOf", "not", "if", "then", "else", "const", "enum", "minimum", "pattern", "patternProperties", "propertyNames", "minProperties", "dependentRequired", "format"}
SEEN = set()


def scan_schema(node):
    if isinstance(node, bool):
        return
    unknown = set(node) - ANNOTATIONS - ASSERTIONS
    assert not unknown, f"Unsupported schema keywords: {unknown}"
    SEEN.update(node)
    for key in ["$defs", "properties", "patternProperties"]:
        for value in node.get(key, {}).values():
            scan_schema(value)
    for key in ["items", "propertyNames", "if", "then", "else", "not", "additionalProperties"]:
        if isinstance(node.get(key), (dict, bool)):
            scan_schema(node[key])
    for key in ["anyOf", "oneOf", "allOf"]:
        for value in node.get(key, []):
            scan_schema(value)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def istype(value, typename):
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }[typename]


def check(value, schema, path="$", root=SCHEMA):
    if isinstance(schema, bool):
        return [] if schema else [f"{path}: false schema"]
    errors = []
    if "$ref" in schema:
        target = root
        assert schema["$ref"].startswith("#/"), "Only internal refs are supported"
        for part in schema["$ref"][2:].split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        errors.extend(check(value, target, path, root))
    for sub in schema.get("allOf", []):
        errors.extend(check(value, sub, path, root))
    for name in ["anyOf", "oneOf"]:
        if name in schema:
            valid = sum(not check(value, sub, path, root) for sub in schema[name])
            if (name == "anyOf" and valid == 0) or (name == "oneOf" and valid != 1):
                errors.append(f"{path}: {name} matched {valid} branches")
    if "not" in schema and not check(value, schema["not"], path, root):
        errors.append(f"{path}: matched prohibited schema")
    if "if" in schema:
        branch = "then" if not check(value, schema["if"], path, root) else "else"
        if branch in schema:
            errors.extend(check(value, schema[branch], path, root))
    if "const" in schema and canonical(value) != canonical(schema["const"]):
        errors.append(f"{path}: incorrect const")
    if "enum" in schema and canonical(value) not in {canonical(v) for v in schema["enum"]}:
        errors.append(f"{path}: value not in enum")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(istype(value, t) for t in types):
            errors.append(f"{path}: wrong type {type(value).__name__}, expected {types}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required {key}")
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path}: too few properties")
        properties = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for key, item in value.items():
            known = False
            if "propertyNames" in schema:
                errors.extend(check(key, schema["propertyNames"], path + "(key)", root))
            if key in properties:
                known = True
                errors.extend(check(item, properties[key], path + "." + key, root))
            for pattern, sub in patterns.items():
                if re.search(pattern, key):
                    known = True
                    errors.extend(check(item, sub, path + "." + key, root))
            if not known and "additionalProperties" in schema:
                errors.extend(check(item, schema["additionalProperties"], path + "." + key, root))
        for key, dependencies in schema.get("dependentRequired", {}).items():
            if key in value:
                for dependency in dependencies:
                    if dependency not in value:
                        errors.append(f"{path}: {key} requires {dependency}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: too many items")
        if schema.get("uniqueItems") and len(value) != len({canonical(v) for v in value}):
            errors.append(f"{path}: duplicate items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(check(item, schema["items"], f"{path}[{index}]", root))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: string too long")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: pattern mismatch")
        if schema.get("format") == "date":
            try:
                datetime.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: invalid calendar date")
        if schema.get("format") == "iso-8601-partial":
            # YYYY, YYYY-MM or YYYY-MM-DD must name a real day/month/year
            try:
                parts = value.split("-")
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                if not (1 <= month <= 12 and 1 <= day <= 31):
                    raise ValueError
                # Also validate year-only dates; year 0000 is not a calendar year.
                datetime.date(year, month, day)
            except (ValueError, IndexError):
                errors.append(f"{path}: invalid calendar date")
        if schema.get("format") == "uri":
            # The schema restricts URI fields to HTTP(S); this validates the
            # applicable subset rather than the full RFC 3986 URI grammar.
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or re.search(r"\s", value):
                errors.append(f"{path}: invalid HTTP(S) URI")
    if istype(value, "number") and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: value below minimum")
    return errors

