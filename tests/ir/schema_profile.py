"""Lint subset Dictum dan resolusi Draft 2020-12 di registry lokal."""

import re

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource

from wire import MAX_INTEGER, MAX_ITEMS, MAX_MEMBERS, MAX_STRING


DIALECT = "https://json-schema.org/draft/2020-12/schema"
ID_PREFIX = "https://dictum.invalid/spec/ir/"
NAME = re.compile(r"[a-z][a-z0-9_]*", re.ASCII)
PATTERNS = {
    "^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+(?![\\s\\S])",
    "^[a-z][a-z0-9_]*(?![\\s\\S])",
    "^[0-9a-f]{32}(?![\\s\\S])",
    "^[0-9a-f]{64}(?![\\s\\S])",
    "^[A-Za-z0-9_][A-Za-z0-9_.:@-]*(?![\\s\\S])",
    "^/",
    "^--?[A-Za-z0-9][A-Za-z0-9-]*(?![\\s\\S])",
}
KEYWORDS = {
    "object": {"required", "properties", "additionalProperties"},
    "array": {"minItems", "maxItems", "items"},
    "string": {"minLength", "maxLength", "pattern", "enum", "const"},
    "integer": {"minimum", "maximum", "const"},
}


class ProfileError(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise ProfileError(message)


def inspect_profile(schemas):
    """Kembalikan semua edge ref yang harus di-resolve oleh registry."""
    active, seen = set(), set()
    references = []

    def target(filename, pointer):
        host, separator, definition = pointer.partition("#/$defs/")
        destination = host or filename
        check(separator and NAME.fullmatch(definition), f"Pointer lokal tidak didukung {pointer}")
        check(destination in schemas, f"Ref di luar registry {pointer}")
        check(definition in schemas[destination].get("$defs", {}), f"Definisi tidak ditemukan {pointer}")
        return destination, definition

    def expand(filename, node):
        while "$ref" in node:
            filename, definition = target(filename, node["$ref"])
            node = schemas[filename]["$defs"][definition]
        return node

    def walk(filename, node, path):
        marker = filename, path
        check(marker not in active, f"Siklus schema {filename} {path}")
        if marker in seen:
            return
        active.add(marker)
        check(isinstance(node, dict), f"Subschema harus objek {filename} {path}")
        if not path:
            check(node.get("$schema") == DIALECT and node.get("$id") == ID_PREFIX + filename,
                  f"Identitas schema keliru {filename}")
            check(node.get("type") == "object", f"Root harus objek {filename}")
            for name, definition in node.get("$defs", {}).items():
                check(NAME.fullmatch(name), f"Nama definisi keliru {filename} {name}")
                walk(filename, definition, ("$defs", name))
            node = {key: value for key, value in node.items()
                    if key not in {"$schema", "$id", "$defs", "title"}}

        if "$ref" in node:
            check(set(node) == {"$ref"}, f"Keyword di samping ref {filename} {path}")
            pointer = node["$ref"]
            destination, definition = target(filename, pointer)
            child = schemas[destination]["$defs"][definition]
            references.append((filename, pointer, child))
            walk(destination, child, ("$defs", definition))
        elif "oneOf" in node:
            check(set(node) == {"oneOf"}, f"Keyword di samping oneOf {filename} {path}")
            tags = set()
            for index, branch in enumerate(node["oneOf"]):
                walk(filename, branch, (*path, "oneOf", index))
                expanded = expand(filename, branch)
                tag = expanded.get("properties", {}).get("kind", {}).get("const")
                check(expanded.get("type") == "object" and "kind" in expanded["required"]
                      and isinstance(tag, str) and tag not in tags,
                      f"Cabang oneOf perlu kind const unik {filename} {path}")
                tags.add(tag)
        else:
            kind = node.get("type")
            check(isinstance(kind, str) and kind in KEYWORDS, f"Tipe di luar profil {filename} {path}")
            check(set(node) <= KEYWORDS[kind] | {"type"}, f"Keyword di luar profil {filename} {path}")
            if kind == "object":
                props = node.get("properties", {})
                check(set(node) == KEYWORDS[kind] | {"type"} and node["additionalProperties"] is False,
                      f"Objek harus tertutup {filename} {path}")
                check(len(props) <= MAX_MEMBERS and set(node["required"]) <= props.keys(),
                      f"Properti objek di luar profil {filename} {path}")
                for name, child in props.items():
                    check(NAME.fullmatch(name), f"Nama properti di luar profil {filename} {name}")
                    walk(filename, child, (*path, "properties", name))
            elif kind == "array":
                check(set(node) == KEYWORDS[kind] | {"type"} and
                      all(type(node[key]) is int for key in ("minItems", "maxItems")) and
                      0 <= node["minItems"] <= node["maxItems"] <= MAX_ITEMS,
                      f"Batas array di luar profil {filename} {path}")
                walk(filename, node["items"], (*path, "items"))
            elif "const" in node:
                value = node["const"]
                check(set(node) == {"type", "const"} and
                      ((kind == "string" and isinstance(value, str) and value.isascii()
                        and 1 <= len(value) <= MAX_STRING) or
                       (kind == "integer" and type(value) is int and abs(value) <= MAX_INTEGER)),
                      f"Const di luar profil {filename} {path}")
            elif kind == "integer":
                check(set(node) == {"type", "minimum", "maximum"} and
                      all(type(node[key]) is int for key in ("minimum", "maximum")) and
                      -MAX_INTEGER <= node["minimum"] <= node["maximum"] <= MAX_INTEGER,
                      f"Batas integer di luar profil {filename} {path}")
            elif "enum" in node:
                values = node["enum"]
                check(set(node) == {"type", "enum"} and all(isinstance(value, str) and
                      value.isascii() and 1 <= len(value) <= MAX_STRING for value in values) and
                      len(values) == len(set(values)), f"Enum di luar profil {filename} {path}")
            else:
                check(all(type(node.get(key)) is int for key in ("minLength", "maxLength")) and
                      0 <= node["minLength"] <= node["maxLength"] <= MAX_STRING
                      and ("pattern" not in node or node["pattern"] in PATTERNS),
                      f"Batas string atau pattern di luar profil {filename} {path}")

        active.remove(marker)
        seen.add(marker)

    for filename, schema in schemas.items():
        walk(filename, schema, ())
    return references


def prepare_validators(schemas):
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    references = inspect_profile(schemas)
    retrieval_attempts = []

    def refuse_retrieval(uri):
        retrieval_attempts.append(uri)
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=refuse_retrieval).with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    for filename, pointer, expected in references:
        result = registry.resolver(ID_PREFIX + filename).lookup(pointer)
        check(result.contents is expected, f"Target ref tidak cocok {filename} {pointer}")
    validators = {filename: Draft202012Validator(schema, registry=registry)
                  for filename, schema in schemas.items()}
    return validators, len(references), retrieval_attempts
