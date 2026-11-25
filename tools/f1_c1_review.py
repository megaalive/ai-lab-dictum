"""Review the already collected F1-C1 report, without accessing the guest.

No inference from package presence to semantic compatibility, rights or
capability. The operator's original report digest is pinned.
"""
import argparse
import hashlib
import json
from pathlib import Path
from f1_inventory_review import ROOT,PLAN,Reject,need,load_plan,validate

SCOPE="F1-C1-OFFLINE-20261124-01"
SOURCE="6adf5ec5acd792b38e71a8a136f2cd2eaf1a2051"
PREFLIGHT="fc92d2bd96b378fce8b99824a770fe445131ae3fb543edf4a62f38b48732fd6b"
REPORT_SHA="66ed58a56e51e16b523d9c0cca8a1f3d932e38bb1b989bc026f69d1fc6c80bb6"
PLAN_SHA="1e560fb47a568c125654ec2a5e7e8cb1e3af08f7bf7491d5d1b4a41925ae662e"
PRESENT={"ss","ping","systemctl","journalctl","dmesg","df","lsblk","findmnt",
         "tar","free","lscpu","dpkg-query","apt-cache","who"}
ABSENT={"dig","unzip"}
UNKNOWN={"ip"}
LEDGER=ROOT/"data/manifests/license-ledger-s5-debian-v1.json"
LEDGER_BLOB="8a343ae9f1041e0043b9da119f549179f1a984e8"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read_json(raw):
    need(0<len(raw)<=65536,"size")
    def closed(pairs):
        o={}
        for k,v in pairs:
            need(k not in o,"duplicate")
            o[k]=v
        return o
    def reject(_):
        raise Reject("number")
    return json.loads(raw.decode("utf-8","strict"),object_pairs_hook=closed,
                      parse_float=reject,parse_constant=reject)

def review(raw,validator_raw,*,mechanical=False):
    plan=load_plan()
    need(sha(PLAN.read_bytes())==PLAN_SHA,"plan-pin")
    report=read_json(raw)
    result=validate(report,plan)
    need(report["role"]==("SYNTHETIC-SHAPE-FIXTURE" if mechanical else "OPERATOR-METADATA-REPORT"),
         "role")
    if not mechanical:
        need(sha(raw)==REPORT_SHA,"report-pin")
        need(report["scope_decision_ref"]==SCOPE and report["source_commit"]==SOURCE and
             report["preflight_evidence_sha256"]==PREFLIGHT,"provenance")
    # Match actual validator JSON, not just a copied success string.
    need(json.dumps(read_json(validator_raw),sort_keys=True)==json.dumps(result,sort_keys=True),
         "validator-mismatch")
    rows={r["id"]:r for r in report["utilities"]}
    statuses={s:{i for i,row in rows.items() if row["status"]==s} for s in result["counts"]}
    if not mechanical:
        need(statuses=={"PRESENT-METADATA":PRESENT,"ABSENT":ABSENT,"UNKNOWN":UNKNOWN},"reported-status-drift")
    ledger_raw=LEDGER.read_bytes()
    need(hashlib.sha1(f"blob {len(ledger_raw)}\0".encode()+ledger_raw).hexdigest()==LEDGER_BLOB,"ledger-pin")
    ledger=json.loads(ledger_raw)
    for row in ledger["sources"]:
        need(row["decision"]=="HOLD-PER-FILE-RIGHTS" and row["training_allowed"] is False and
             row["distribution_allowed"] is False and row["imported"] is False,"rights-drift")
    comparison=[]
    for row in report["utilities"]:
        candidates=[x for x in ledger["sources"] if x["package"]==row["package"]]
        versions=sorted({v.removeprefix("Version: ") for x in candidates for v in x["metadata"]
                         if v.startswith("Version: ")})
        version_status=("NOT-APPLICABLE" if row["status"]!="PRESENT-METADATA" else
                        "NO-S5-PACKAGE-SAMPLE" if not versions else
                        "EXACT-PACKAGE-VERSION-MATCH-ONLY" if row["version"] in versions else "VERSION-DIFFERENT")
        comparison.append({**row,"s5_package_versions":versions,"s5_version_status":version_status,
                           "rights":"HOLD/NOT VERIFIED","semantic_status":"NOT RUN","binding_status":"BLOCKED"})
    intents=[]
    for item in plan["intents"]:
        states={u:rows[u]["status"] for u in item["utility_candidates"]}
        disposition=("NO-UTILITY-MAPPING" if not states else
                     "ALL-PRESENT-METADATA" if all(s=="PRESENT-METADATA" for s in states.values()) else
                     "MAPPED-CANDIDATE-GAP")
        intents.append({"intent":item["intent"],"operation_surface":item["operation_surface"],
                        "candidate_statuses":states,"metadata_disposition":disposition,
                        "compatibility_obligation":item["compatibility_obligation"],
                        "semantic_status":"NOT RUN","host_equivalence":"NOT RUN","binding_status":"BLOCKED"})
    return {"schema_version":1,"role":"MECHANICAL-ONLY" if mechanical else "OPERATOR-REPORT-CONTENT-REVIEW",
            "report_sha256":sha(raw),"validator_sha256":sha(validator_raw),"source_commit":report["source_commit"],
            "plan_sha256":PLAN_SHA,"scope_decision_ref":report["scope_decision_ref"],
            "preflight_evidence_sha256":report["preflight_evidence_sha256"],"counts":result["counts"],
            "validator":"SHAPE-VALID-ONLY","utility_comparison":comparison,"intent_obligations":intents,
            "rights":"HOLD","semantic_status":"NOT RUN","binding_status":"BLOCKED","execution_allowed":False,
            "network_allowed":False,"isolation_attested_by_tool":False,"S3":"NOT RUN","FES":"NOT RUN"}

def main():
    parser=argparse.ArgumentParser(description="Review the existing exact F1-C1 report; no guest execution")
    for arg in ("report","validator","output"):
        parser.add_argument("--"+arg,required=True,type=Path)
    args=parser.parse_args()
    try:
        paths=[p.resolve() for p in (args.report,args.validator,args.output)]
        need(len(set(paths))==3 and all(not p.is_relative_to(ROOT.resolve()) for p in paths),"private-path")
        def bounded(p):
            with p.open("rb") as f:
                return f.read(65537)
        out=review(bounded(paths[0]),bounded(paths[1]))
        data=json.dumps(out,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()+b"\n"
        with paths[2].open("xb") as f:
            f.write(data)
        print(json.dumps({"status":"REPORT-CONTENT-REVIEW-ONLY","review_sha256":sha(data),
                          "counts":out["counts"],"binding_status":"BLOCKED","semantic_status":"NOT RUN"},
                         sort_keys=True))
    except (Reject,ValueError,TypeError,KeyError,OSError,RecursionError):
        raise SystemExit("F1-C1 report review rejected (sanitized); preserve originals") from None

if __name__=="__main__":
    main()
