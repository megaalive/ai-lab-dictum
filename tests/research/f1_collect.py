"""Blank collection plan and mechanical worksheet lifecycle, no human gold."""
import copy
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from f1_collect import (collection_plan,author_packet,review_sheet,assemble,reference)
from f1_seed import load_contract,rights_check,parse
from f1_corpus import sha,encoded,Reject

contract=load_contract()
plan=collection_plan(contract)
assert plan==collection_plan(contract)
tasks=plan["assignments"]
assert len(tasks)==300 and Counter(t["target_language"] for t in tasks)=={"id":210,"en":90}
assert Counter(t["target_suite"] for t in tasks)=={"supported":240,"ambiguity":20,"ood":20,"security":20}
assert set(Counter(t["intent"] for t in tasks if t["intent"]).values())=={5}
assert len({t["intent"] for t in tasks if t["intent"]})==48
ref=reference(contract)
assert len(ref["intents"])==48 and "patterns" not in ref and ref["execution_allowed"] is False
author=author_packet(plan)
assert all(not r["text"] and r["author"] is None for r in author["records"])
for i,text in enumerate(("toy amber","toy violet","toy crimson")):
    row=author["records"][i]
    row.update(text=text,language="en",semantic_group="toy-g"+str(i),family="toy-f"+str(i),
               source_id="toy-source",source_version="v1",author="toy-author")
sheet=review_sheet(author,plan)
assert len(sheet["records"])==3 and len(sheet["skipped_assignment_ids"])==297
assert all(r["decision"]=="PENDING" and r["expected"] is None for r in sheet["records"])
for row in sheet["records"]:
    row.update(reviewer="toy-reviewer",decision="ACCEPTED",decision_ref="toy-review",
               evidence_sha256="a"*64,sensitive_data=False,adjudicated=True,reason_code="toy-accept",
               fixture_id="CAT-35",expected={"decision":"allow-proposal","reason":"proposal-eligible",
                    "state":"resolved","intent":"memory.summary","slots":{}},slot_sources={},tags=["supported"])
sheet["records"][-1].update(decision="REJECTED",reason_code="toy-reject",fixture_id=None,expected=None,
                            slot_sources=None,tags=None)
def assemble_toy(a=author,s=sheet):
    return assemble(a,s,plan,contract,mechanical=True,regression=set())
seed,request,audit=assemble_toy()
assert parse(seed)["role"]=="MECHANICAL-TEST" and len(parse(seed)["records"])==2
assert request["role"]=="RIGHTS-REVIEW-REQUEST-NOT-APPROVAL" and request["seed_sha256"]==sha(seed)
assert not request["allow_development_fit"] and request["owner_decision_ref"] is None
assert audit["accepted_count"]==2 and audit["rejected_count"]==1 and len(audit["skipped_assignment_ids"])==297
assert audit["rights"]=="HOLD" and not audit["review_identity_attested_by_tool"]
assert assemble_toy()==(seed,request,audit)
def changed(field,value):
    d=copy.deepcopy(sheet)
    d["records"][0][field]=value
    return d
def bad(fn):
    try:
        fn()
    except (Reject,ValueError,TypeError,KeyError):
        return
    raise AssertionError("invalid worksheet accepted")
negative=[
 lambda:assemble_toy(s=changed("text","tampered")),
 lambda:assemble_toy(s=changed("author_row_sha256","0"*64)),
 lambda:assemble_toy(s=changed("reviewer","toy-author")),
 lambda:assemble_toy(s=changed("decision","PENDING")),
 lambda:assemble_toy(s=changed("sensitive_data",True)),
 lambda:assemble_toy(s=changed("adjudicated",False)),
 lambda:assemble_toy(s=changed("evidence_sha256","")),
 lambda:assemble_toy(s=changed("fixture_id","CAT-01")),
 lambda:assemble_toy(s=changed("tags",["ood"])),
 lambda:assemble_toy(s=changed("decision","REJECTED")),
 lambda:assemble_toy(s={**sheet,"records":sheet["records"][:-1]}),
 lambda:assemble_toy(s={**sheet,"records":sheet["records"]+[sheet["records"][0]]}),
 lambda:assemble_toy(s={**sheet,"skipped_assignment_ids":[]}),
 lambda:assemble_toy(s={**sheet,"author_packet_sha256":"b"*64}),
 lambda:rights_check(request,sha(seed),False),
 lambda:assemble(author,sheet,plan,contract,regression=set()),
]
for fn in negative:
    bad(fn)
print("F1_HUMAN_COLLECTION", "300 blank assignments; 3 mechanical reviews, 2 accepted/1 rejected; "
      +str(len(negative))+" negative vectors; human gold 0; rights HOLD")
