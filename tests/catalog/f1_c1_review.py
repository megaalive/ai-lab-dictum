"""Review mechanics only: never manufacture the actual operator report."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from f1_c1_review import review,PLAN_SHA,PRESENT,ABSENT,UNKNOWN,Reject
from f1_inventory_review import load_plan,validate

plan=load_plan()
report={"schema_version":1,"role":"SYNTHETIC-SHAPE-FIXTURE","source_commit":"a"*40,
        "plan_sha256":PLAN_SHA,"scope_decision_ref":"SYNTHETIC-ONLY",
        "preflight_evidence_sha256":"b"*64,"guest_profile":"debian-13-x86_64-disposable",
        "utilities":[],"semantic_status":"NOT RUN","binding_status":"BLOCKED",
        "execution_allowed":False,"network_allowed":False}
for u in plan["utilities"]:
    is_present=u["id"] in PRESENT
    report["utilities"].append({"id":u["id"],"status":"PRESENT-METADATA" if is_present else
         "ABSENT" if u["id"] in ABSENT else "UNKNOWN","package":u["package_candidate"] if is_present else None,
         "version":"1:2.3-4" if is_present else None,"path":u["path_candidates"][0] if is_present else None,
         "sha256":"c"*64 if is_present else None})
def enc(x):
    return json.dumps(x,sort_keys=True).encode()
v=validate(report,plan)
out=review(enc(report),enc(v),mechanical=True)
assert out["role"]=="MECHANICAL-ONLY" and out["counts"]=={"PRESENT-METADATA":14,"ABSENT":2,"UNKNOWN":1}
assert len(out["intent_obligations"])==48 and len(out["utility_comparison"])==17
gaps={x["intent"] for x in out["intent_obligations"] if x["metadata_disposition"]=="MAPPED-CANDIDATE-GAP"}
assert gaps=={"network.interface.list","network.route.table","network.dns.lookup","archive.contents.list","archive.extract.safe"}
assert all(x["binding_status"]=="BLOCKED" for x in out["intent_obligations"])
assert not out["isolation_attested_by_tool"] and out["rights"]=="HOLD"
def bad(fn):
    try:
        fn()
    except (Reject,ValueError,KeyError,TypeError):
        return
    raise AssertionError("bad review accepted")
bad(lambda:review(enc(report),enc(v)))
bad(lambda:review(enc({**report,"role":"OPERATOR-METADATA-REPORT"}),enc(v),mechanical=True))
bad(lambda:review(enc({**report,"role":"OPERATOR-METADATA-REPORT"}),enc(v)))
bad(lambda:review(enc(report),enc({**v,"execution_allowed":0}),mechanical=True))
bad(lambda:review(enc(report),enc({**v,"counts":{"PRESENT-METADATA":17}}),mechanical=True))
bad(lambda:review(enc({**report,"plan_sha256":"0"*64}),enc(v),mechanical=True))
bad(lambda:review(enc({**report,"binding_status":"VERIFIED"}),enc(v),mechanical=True))
bad(lambda:review(enc(report),b'{"result":"a","result":"b"}',mechanical=True))
print("F1_C1_CONTENT_REVIEW", "17 utility rows; 48 obligations; 5 gaps; 8 negative vectors; actual report NOT SUPPLIED")
