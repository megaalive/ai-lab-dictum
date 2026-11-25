"""Exercise the complete comparator with non-gold abstract toy inputs.

No actual private seed, rights, test/holdout labels or regression training.
The arbitrary toy class assignments are not language/semantic gold.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from f1_compare import _compare_core, MARGINS
from f1_corpus import sha, encoded

probe,cli,b2_probe=map(Path,sys.argv[1:4])
def row(i,word,intent=None):
    supported=intent is not None
    e={"decision":"allow-proposal" if supported else "unsupported",
       "reason":"proposal-eligible" if supported else "unsupported-intent",
       "state":"resolved" if supported else "unsupported","intent":intent}
    if supported:
        e["slots"]={}
    return {"id":"toy-"+str(i),"text":"toy "+word,"language":"en","role":"MECHANICAL-TEST",
            "tags":["supported" if supported else "ood"],"expected":e}
# Labels are deliberately artificial mappings; actual grammar should abstain.
rows=[row(1,"zircon amethyst","memory.summary"),row(2,"copper amber","system.os.info"),
      row(3,"zircon topaz","memory.summary"),row(4,"copper obsidian","system.os.info"),
      row(5,"opal nebula"),row(6,"zircon aquamarine","memory.summary"),
      row(7,"copper carnelian","system.os.info"),row(8,"garnet moon")]
assign={r["id"]:{"split":"train" if j<4 else "dev" if j<6 else "test"}
        for j,r in enumerate(rows)}
candidate={"rows":assign,"manifest_sha256":"a"*64,"rights_sha256":"b"*64,
           "missing_supported_intents":{"train":[],"dev":[],"test":[]}}
raw_gold={r["id"]:{"intent":r["expected"]["intent"],"slots":{}} for r in rows if "supported" in r["tags"]}
binaries={k:"c"*64 for k in ("probe","cli","b2_probe")}
lock={"owner_decision_ref":"MECHANICAL-ONLY"}
out=_compare_core(rows,raw_gold,candidate,lock,"d"*40,binaries,probe,cli,b2_probe,mechanical=True)
assert out["status"]=="COMPLETE-MECHANICAL-SMOKE" and out["role"]=="MECHANICAL-COMPARATOR-SMOKE"
assert out["training_supported_rows"]==4 and len(out["weight_sha256"])==64
assert out["model_int16_bytes"]==48*(1024+1)*2
assert out["selected_margin"]==max(MARGINS)
assert len(out["dev_margin_evaluation"])==len(MARGINS)
for v in out["dev_margin_evaluation"].values():
    assert {r["id"] for r in v["results"]}=={"toy-5","toy-6"}
    assert v["metrics"]["statuses"]=={"complete":2}
    assert v["metrics"]["suite_counts"]["supported"]["correct"]==0
for m in ("B0","B1","B2"):
    v=out["test"][m]
    assert {r["id"] for r in v["results"]}=={"toy-7","toy-8"}
    assert v["metrics"]["statuses"]=={"complete":2}
    assert v["metrics"]["suite_counts"]["supported"]["accepted"]==0
    assert v["metrics"]["suite_counts"]["ood"]["correct"]==1
    assert v["metrics"]["resolved_JIA"]==0 and v["metrics"]["FES"]=="NOT RUN"
assert out["blind"]=="NOT RUN" and out["rights_review"]=="MECHANICAL-NOT-AUTHORIZED"
print("F1_COMPARATOR_NATIVE_SMOKE 4 toy train rows; 2 dev x 6 margins; 2 test x 3 models;"
      " identical full denominators; no proposals; actual Dictum fit/quality NOT RUN")
