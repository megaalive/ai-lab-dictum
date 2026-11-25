"""Actual native metadata lookup vs independent pinned source oracle."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog/core/intents-v1.json"
PROFILE = ROOT / "catalog/debian-13/v1.json"
OVERLAY = ROOT / "spec/catalog/f1-runtime-catalog-v2.json"
OVERLAY_DATA=json.loads(OVERLAY.read_bytes())
ADDITIONAL=OVERLAY_DATA["deferred_slots"]+OVERLAY_DATA["additional_slots"]
NARRATIVES=set(OVERLAY_DATA["narrative_only"])


def rows():
    catalog = json.loads(CATALOG.read_bytes())["intents"]
    profile = json.loads(PROFILE.read_bytes())
    bindings = {x["intent"]: x for x in profile["bindings"]}
    assert len(catalog) == len({x["id"] for x in catalog}) == len(bindings) == 48
    assert {x["id"] for x in catalog} == set(bindings)
    assert len(ADDITIONAL)==11 and len(NARRATIVES)==5
    assert sum(x["skeleton"] for x in catalog) == 8
    assert profile["trust_status"] == "NOT VERIFIED"
    for x in catalog:
        b = bindings[x["id"]]
        assert not x["execute_eligible"] and not x["source"]["external_content_imported"]
        assert (b["capability_status"], b["compatibility"], b["version_status"]) == (
            "BLOCKED", "NOT VERIFIED", "NOT VERIFIED")
        yield x, b


def check(value, row, binding):
    expected = {"intent": row["id"], "id": row["description"]["id"],
                "en": row["description"]["en"], "ordinal": row["ordinal"],
                "effect": row["effect"]["class"], "catalogued": True,
                "catalog_proposal_eligible": row["proposal_eligible"],
                "pipeline_status": "SYNTHETIC_PROPOSAL",
                "typed_slot_count": len(row["slots"]), "deferred_slot_count": len(row["deferred_slots"]),
                "runtime_typed_slot_count":len(row["slots"])+sum(x["intent"]==row["id"] for x in ADDITIONAL),
                "runtime_representation":"narrative-guidance" if row["id"] in NARRATIVES else "structured-proposal",
                "capability_status": binding["capability_status"],
                "compatibility": binding["compatibility"], "version_status": binding["version_status"],
                "source": "pinned original catalog metadata; not observed OS data",
                "copyable": False, "execution_allowed": False, "observed_os_data": False}
    assert value == expected, row["id"]


def check_inspect(v):
    assert v["intent_count"] == v["implemented_synthetic_intent_count"] == 48
    assert v["f0_skeleton_intent_count"] == 8
    assert v["catalogued_intent_count"] == 48 and v["verified_binding_count"] == 0
    assert v["catalog_sha256"] == hashlib.sha256(OVERLAY.read_bytes()).hexdigest()
    assert v["catalog_registry_sha256"] == hashlib.sha256(CATALOG.read_bytes()).hexdigest()
    assert v["ir_schema_version"] == 2
    assert v["profile_sha256"] == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    assert v["execution_allowed"] is False and v["neural_parameters"] == 0


def main():
    cli = sys.argv[1]
    count = 0
    for row, binding in rows():
        p = subprocess.run([cli, "search", row["id"]], capture_output=True, timeout=5)
        assert p.returncode == 0 and not p.stderr, row["id"]
        check(json.loads(p.stdout), row, binding)
        count += 1
    p = subprocess.run([cli, "inspect"], capture_output=True, timeout=5)
    assert p.returncode == 0 and not p.stderr
    check_inspect(json.loads(p.stdout))
    count += 1
    negatives = ["", "memory", "MEMORY.SUMMARY", " memory.summary", "memory.summary ",
                 "memory.summary.CANARY_SECRET", "CANARY_SECRET", "--help",
                 "/fixture/data/.env", "memory.summary\nCANARY_SECRET", "a"*4097,
                 b"\xff", "memóry.summary"]
    for i, text in enumerate(negatives):
        p = subprocess.run([cli, "search", text], capture_output=True, timeout=5)
        assert p.returncode == 3 and not p.stdout, i
        assert p.stderr == b"dictum: unsupported intent.\n", i
        count += 1
    # An exact registry ID is not an instruction nor a capability. In particular,
    # metadata lookup must not interpret canonical IDs as runtime grammar.
    for row, _ in rows():
        p = subprocess.run([cli, "ask", row["id"]], capture_output=True, timeout=5)
        assert p.returncode == 3 and not p.stderr, row["id"]
        v = json.loads(p.stdout)
        assert v["decision"] == "unsupported" and not v["execution_allowed"] and not v["observed_os_data"]
        count += 1
    print("F1_CATALOG_LOOKUP",count,"checks; 48 metadata rows; 48 synthetic; 5 narrative-only; 0 verified bindings")


if __name__ == "__main__":
    main()
