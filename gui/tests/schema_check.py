"""Minimal JSON Schema checker for the contract files (the subset they use).

Supports: type, const, enum, required, properties, items, prefixItems,
minItems, minLength, minimum, anyOf and local $ref. Standard library only.
"""
import json
from pathlib import Path

CONTRACT = Path(__file__).resolve().parents[1] / "contract"
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def load(name):
    return json.loads((CONTRACT / name).read_text(encoding="utf-8"))


def _is_type(value, t):
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[t])


def errors(value, schema, root=None, path="$"):
    root = root or schema
    out = []
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return errors(value, node, root, path)
    if "anyOf" in schema:
        if not any(not errors(value, s, root, path) for s in schema["anyOf"]):
            out.append(f"{path}: matches none of anyOf")
        return out
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        if not any(_is_type(value, x) for x in types):
            return [f"{path}: expected {t}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        out.append(f"{path}: too short")
    if isinstance(value, (int, float)) and "minimum" in schema and value < schema["minimum"]:
        out.append(f"{path}: below minimum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}: missing {key}")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                out += errors(value[key], sub, root, f"{path}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append(f"{path}: too few items")
        prefix = schema.get("prefixItems", [])
        for i, item in enumerate(value):
            if i < len(prefix):
                out += errors(item, prefix[i], root, f"{path}[{i}]")
            elif "items" in schema:
                out += errors(item, schema["items"], root, f"{path}[{i}]")
    return out
