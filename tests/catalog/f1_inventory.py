"""Synthetic shape fixtures only; no actual guest attestation."""
import copy
import hashlib
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from f1_inventory_review import PLAN,Reject,load_plan,validate

p=load_plan()
report={"schema_version":1,"role":"SYNTHETIC-SHAPE-FIXTURE","source_commit":"a"*40,
        "plan_sha256":hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "scope_decision_ref":"SYNTHETIC-ONLY","preflight_evidence_sha256":"b"*64,
        "guest_profile":"debian-13-x86_64-disposable","utilities":[],
        "semantic_status":"NOT RUN","binding_status":"BLOCKED",
        "execution_allowed":False,"network_allowed":False}
for i,x in enumerate(p["utilities"]):
    present=i%3==0
    report["utilities"].append({"id":x["id"],"status":"PRESENT-METADATA" if present else "ABSENT" if i%3==1 else "UNKNOWN",
        "package":x["package_candidate"] if present else None,"version":"1:2.3-4" if present else None,
        "path":x["path_candidates"][0] if present else None,"sha256":"c"*64 if present else None})
out=validate(report,p)
assert out["counts"]=={"PRESENT-METADATA":6,"ABSENT":6,"UNKNOWN":5}
assert out["result"]=="SHAPE-VALID-ONLY" and not out["isolation_attested"] and not out["execution_allowed"]
def root(**kw):
    x=copy.deepcopy(report);x.update(kw);return x
def util(i,**kw):
    x=copy.deepcopy(report);x["utilities"][i].update(kw);return x
negative=[
 root(role="VERIFIED"),root(binding_status="VERIFIED"),root(semantic_status="PASS"),
 root(execution_allowed=True),root(network_allowed=True),root(schema_version=True),
 root(source_commit="main"),root(plan_sha256="x"*64),root(preflight_evidence_sha256=""),
 root(scope_decision_ref="production/host"),root(guest_profile="proxmox-host"),
 root(utilities=report["utilities"][:-1]),root(utilities=report["utilities"][:-1]+[report["utilities"][0]]),
 util(0,id="unknown"),util(0,path="/tmp/ss"),util(0,package="unknown"),
 util(0,version="secret\n"),util(0,sha256=None),util(1,sha256="c"*64),
 util(0,status="VERIFIED"),util(0,authority=True),
]
for i,x in enumerate(negative):
    try:
        validate(x,p)
    except Reject:
        pass
    else:
        raise AssertionError("accepted negative "+str(i))
print("F1_INVENTORY_SHAPE",1+len(negative),"vectors; 17 candidate utilities, 48 obligations;",
      "actual guest/semantics/host-equivalence NOT RUN; all bindings BLOCKED")
