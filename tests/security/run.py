"""A5 synthetic checklist lint, NOT real attestation or execution approval."""
import copy
import json
import re
from pathlib import Path

REQUIRED = {
    "owner-scope", "disposable-vm", "clean-snapshot", "no-host-share",
    "no-clipboard", "no-credentials", "no-host-passthrough", "no-production-bridge",
    "egress-disabled", "no-daemon-proxy", "explicit-fixture-root",
    "synthetic-fixture", "exact-allowlist", "identity-visibility", "descriptor-binding",
    "confinement-verified", "atomic-cgroup", "resource-limits", "trace-capability",
    "before-after-oracle", "reset-per-case", "separate-controller",
}
KEYS = {"schema_version", "mode", "phase", "profile", "target", "vcpu",
        "memory_mib", "timeout_ms", "max_output_bytes", "checks"}


def lint(record):
    if set(record) != KEYS or type(record["schema_version"]) is not int or record["schema_version"] != 1:
        return "shape"
    if record["mode"] != "synthetic-contract-only":
        return "mode"
    if record["phase"] != "F0-B":
        return "phase"
    if record["profile"] != "debian-13-x86-64" or record["target"] != "disposable-fixture-vm":
        return "target"
    if any(type(record[k]) is not int for k in ("vcpu", "memory_mib", "timeout_ms", "max_output_bytes")):
        return "limits"
    if not (record["vcpu"] == 2 and record["memory_mib"] == 2048 and
            1 <= record["timeout_ms"] <= 5000 and 1 <= record["max_output_bytes"] <= 65536):
        return "limits"
    checks = record["checks"]
    if type(checks) is not list or any(type(c) is not dict or set(c) !=
                                      {"id", "state", "evidence_sha256"} for c in checks):
        return "check-shape"
    if len(checks) != len(REQUIRED) or {c["id"] for c in checks} != REQUIRED:
        return "check-ids"
    for c in checks:
        if c["state"] != "VERIFIED":
            return "check-state"
        if not isinstance(c["evidence_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", c["evidence_sha256"]):
            return "evidence"
    return "SYNTHETIC-COMPLETE"


def main():
    path = Path(__file__).with_name("lab-preflight-v1.json")
    vectors = json.loads(path.read_text(encoding="utf-8"))
    tests = [("positive", vectors["record"], vectors["expected"])]
    for m in vectors["mutations"]:
        rec = copy.deepcopy(vectors["record"])
        obj = rec
        for key in m["path"][:-1]:
            obj = obj[key]
        obj[m["path"][-1]] = m["value"]
        tests.append((m["id"], rec, m["expected"]))
    if len({x[0] for x in tests}) != len(tests):
        raise ValueError("duplicate test ID")
    bad = 0
    for name, rec, expected in tests:
        actual = lint(rec)
        ok = actual == expected
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: {actual} expected {expected}")
    print(f"A5 contract lint: {len(tests)-bad}/{len(tests)}; actual VM S3 BLOCKED/NOT RUN")
    return bool(bad)


if __name__ == "__main__":
    raise SystemExit(main())
