"""Lock/denominator tests use only mechanical records; no actual B2 fit."""
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from f1_compare import validate_lock,score_rows,BUDGET
from f1_corpus import Reject,sha,encoded

candidate={"role":"MECHANICAL-TEST","seed_sha256":"a"*64,"rights_sha256":"b"*64,
           "fuzzy_pairs":[["toy-a","toy-b"]]}
candidate["manifest_sha256"]=sha(encoded(candidate))
binary={"probe":"c"*64,"cli":"d"*64,"b2_probe":"e"*64}
source="f"*40
lock={"schema_version":1,"role":"MECHANICAL-TEST","scope":"F1-B2-DEVELOPMENT-ONLY",
      "candidate_manifest_sha256":candidate["manifest_sha256"],"seed_sha256":"a"*64,
      "rights_sha256":"b"*64,"owner_decision_ref":"toy-owner","reviewer":"toy-reviewer",
      "review_evidence_sha256":"a"*64,"source_commit":source,"binaries_sha256":binary,
      "fuzzy_review":[{"pair":["toy-a","toy-b"],"decision":"KEEP-TOGETHER","review_ref":"toy-ref"}],
      "budget":BUDGET,"allow_fit":False,"allow_distribution":False,"blind":False}
assert validate_lock(lock,candidate,source,binary,mechanical=True)
def bad(fn):
    try:
        fn()
    except (Reject,ValueError,TypeError,KeyError):
        return
    raise AssertionError("bad comparator input accepted")
negative=[]
for k,v in [
    ("role","OWNER-REVIEWED-F1-DEVELOPMENT-LOCK"),("allow_fit",True),("blind",True),
    ("allow_distribution",True),("schema_version",True),("source_commit","0"*40),
    ("seed_sha256","0"*64),("rights_sha256","0"*64),("candidate_manifest_sha256","0"*64),
    ("review_evidence_sha256",""),("reviewer",""),("binaries_sha256",{}),
    ("budget",{**BUDGET,"epochs":13}),("fuzzy_review",[]),
    ("fuzzy_review",[{"pair":["toy-a","toy-b"],"decision":"SPLIT","review_ref":"toy-ref"}]),
    ("fuzzy_review",[{"pair":["toy-b","toy-a"],"decision":"KEEP-TOGETHER","review_ref":"toy-ref"}]),
]:
    bad(lambda k=k,v=v:validate_lock({**lock,k:v},candidate,source,binary,mechanical=True))
    negative.append(k)
bad(lambda:validate_lock(lock,{**candidate,"fuzzy_pairs":[]},source,binary,mechanical=True))
bad(lambda:validate_lock(lock,candidate,source,binary))
bad(lambda:validate_lock(lock,candidate,source,{**binary,"probe":"0"*64},mechanical=True))
rows=[{"id":"a","tags":["supported"],"expected":{"intent":"memory.summary"},"language":"id"},
      {"id":"b","tags":["supported"],"expected":{"intent":"memory.summary"},"language":"en"},
      {"id":"c","tags":["ambiguity"],"expected":{"intent":None},"language":"mixed"},
      {"id":"d","tags":["ood"],"expected":{"intent":None},"language":"id"},
      {"id":"e","tags":["security"],"expected":{"intent":None},"language":"en"}]
def result(i,**kw):
    return {"id":i,"status":"complete","outcome":"unsupported","actual_intent":None,
            "accepted":False,"correct":False,"raw_joint":False,"raw_intent":False,"cold_ms":1.0,**kw}
# Construct result overrides without duplicate dict keyword arguments.
actual=[result("a",outcome="allow-proposal",actual_intent="memory.summary",accepted=True,
               correct=True,raw_joint=True,raw_intent=True),
        result("b",status="timeout",outcome="no-result"),
        result("c",outcome="clarify",correct=True),result("d",correct=True),result("e",outcome="deny",correct=True)]
m=score_rows(rows,actual)
assert m["resolved_JIA"]==.5 and m["raw_JIA"]==.5 and m["supported_coverage"]==.5
assert m["supported_selective_accuracy"]==1.0 and m["all_case_exact_outcome_accuracy"]==.8
assert m["ambiguity_exact_recall"]==m["ood_exact_recall"]==1.0 and m["FES"]=="NOT RUN"
assert m["statuses"]=={"complete":4,"timeout":1} and m["timing_n"]==5
assert score_rows(rows,list(reversed(actual)))==m
for bad_rows in [actual[:-1],actual+actual[:1],[{**a,"id":"missing"} if a["id"]=="b" else a for a in actual],
                 [{**a,"correct":True} if a["id"]=="b" else a for a in actual],
                 [{**a,"accepted":True} if a["id"]=="c" else a for a in actual],
                 [{**a,"raw_joint":True} if a["id"]=="e" else a for a in actual]]:
    bad(lambda bad_rows=bad_rows:score_rows(rows,bad_rows))
print("F1_PRIVATE_COMPARE_LOCK",len(negative)+3,"lock negatives; 6 denominator negatives;",
      "5 mechanical cases incl timeout; actual seed/lock/fit/test/blind NOT RUN")
