"""A4 data-only reference; synthetic recipes, never invokes a shell."""
import json
import re
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHELLS = {"bash-posix-clean-v1", "dash-clean-v1"}
IDENTITY = {"path": "/fixture/bin/argv-dumper", "version": "fixture-v1",
            "sha256": "a" * 64}
INVISIBLE = [(0x034F, 0x034F), (0x115F, 0x1160), (0x17B4, 0x17B5),
             (0x180B, 0x180F), (0x3164, 0x3164), (0xFE00, 0xFE0F),
             (0xFFA0, 0xFFA0), (0xE0100, 0xE01EF)]


class Reject(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Reject(reason)


def check_token(value):
    need(type(value) is str, "atom-type")
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise Reject("utf8") from exc
    need(len(raw) <= 1024, "token-size")
    for ch in value:
        n = ord(ch)
        need(not (0xFDD0 <= n <= 0xFDEF or n & 0xFFFF >= 0xFFFE),
             "noncharacter")
        need(unicodedata.category(ch) not in {"Cc", "Cf", "Zl", "Zp"}
             and not any(a <= n <= b for a, b in INVISIBLE), "unsafe-character")
    return value


def atom(x):
    need(type(x) is dict, "atom-type")
    kind = x.get("kind")
    if kind == "option-end":
        need(set(x) == {"kind"}, "atom-shape")
        return "--"
    need(set(x) == {"kind", "value"}, "atom-shape")
    v = x["value"]
    if kind == "integer":
        need(type(v) is int and -(2**53-1) <= v <= 2**53-1, "integer")
        return str(v)
    if kind == "flag":
        need(type(v) is str and re.fullmatch(r"--?[A-Za-z0-9][A-Za-z0-9-]*", v),
             "flag-syntax")
    else:
        need(kind == "literal", "atom-type")
    return check_token(v)


def quote(value):
    return "'" + value.replace("'", "'\\''") + "'"


def render(case):
    """gate/recipe are harness-selected synthetic inputs, not model authority."""
    try:
        need(case["shell"] in SHELLS, "unsupported-shell")
        need(case["gate"] == "verified-fixture", "unverified-binding")
        action = case["action"]
        need(action["kind"] == "proposal-only", "non-executable-action")
        need(set(action) == {"kind", "operation"}, "action-shape")
        op = action["operation"]
        need(set(op) == {"kind", "identity", "argv"} and op["kind"] == "executable",
             "operation-shape")
        need(op["identity"] == IDENTITY, "identity")
        executable = check_token(op["identity"]["path"])
        need(executable.startswith("/"), "identity")
        args = op["argv"]
        need(type(args) is list and len(args) <= 32, "argv-count")
        vals = [atom(a) for a in args]
        kinds = [a["kind"] for a in args]
        recipe = case["recipe"]
        if recipe == "fixture-end":
            need(len(args) >= 2 and kinds[0] == "option-end"
                 and all(k == "literal" for k in kinds[1:]), "operand-binding")
            need("-" not in vals[1:], "stdin-operand")
        elif recipe == "fixture-no-end":
            need(kinds == ["literal"] and vals[0] and not vals[0].startswith("-"),
                 "operand-binding")
        elif recipe == "fixture-limit":
            need(kinds == ["flag", "integer", "option-end", "literal"] and
                 vals[0] == "--limit", "operand-binding")
            need(1 <= args[1]["value"] <= 4, "limit")
            need(vals[3] not in {"", "-"}, "stdin-operand")
        else:
            raise Reject("unknown-recipe")
        preview = " ".join(quote(t) for t in [executable, *vals])
        need(len(preview.encode("utf-8")) <= 32768, "preview-size")
        return {"kind": "COPYABLE", "preview": preview}
    except Reject as exc:
        return {"kind": "NON_COPYABLE", "reason": str(exc)}


def main():
    data = json.loads((HERE / "fixtures/preview-v1.json").read_text(encoding="utf-8"))
    ids = set()
    count = 0
    bad = 0
    accepted = 0
    for c in data["cases"]:
        need(c["id"] not in ids, "duplicate-case")
        ids.add(c["id"])
        result = render(c)
        expected = c["expected"]
        if expected["kind"] == "COPYABLE":
            accepted += 1
        ok = result == expected and ("preview" not in result or
                                     result["kind"] == "COPYABLE")
        if result["kind"] == "NON_COPYABLE":
            ok = ok and set(result) == {"kind", "reason"} and "CANARY_SECRET" not in json.dumps(result)
        bad += not ok
        count += 1
        print(f"{'PASS' if ok else 'FAIL'} {c['id']} expected={expected['kind']} actual={result['kind']}")
    # Invalid UTF-8 is a byte-layer negative; never pass it to JSON/shell.
    for sample in data["invalid_utf8_hex"]:
        try:
            bytes.fromhex(sample).decode("utf-8", errors="strict")
            ok = False
        except UnicodeDecodeError:
            ok = True
        bad += not ok
        count += 1
        print(f"{'PASS' if ok else 'FAIL'} invalid-utf8-{sample}")
    need(count == data["expected_count"], "case-count")
    print(f"Unicode database: {unicodedata.unidata_version}")
    print(f"A4 data-only: {count-bad}/{count}, {accepted} copyable golden, {count-accepted} negative/byte; S1 NOT RUN")
    return bool(bad)


if __name__ == "__main__":
    raise SystemExit(main())
