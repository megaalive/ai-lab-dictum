"""Mechanical-only seed preparation tests; no actual human gold or rights."""
import copy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from f1_seed import prepare, source_digest, load_contract
from f1_corpus import Reject, sha, encoded, normalize

def row(i,text,intent="memory.summary",slots=None,sources=None,lang="en"):
    return {"id":"toy-"+str(i),"role":"MECHANICAL-TEST","revision":1,"text":text,
            "text_sha256":sha(text.encode()),"normalized_sha256":sha(normalize(text).encode()),
            "language":lang,"dominant_language":None,"semantic_group":"g"+str(i),"family":"f"+str(i),
            "parent":None,"source_id":"toy-source","source_version":"v1","author":"toy-author",
            "review":{"reviewer":"toy-reviewer","decision_ref":"toy-review","evidence_sha256":"a"*64,
                      "decision":"ACCEPTED","sensitive_data":False,"adjudicated":True},
            "fixture_id":load_contract()["catalog"][intent]["fixture_id"],
            "expected":{"decision":"allow-proposal","reason":"proposal-eligible","state":"resolved",
                        "intent":intent,"slots":slots or {}},"slot_sources":sources or {},
            "tags":["supported"],"derivation":"MECHANICAL-TEST"}

def packet(rows):
    seed=encoded({"schema_version":1,"role":"MECHANICAL-TEST","records":rows})
    rights={"schema_version":1,"role":"MECHANICAL-TEST","seed_sha256":sha(seed),
            "owner_decision_ref":"toy-scope","sources":[{"id":"toy-source","version":"v1",
            "record_set_sha256":source_digest(rows),"origin":"MECHANICAL-TEST",
            "rights_decision_ref":"toy-rights","attribution":"toy-author"}],
            "allow_development_fit":False,"allow_development_evaluation":False,
            "allow_distribution":False,"blind":False}
    return seed,rights

def candidate(rows,edit_rights=None,regression=None):
    seed,rights=packet(rows)
    if edit_rights:
        edit_rights(rights)
    return prepare(seed,encoded(rights),mechanical=True,regression=set() if regression is None else regression)

rows=[row(1,"toy amethyst memory"),row(2,"toy pewter memory",lang="id"),
      row(3,"toy observe demo.service","service.status.get",{"unit":{"kind":"unit-name","value":"demo.service"}},
          {"unit":{"kind":"input-span","span":{"start":12,"end":24}}}),
      row(4,"toy cobalt uptime","system.uptime.summary"),
      row(5,"toy violet operating system","system.os.info"),
      row(6,"toy teal boot messages","log.boot.messages",{"limit":{"kind":"positive-int","value":30}},
          {"limit":{"kind":"catalog-default"}})]
a=candidate(rows)
b=candidate(rows)
assert a==b
assert a["rows"]["toy-1"]["component"]==a["rows"]["toy-2"]["component"]
assert a["training_allowed"] is False and a["readiness"]=="REVIEW-REQUIRED"
assert a["human_review_evidence_status"]=="SHAPE-ONLY-NOT-ATTESTED"
assert sum(c.get("all",0) for c in a["counts"].values())==len(rows)
assert a["manifest_sha256"]==sha(encoded({k:v for k,v in a.items() if k!="manifest_sha256"}))
def change(i,path,value):
    x=copy.deepcopy(rows)
    d=x[i]
    for k in path[:-1]:
        d=d[k]
    d[path[-1]]=value
    return x
def bad(fn):
    try:
        fn()
    except (Reject,ValueError,TypeError,KeyError):
        return
    raise AssertionError("bad candidate accepted")
neg=[
 lambda:candidate(rows+rows[:1]),lambda:candidate(change(0,["role"],"HUMAN-DEVELOPMENT-SEED")),
 lambda:candidate(change(0,["text_sha256"],"0"*64)),lambda:candidate(change(0,["normalized_sha256"],"0"*64)),
 lambda:candidate(change(0,["review","reviewer"],"toy-author")),
 lambda:candidate(change(0,["review","sensitive_data"],True)),
 lambda:candidate(change(0,["review","adjudicated"],False)),
 lambda:candidate(change(0,["source_version"],"v2")),lambda:candidate(change(0,["parent"],"toy-0")),
 lambda:candidate(change(0,["parent"],"toy-1")),lambda:candidate(change(0,["parent"],"toy-2")),
 lambda:candidate(change(0,["fixture_id"],"CAT-01")),lambda:candidate(change(0,["expected","intent"],"unknown")),
 lambda:candidate(change(0,["expected","state"],"unsupported")),lambda:candidate(change(0,["tags"],["supported","security"])),
 lambda:candidate(change(0,["tags"],["supported","NET"])),
 lambda:candidate(change(2,["expected","slots","unit","value"],"unknown.service")),
 lambda:candidate(change(2,["slot_sources","unit","span","start"],13)),
 lambda:candidate(change(2,["slot_sources","unit","kind"],"catalog-default")),
 lambda:candidate(change(2,["expected","slots"],{})),
 lambda:candidate(change(5,["expected","slots","limit","value"],31)),
 lambda:candidate(rows,lambda r:r.update(allow_development_fit=True)),
 lambda:candidate(rows,lambda r:r.update(blind=True)),
 lambda:candidate(rows,lambda r:r.update(allow_distribution=True)),
 lambda:candidate(rows,lambda r:r.update(seed_sha256="0"*64)),
 lambda:candidate(rows,lambda r:r["sources"][0].update(record_set_sha256="0"*64)),
 lambda:candidate(rows,regression={normalize(rows[0]["text"])}),
 lambda:prepare(packet(rows)[0],encoded(packet(rows)[1])),
 lambda:prepare(b'{"role":"MECHANICAL-TEST","role":"MECHANICAL-TEST"}',encoded(packet(rows)[1]),mechanical=True),
]
for fn in neg:
    bad(fn)
print("F1_SEED_PREPARATION",len(rows),"mechanical rows;",len(neg),
      "negative vectors; stable candidate hash",a["manifest_sha256"],
      "human gold/actual split/training NOT RUN")
