"""Replay all locked S2 dev labels, unchanged. Diagnostic, not blind or tuning."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("functional_oracle",HERE/"run.py")
oracle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
raw=(ROOT/"tests/spikes/s2/development-v1.json").read_bytes()
manifest=json.loads(raw)
cases=manifest["development"]
assert manifest["fixed_time_end_unix_s"]==oracle.reference
assert len(cases)==100 and len({r["id"] for r in cases})==100
assert Counter(r["expected"]["status"] for r in cases)=={"candidate":80,"clarify":10,"unsupported":10}
regressions={"dev-6-7","dev-7-7"}
print("S2_REPLAY_CORPUS",hashlib.sha256(raw).hexdigest(),"100 fixed old development cases")

for model in ("B0","B1"):
    counts=Counter()
    confusion=Counter()
    failures=[]
    fixed=set()
    for row in cases:
        text=row["text"].encode()
        p=subprocess.run([sys.argv[1],model],input=text,capture_output=True,timeout=5)
        assert p.returncode==0 and not p.stderr, row["id"]
        result=json.loads(p.stdout)
        oracle.check_invariants(result,text,p.stdout.decode("utf-8").rstrip("\n"))
        expected=row["expected"]
        status=expected["status"]
        view=result["view"]
        decision=view["decision"]
        accepted=decision=="allow-proposal"
        counts[status,"n"]+=1
        counts[status,"accepted"]+=accepted
        if status=="candidate":
            ir=result["ir"]
            correct=accepted and ir.get("intent")==expected["intent"] and {
                v["name"]:v["value"] for v in ir["slots"]}==expected["slots"]
            actual=ir.get("intent",decision) if ir else decision
            confusion[expected["intent"],actual]+=1
            counts[row["language"],"n"]+=1
            counts[row["language"],"correct"]+=correct
        else:
            correct=decision==status
            # Do not count conservative deny as an exact S2 unsupported label.
            counts[status,"nonproposal"]+=not accepted
            assert not accepted, "negative suite emitted a proposal: "+row["id"]
        counts[status,"correct"]+=correct
        if not correct:
            failures.append({"id":row["id"],"expected":status,"actual":decision})
        if row["id"] in regressions and correct:
            fixed.add(row["id"])
    n=counts["candidate","n"]
    a=counts["candidate","accepted"]
    c=counts["candidate","correct"]
    print("S2_PIPELINE_REPLAY",model,json.dumps({
        "counts":{s:{k:counts[s,k] for k in ("n","accepted","correct","nonproposal")}
                  for s in ("candidate","clarify","unsupported")},
        "resolved_JIA":c/n,"supported_JS":c/n,"coverage":a/n,"selective_accuracy":c/a if a else None,
        "language":{s:[counts[s,"correct"],counts[s,"n"]] for s in ("id","en")},
        "confusion":{a+" -> "+b:n for (a,b),n in confusion.items()},
        "known_collision_correct":sorted(fixed),"failures":failures,
        "limitations":"old S2 labels have no explicit raw span gold; B1 guarded word retrieval differs from S2 TF-IDF; strict policy may deny where old prototype clarified or marked unsupported"
    },sort_keys=True))
    if model=="B0":
        assert fixed==regressions,"known path/log collision regression"
