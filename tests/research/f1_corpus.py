"""Pure mechanical split vectors; never read or write user/production data."""
import copy
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("corpus_mechanics",ROOT/"tools/f1_corpus.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

inventory=m.inventory()
assert inventory["functional_counts"]=={"supported":198,"ambiguity":36,"ood":33,"security":105}
assert inventory["human_gold_count"]==0 and inventory["actual_split"]=="NOT RUN"
assert not inventory["training_allowed"] and inventory["rights"]=="HOLD"

def row(i,text,group=None,family=None,semantic=None,parent=None,language="en"):
    return {"id":"toy-"+i,"intent":"toy-intent-"+("a" if language=="en" else "b"),
            "language":language,"text":"toy "+text,"semantic_group":"toy-"+(group or i),
            "family":"toy-"+(family or i),"semantic_key":"toy-"+(semantic or i),
            "parent":None if parent is None else "toy-"+parent,
            "role":"MECHANICAL-TOY","rights_status":"HOLD","human_reviewed":False}

rows=[
    row("a","alpha beta gamma delta epsilon zeta eta theta","a","fam-a","sem-a"),
    row("b","alpha beta gamma delta epsilon zeta eta iota","a","fam-b","sem-b",parent="a"),
    row("c","unrelated words oak pine cedar maple","c","fam-b","sem-c"),
    row("d","ALPHA BETA GAMMA DELTA EPSILON ZETA ETA THETA","d","fam-d","sem-a"),
    row("e","sample one two three four five six seven eight nine ten eleven twelve","e"),
    row("f","sample one two three four five six seven eight nine ten eleven thirteen","f"),
]
for i,text in enumerate(["violet comet bronze","river quartz blue","orange paper anchor","tiny reed cloud",
                         "bamboo fossil stone","violet glass pebble","winter lantern moss","opal violet tree",
                         "copper mountain fern","walnut brick lake","silver valley snow","amber cliff rain",
                         "robin velvet sand","mint granite wind","pearl shell flame","ruby willow dusk",
                         "ivory bridge dawn","jade dune star","linen apple mist","birch coral moon"]):
    rows.append(row("g"+str(i),text,language="id" if i%2 else "en"))
out=m.partition_mechanical(rows)
assert out==m.partition_mechanical(list(reversed(rows)))
assert sum(x.get("all",0) for x in out["counts"].values())==len(rows)
assert all(out["counts"][s].get("all",0)>0 for s in ("train","dev","test"))
assert len({out["rows"]["toy-"+i]["component"] for i in "abcd"})==1
assert out["rows"]["toy-e"]["component"]==out["rows"]["toy-f"]["component"]
assert out["fuzzy_candidate_count"]>=1 and out["fuzzy_review_required"]
assert out["rows"]["toy-a"]["normalized_sha256"]==out["rows"]["toy-d"]["normalized_sha256"]
assert out["rows"]["toy-a"]["raw_sha256"]!=out["rows"]["toy-d"]["raw_sha256"]
assert not out["training_allowed"] and out["human_gold_count"]==0
assert out["manifest_sha256"]==m.sha(m.encoded({k:v for k,v in out.items() if k!="manifest_sha256"}))

def changed(i,**kw):
    data=copy.deepcopy(rows)
    data[i].update(kw)
    return data

neg=[
    [],rows+[rows[0]],changed(0,role="HUMAN-GOLD"),changed(0,rights_status="APPROVED"),
    changed(0,human_reviewed=True),changed(0,role="BLIND"),changed(0,text="private input"),
    changed(0,text="toy secret\n"),changed(0,parent="toy-a"),changed(0,parent="toy-absent"),
    changed(0,parent="toy-c"),changed(0,parent="toy-b"),
    changed(1,parent="toy-absent"),
    changed(3,semantic_key="toy-contradiction"),changed(0,language="xx"),
    changed(0,semantic_key="not-toy"),changed(0,id="toy-b"),
    changed(0,split="train"),changed(0,text="toy "+"a"*300),changed(0,text="toy é"),
]
for i,data in enumerate(neg):
    try:
        m.partition_mechanical(data)
    except m.Reject:
        pass
    else:
        raise AssertionError("negative accepted "+str(i))
print("F1_CORPUS_MECHANICS",len(rows),"toy rows",out["component_count"],"components",
      out["fuzzy_candidate_count"],"fuzzy pairs",len(neg),"negative vectors",
      "deterministic manifest",out["manifest_sha256"],"counts",
      {k:v["all"] for k,v in out["counts"].items()},"actual split/training NOT RUN")
print("F1_CORPUS_INVENTORY_COUNTS",json.dumps(inventory["functional_counts"],sort_keys=True),
      "33 intents; human gold 0; rights HOLD")
