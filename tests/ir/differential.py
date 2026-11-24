"""Compare native stage/decoded value/spans to the independent Python oracle."""
import json
import random
import subprocess
import sys
from collections import Counter
from run import SCHEMAS, SCHEMA_DIR, fixture, edit, sample_bytes
from schema_profile import prepare_validators
from wire import Reject, check_input, decode_frame, read_source

SEED = 23004


def encode(value, **kwargs):
    return json.dumps(value, **kwargs).encode("utf-8")


def oracle(mode, data, validators):
    try:
        if mode == "input":
            check_input(data)
            return "ok", None
        obj = decode_frame(data)
        if mode != "raw" and not validators[SCHEMAS[mode]].is_valid(obj):
            return "schema/structure", None
        return "ok", obj
    except Reject as exc:
        return str(exc), None


def inspect(lines, data, obj):
    # Verify every raw span by re-decoding the exact slice independently.
    # For objects, preserve key order (including their raw spans).
    it = iter(lines)

    def visit(value):
        kind, start, end, *rest = next(it).split(" ")
        kind, start, end = int(kind), int(start), int(end)
        assert 0 <= start < end <= len(data)
        decoded = decode_frame(data[start:end])
        assert type(decoded) is type(value) and decoded == value
        expected_kind = {dict: 0, list: 1, str: 2, int: 3, bool: 4 if value is True else 5,
                         type(None): 6}[type(value)]
        assert kind == expected_kind
        if isinstance(value, str):
            assert int(rest[0]) == len(value)
            assert bytes.fromhex(rest[1]) == value.encode("utf-8")
        elif type(value) is int:
            assert int(rest[0]) == value
        elif isinstance(value, (dict, list)):
            assert int(rest[0]) == len(value)
            children = []
            if isinstance(value, dict):
                for key, child in value.items():
                    children.extend((visit(key), visit(child)))
            else:
                children = [visit(child) for child in value]
            previous = start
            for a, b in children:
                assert previous < a < b < end
                previous = b - 1
        return start, end

    start, end = visit(obj)
    assert not data[:start].strip(b" \t\r\n") and not data[end:].strip(b" \t\r\n")
    assert next(it, None) is None


def main():
    validators, _, retrievals = prepare_validators(
        {name: read_source(SCHEMA_DIR / name) for name in SCHEMAS.values()})
    stats = Counter()
    seen = set()
    failures = []
    rng = random.Random(SEED)

    def case(label, mode, data, gold=None, strict=True):
        key = mode, data
        if key in seen:
            return
        seen.add(key)
        expected, obj = oracle(mode, data, validators)
        stats[mode, "positive" if expected == "ok" else "negative"] += 1
        # Multi-violation fuzz: only compare byte/schema/acceptance layer.
        def normalize(s):
            return s if strict or not s.startswith("byte/") else "byte"
        try:
            result = subprocess.run([sys.argv[1], mode], input=data, capture_output=True, timeout=5)
            assert result.returncode == 0 and not result.stderr, (result.returncode, result.stderr[:300])
            actual, *lines = result.stdout.decode("ascii").splitlines()
            assert gold is None or gold == expected, (gold, expected)
            assert normalize(actual) == normalize(expected), (expected, actual)
            if actual == "ok" and mode != "input":
                inspect(lines, data, obj)
            else:
                assert not lines
        except (AssertionError, ValueError, StopIteration, subprocess.TimeoutExpired) as exc:
            failures.append(label)
            print("FAIL", label, mode, repr(exc), "payload_hex=", data[:512].hex(),
                  "size=", len(data))

    for raw in fixture("raw"):
        case(raw["id"], raw.get("target", "raw"), sample_bytes(raw), raw["expect"])
    chains = {x["id"]: x for x in fixture("chains")["chains"]}
    for name, chain in chains.items():
        for stage, obj in chain["objects"].items():
            case(name + stage, stage, encode(obj, ensure_ascii=False), "ok")
            case(name + stage + "-reordered", stage, encode(obj, sort_keys=True, ensure_ascii=True), "ok")
    for schema in fixture("schema"):
        stage = schema["stage"]
        obj = edit(chains[schema["base"]]["objects"][stage], schema["edits"])
        case(schema["id"], stage, encode(obj), schema["expect"])
    for i in range(256):
        # Mutate synthetic valid frames, never use production data.
        data = bytearray(encode(rng.choice(list(chains.values()))["objects"]["nlu"]))
        for _ in range(rng.randrange(1, 5)):
            pos = rng.randrange(len(data))
            data[pos] = rng.randrange(256)
        case(f"mutation-{i}", "nlu", bytes(data), strict=False)
    for i, data in enumerate((b'""', b'{"":""}', b'null', b'true', b'false',
                              b'{"x":"\\u0061","y":"a"}', b'{"x":"\\ud83d\\ude42"}')):
        case(f"typed-{i}", "raw", data, "ok")
    print("seed", SEED, "unique", len(seen), "counts", sorted(stats.items()),
          "failures", len(failures), "retrievals", len(retrievals))
    return int(bool(failures or retrievals or len(seen) < 100))


if __name__ == "__main__":
    sys.exit(main())
