"""Shape/provenance check for sanitized disposable-guest metadata reports.

No probing, subprocess, network, or host access beyond supplied repository
plan/report bytes. A successful check is never an attestation or capability.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"spec/catalog/f1-debian-inventory-plan-v1.json"
PROFILE=ROOT/"catalog/debian-13/v1.json"

class Reject(ValueError):
    pass

def need(ok,code):
    if not ok:
        raise Reject(code)

def load_plan():
    raw=PROFILE.read_bytes()
    p=json.loads(PLAN.read_bytes())
    need(hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()==
         p["source_git_blob"]=="2cc5431daaf3da0dcaaa7fdcacefdb7b04a8cae9","profile-pin")
    binding=json.loads(raw)["bindings"]
    need(len(p["intents"])==len(binding)==48 and
         [x["intent"] for x in p["intents"]]==[x["intent"] for x in binding],"intent-coverage")
    need(p["status"]=="NOT RUN" and p["metadata_only"] is True and
         p["execution_allowed"] is False and p["network_allowed"] is False and
         p["actual_binding_status"]=="BLOCKED","authority")
    ids={x["id"] for x in p["utilities"]}
    need(len(ids)==len(p["utilities"])==17,"utility-coverage")
    for row,b in zip(p["intents"],binding):
        need(row["operation_surface"]==b["operation_surface"] and
             row["compatibility_obligation"]==b["host_equivalence"]["method"] and
             set(row["utility_candidates"])<=ids and row["semantic_status"]=="NOT RUN" and
             row["binding_status"]==b["capability_status"]=="BLOCKED","intent-binding")
        need((row["operation_surface"]=="command-candidate")==bool(row["utility_candidates"]),
             "surface")
    return p

def hexstr(v,n):
    return type(v) is str and re.fullmatch("[0-9a-f]{"+str(n)+"}",v) is not None

def validate(report,plan):
    keys={"schema_version","role","source_commit","plan_sha256","scope_decision_ref",
          "preflight_evidence_sha256","guest_profile","utilities","semantic_status",
          "binding_status","execution_allowed","network_allowed"}
    need(type(report) is dict and set(report)==keys and
         type(report["schema_version"]) is int and report["schema_version"]==1,"shape")
    need(report["role"] in {"SYNTHETIC-SHAPE-FIXTURE","OPERATOR-METADATA-REPORT"} and
         report["guest_profile"]=="debian-13-x86_64-disposable","role")
    need(hexstr(report["source_commit"],40) and
         report["plan_sha256"]==hashlib.sha256(PLAN.read_bytes()).hexdigest() and
         hexstr(report["preflight_evidence_sha256"],64) and
         type(report["scope_decision_ref"]) is str and
         re.fullmatch(r"[A-Z0-9-]{1,64}",report["scope_decision_ref"]),"evidence-shape")
    need(report["semantic_status"]=="NOT RUN" and report["binding_status"]=="BLOCKED" and
         report["execution_allowed"] is False and report["network_allowed"] is False,"authority")
    need(type(report["utilities"]) is list and len(report["utilities"])==17,"utility-coverage")
    expected={x["id"]:x for x in plan["utilities"]}
    seen=set()
    counts={"PRESENT-METADATA":0,"ABSENT":0,"UNKNOWN":0}
    for row in report["utilities"]:
        need(type(row) is dict and set(row)=={"id","status","package","version","path","sha256"},
             "utility-shape")
        i=row["id"]
        need(type(i) is str and i in expected and i not in seen and row["status"] in counts,"utility-id")
        seen.add(i)
        counts[row["status"]]+=1
        if row["status"]=="PRESENT-METADATA":
            # Candidate package and exact paths only. Mismatch remains UNKNOWN;
            # do not invent replacement utility identities.
            need(row["package"]==expected[i]["package_candidate"] and
                 row["path"] in expected[i]["path_candidates"] and
                 hexstr(row["sha256"],64) and type(row["version"]) is str and
                 re.fullmatch(r"[A-Za-z0-9.+:~\-]{1,128}",row["version"]),"metadata")
        else:
            need(all(row[k] is None for k in ("package","version","path","sha256")),"unknown-fields")
    need(seen==set(expected),"utility-coverage")
    return {"result":"SHAPE-VALID-ONLY","role":report["role"],"counts":counts,
            "semantic_status":"NOT RUN","binding_status":"BLOCKED",
            "isolation_attested":False,"execution_allowed":False}

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: f1_inventory_review.py <sanitized-report.json>")
    try:
        # Bound report bytes; no raw records or errors echoed.
        with open(sys.argv[1],"rb") as f:
            raw=f.read(65537)
        need(len(raw)<=65536,"size")
        def closed(pairs):
            out={}
            for k,v in pairs:
                need(k not in out,"duplicate")
                out[k]=v
            return out
        print(json.dumps(validate(json.loads(raw,object_pairs_hook=closed),load_plan()),sort_keys=True))
    except (Reject,ValueError,TypeError,KeyError,OSError):
        raise SystemExit("inventory report rejected (sanitized)") from None
