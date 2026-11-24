"""A6 detached manifest wire oracle. No crypto, trusted installer or release loader."""
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.exceptions import NoSuchResource
from run import validate, Reject, need

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
MAX_WIRE = 32768
MAX_INT = 9007199254740991
DEV_PIN = "c8cbddc1f0aece4f0fdf93d0e07d9803497f34a8d6bafc507a0eff3a7c7f48c6"
CATALOG_BYTES = b"dictum-synthetic-catalog-v1"
POLICY_BYTES = b"abc"  # inert marker, not a policy implementation


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_wire(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_WIRE, "manifest-size")
    need(b"\x00" not in raw, "manifest-nul")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise Reject("manifest-utf8") from exc
    depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            need(depth <= 8, "manifest-depth")
        elif ch in "]}":
            depth -= 1
            need(depth >= 0, "manifest-json")
    need(depth == 0 and not in_string, "manifest-json")

    def pairs(values):
        result = {}
        for key, value in values:
            need(key not in result, "manifest-duplicate")
            result[key] = value
        return result

    def integer(value):
        need(value.isascii() and value.isdecimal() and len(value) <= 16,
             "manifest-number")
        n = int(value)
        need(0 <= n <= MAX_INT, "manifest-number")
        return n

    def reject_number(_):
        raise Reject("manifest-number")

    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                          parse_float=reject_number, parse_constant=reject_number)
    except json.JSONDecodeError as exc:
        raise Reject("manifest-json") from exc
    need(type(data) is dict, "manifest-object")
    return data


def version(v):
    return v["major"], v["minor"], v["patch"]


def make_validator():
    schema = strict_wire((ROOT/"spec/model-pack/manifest-v1.schema.json").read_bytes())
    Draft202012Validator.check_schema(schema)
    attempted = []
    def deny(uri):
        attempted.append(uri)
        raise NoSuchResource(ref=uri)
    return Draft202012Validator(schema, registry=Registry(retrieve=deny)), attempted


def shape(raw, validator):
    data = strict_wire(raw)
    need(validator.is_valid(data), "manifest-schema")
    dev = data["role"] == "synthetic-test-only"
    need((data["architecture"]["id"] == 0x7fffffff) == dev,
         "manifest-role-profile")
    comp = data["compatibility"]
    need(version(comp["runtime_min"]) <= version(comp["runtime_max"]),
         "manifest-version-order")
    return data


def binding(raw, pack, validator):
    """Only the pinned synthetic shape can be checked; never authenticates."""
    data = shape(raw, validator)
    need(data["role"] == "synthetic-test-only" and
         data["publisher_key_id"] == "dev-fixture-a6", "manifest-role-key")
    info = validate(pack)
    need(data["pack"] == {"sha256":info["sha256"], "length":len(pack),
                         "major":1,"minor":0}, "manifest-pack")
    need(data["architecture"] == {"id":0x7fffffff,"profile_version":1},
         "manifest-profile")
    need(data["tokenizer"] == {"sha256":info["tokenizer_sha256"],
                              "length":30,"kind":1,"version":1}, "manifest-tokenizer")
    need(data["catalog"] == {"sha256":sha(CATALOG_BYTES),"length":len(CATALOG_BYTES),
                             "version":1} and data["catalog"]["sha256"] ==
         info["catalog_sha256"], "manifest-catalog")
    need(data["policy"] == {"sha256":sha(POLICY_BYTES),"length":len(POLICY_BYTES),
                            "version":1}, "manifest-policy")
    comp = data["compatibility"]
    need(version(comp["runtime_min"]) <= (0,1,0) <= version(comp["runtime_max"]),
         "manifest-runtime")
    return "SYNTHETIC-BINDING-ONLY"


def main():
    validator, attempted = make_validator()
    raw = (FIXTURES/"unsigned-dev-manifest.json").read_bytes()
    pack = bytes.fromhex(json.loads((FIXTURES/"dctm-v1.json").read_text())["pack_hex"])
    original = strict_wire(raw)
    checks = []
    def check(name, expected, fn):
        actual = "ok"
        try:
            fn()
        except Reject as exc:
            actual = str(exc)
        checks.append((name,actual == expected))
        print(f"{'PASS' if actual == expected else 'FAIL'} {name}: {actual} expected {expected}")
    def encode(obj):
        return json.dumps(obj,ensure_ascii=True,separators=(",",":")).encode()
    check("manifest-golden-pin","ok",lambda:need(
        sha(raw) == DEV_PIN and binding(raw,pack,validator) == "SYNTHETIC-BINDING-ONLY",
        "manifest-golden"))
    check("same-object-different-bytes","ok",lambda:need(
        strict_wire(raw+b"\n") == original and sha(raw+b"\n") != DEV_PIN,
        "manifest-byte-identity"))
    for name, payload, expected in [
        ("duplicate-root", raw.replace(b'"schema_version": 1',b'"schema_version":1,"schema_version":1',1), "manifest-duplicate"),
        ("duplicate-nested", raw.replace(b'"profile_version": 1',b'"profile_version":1,"profile_version":1',1), "manifest-duplicate"),
        ("invalid-utf8", b"\xff"+raw, "manifest-utf8"),
        ("raw-nul", raw+b"\0", "manifest-nul"),
        ("bom", b"\xef\xbb\xbf"+raw, "manifest-json"),
        ("trailing", raw+b"{}", "manifest-json"),
        ("float", raw.replace(b'"schema_version": 1',b'"schema_version":1.0',1), "manifest-number"),
        ("exponent", raw.replace(b'"schema_version": 1',b'"schema_version":1e0',1), "manifest-number"),
        ("nonfinite", raw.replace(b'"schema_version": 1',b'"schema_version":NaN',1), "manifest-number"),
        ("negative-zero", raw.replace(b'"schema_version": 1',b'"schema_version":-0',1), "manifest-number"),
        ("oversized-int", raw.replace(b'"release_sequence": 1',b'"release_sequence":9007199254740992',1), "manifest-number"),
        ("depth", b"["*9+b"0"+b"]"*9, "manifest-depth"),
        ("oversize", b" "*32769, "manifest-size"),
        ("not-object", b"[]", "manifest-object"),
    ]:
        check(name,expected,lambda payload=payload:shape(payload,validator))
    mutations = [
        ("unknown-field",["signature"],"faked","manifest-schema"),
        ("unknown-nested",["pack","executable"],True,"manifest-schema"),
        ("unknown-role",["role"],"other","manifest-schema"),
        ("role-profile",["role"],"release-model-pack","manifest-role-profile"),
        ("key-invalid",["publisher_key_id"],"bad key","manifest-schema"),
        ("key-mismatch",["publisher_key_id"],"different-fixture","manifest-role-key"),
        ("hash-uppercase",["pack","sha256"],"A"*64,"manifest-schema"),
        ("hash-short",["pack","sha256"],"a"*63,"manifest-schema"),
        ("pack-digest",["pack","sha256"],"0"*64,"manifest-pack"),
        ("pack-length",["pack","length"],601,"manifest-pack"),
        ("pack-major",["pack","major"],2,"manifest-schema"),
        ("bool-version",["pack","major"],True,"manifest-schema"),
        ("profile-version",["architecture","profile_version"],2,"manifest-profile"),
        ("tokenizer-digest",["tokenizer","sha256"],"0"*64,"manifest-tokenizer"),
        ("tokenizer-length",["tokenizer","length"],31,"manifest-tokenizer"),
        ("catalog-digest",["catalog","sha256"],"0"*64,"manifest-catalog"),
        ("catalog-length",["catalog","length"],1,"manifest-catalog"),
        ("policy-digest",["policy","sha256"],"0"*64,"manifest-policy"),
        ("policy-length",["policy","length"],1,"manifest-policy"),
        ("version-order",["compatibility","runtime_min","major"],1,"manifest-version-order"),
        ("runtime-outside",["compatibility","runtime_min","patch"],1,"manifest-runtime"),
        ("platform",["compatibility","platform"],"unknown","manifest-schema"),
        ("sequence",["release_sequence"],0,"manifest-schema"),
    ]
    for name,path,value,expected in mutations:
        candidate = copy.deepcopy(original)
        target = candidate
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        check(name,expected,lambda candidate=candidate:binding(encode(candidate),pack,validator))
    release_shape = copy.deepcopy(original)
    release_shape["role"] = "release-model-pack"
    release_shape["architecture"]["id"] = 1
    check("release-shape-not-authentication","manifest-role-key",
          lambda:binding(encode(release_shape),pack,validator))
    check("local-schema-only","ok",lambda:need(not attempted,"manifest-retrieval"))
    need(len(checks) == len({name for name,_ in checks}),"duplicate-case")
    passed = sum(ok for _,ok in checks)
    print(f"A6 manifest contract: {passed}/{len(checks)}; signature enforcement NOT RUN")
    return passed != len(checks)


if __name__ == "__main__":
    raise SystemExit(main())
