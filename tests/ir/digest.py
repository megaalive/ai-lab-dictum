"""Independent SHA-256 and JCS oracle for the closed plan schema subset."""
import hashlib
import json
import random
import subprocess
import sys
from copy import deepcopy
from run import fixture

probe = sys.argv[1]
rng = random.Random(23009)
count = 0


def invoke(mode, data):
    global count
    count += 1
    p = subprocess.run([probe, mode], input=data, capture_output=True, timeout=5, check=True)
    assert not p.stderr
    return p.stdout.decode("ascii").strip()


for size in [0, 1, 3, 55, 56, 63, 64, 65, 119, 120, 127, 128, 129, 1024, 32768]:
    data = rng.randbytes(size)
    assert invoke("hash", data) == hashlib.sha256(data).hexdigest()
assert invoke("hash", b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def digest(plan):
    unsigned = {k: v for k, v in plan.items() if k != "digest"}
    # For this profile, all keys ASCII, strings scalars, integers exact,
    # and the standard encoder's escapes coincide with JCS.
    canon = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(b"dictum:execution-plan:v1\n" + canon.encode()).hexdigest()


def check(plan):
    plan = deepcopy(plan)
    expected = digest(plan)
    plan["digest"] = expected
    for ascii_only, sort in [(False, False), (True, True)]:
        data = json.dumps(plan, ensure_ascii=ascii_only, sort_keys=sort, indent=2).encode()
        assert invoke("digest", data) == expected + " match"
    plan["action_id"] = "9" * 32
    assert invoke("digest", json.dumps(plan).encode()) == digest(plan) + " mismatch"
    plan["unknown"] = 0
    assert invoke("digest", json.dumps(plan).encode()) == "invalid"


chains = fixture("chains")["chains"]
for chain in chains:
    plan = chain["objects"]["plan"]
    check(plan)
    if plan["action"]["operation"]["kind"] == "executable":
        variant = deepcopy(plan)
        variant["action"]["operation"]["argv"] = [
            {"kind": "literal", "value": "é e\u0301 🙂 \u0001\b\t\n\f\r\"\\ /"},
            {"kind": "integer", "value": -9007199254740991},
            {"kind": "integer", "value": 9007199254740991},
            {"kind": "literal", "value": ""},
        ]
        check(variant)
assert invoke("digest", b'{}') == "invalid"
print("SHA-256/JCS checks", count, "seed=23009; structure and digest only, no authority claim")
