"""F1 regression inventory and group-aware split mechanics.

No actual corpus import, training, private holdout access, or rights grant.
The public entrypoint emits only identities/counts of locked repo fixtures.
partition_mechanical() accepts only toy test vectors and is not a split lock.
"""
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SEED=20261124
SPLITS={"train":70,"dev":15,"test":15}
PINS={
    "tests/pipeline/functional-v1.json":"ef1cfdb87b4b36faf805f551523ba752ca38c65a",
    "tests/pipeline/raw-gold-v1.json":"e2c328ca211aa4a90f00e3fd2b94e0e572d42161",
    "tests/pipeline/f1-functional-v1.json":"08c97353580b97db7738d86d0c446367dd99aaf4",
    "tests/pipeline/f1-raw-gold-v1.json":"bcec0847640eea5a79fa23dceb40cb723eb5e9c3",
    "tests/pipeline/f1-v2-functional.json":"b85324dd85a840c15abad97a6ddc512f4b7d24eb",
    "tests/pipeline/f1-v2-raw-gold.json":"7fd6d5dbf08fde3a1acfd27133d8eeeebfb11926",
    "tests/spikes/s2/development-v1.json":"3081d95d327c2aa7851efaa673168591c1f7002c",
    "data/manifests/license-ledger-v1.json":"da53ad25f9f1b1e31f601ff43c7e1bcd78c18fa3",
    "data/manifests/corpus-protocol-v1.md":"5ba9a21857a78ad85c881e8c94e816d07880bb10",
}
KEYS={"id","intent","language","text","semantic_group","family","semantic_key",
      "parent","role","rights_status","human_reviewed"}


class Reject(ValueError):
    pass


def need(ok,code):
    if not ok:
        raise Reject(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()


def pinned(path):
    raw=(ROOT/path).read_bytes()
    actual=hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
    need(actual==PINS[path],"source-drift")
    return raw


def inventory():
    sources={}
    for p in PINS:
        raw=pinned(p)
        sources[p]={"git_blob":PINS[p],"sha256":sha(raw),"bytes":len(raw)}
    ledger=json.loads(pinned("data/manifests/license-ledger-v1.json"))
    need(ledger["license_decision"]=="PENDING-OWNER-AND-S5" and
         all(x["decision"]=="HOLD" and not x["training_allowed"] and
             not x["distribution_allowed"] for x in ledger["sources"]), "rights")
    expected=[("functional-v1.json",140,"raw-gold-v1.json",48),
              ("f1-functional-v1.json",232,"f1-raw-gold-v1.json",150),
              ("f1-v2-functional.json",202,"f1-v2-raw-gold.json",102)]
    combined=[]
    for name,n,labels,supported in expected:
        path="tests/pipeline/"+name
        cases=json.loads(pinned(path))["cases"]
        raw_gold=json.loads(pinned("tests/pipeline/"+labels))["cases"]
        need(len(cases)==n and len({x["id"] for x in cases})==n and
             len(raw_gold)==supported and set(raw_gold)=={x["id"] for x in cases
             if x["suite"]=="supported"},"regression-count")
        sources[path]["role"]="SELF-FUNCTIONAL-REGRESSION"
        sources[path]["suite_counts"]=dict(Counter(x["suite"] for x in cases))
        combined+=cases
    need(len(combined)==len({x["id"] for x in combined})==574,"case-id")
    counts=Counter(x["suite"] for x in combined)
    need(counts=={"supported":300,"ambiguity":60,"ood":47,"security":167},"case-count")
    intents=Counter(x["expected"]["intent"] for x in combined if x["suite"]=="supported")
    need(len(intents)==48 and all(n>=6 for n in intents.values()),"intent-count")
    s2=json.loads(pinned("tests/spikes/s2/development-v1.json"))
    need(len(s2["reference"])==32 and len(s2["development"])==100,"s2-count")
    return {"schema_version":1,"role":"REGRESSION-INVENTORY-NOT-CORPUS",
            "sources":sources,"functional_counts":dict(counts),"supported_intents":dict(intents),
            "s2_reference":32,"s2_development":100,"human_gold_count":0,
            "rights":"HOLD","actual_split":"NOT RUN","training":"NOT RUN",
            "blind":"NOT RUN","training_allowed":False,"distribution_allowed":False}


def normalize(text):
    # Grouping ONLY; preserve exact UTF-8 bytes for actual inputs and labels.
    return " ".join(unicodedata.normalize("NFKC",text).casefold().split())


def trigrams(text):
    return {text[i:i+3] for i in range(len(text)-2)}


def similar(a,b):
    if min(len(a),len(b))<8:
        return False
    for x,y in ((set(a.split()),set(b.split())),(trigrams(a),trigrams(b))):
        if x and y and len(x&y)*100>=85*len(x|y):
            return True
    return False


def partition_mechanical(records):
    """Connected components and deterministic 70/15/15 mechanics on toy data.

    Not an actual corpus validator, authorization or human review. Only
    closed toy role with no training/distribution rights is accepted.
    """
    need(type(records) is list and 1<=len(records)<=500,"size")
    by_id={}
    normal={}
    for row in records:
        need(type(row) is dict and set(row)==KEYS,"shape")
        need(row["role"]=="MECHANICAL-TOY" and row["rights_status"]=="HOLD"
             and row["human_reviewed"] is False,"actual-corpus-not-authorized")
        for k in ("id","intent","semantic_group","family","semantic_key"):
            need(type(row[k]) is str and re.fullmatch(r"toy-[a-z0-9.-]{1,64}",row[k]),"toy-id")
        need(row["id"] not in by_id and row["language"] in {"id","en","mixed"},"record")
        need(type(row["text"]) is str and row["text"].startswith("toy ") and
             row["text"].isascii() and 4<len(row["text"])<=256 and
             all(32<=ord(c)<127 for c in row["text"]),"toy-text")
        need(row["parent"] is None or type(row["parent"]) is str,"parent")
        by_id[row["id"]]=row
        normal[row["id"]]=normalize(row["text"])
    for i,row in by_id.items():
        parent=row["parent"]
        if parent is not None:
            need(parent in by_id and by_id[parent]["semantic_group"]==row["semantic_group"],"parent-group")
    for i,row in by_id.items():
        parent=row["parent"]
        seen={i}
        while parent is not None:
            need(parent not in seen,"parent-cycle")
            seen.add(parent)
            parent=by_id[parent]["parent"]
    ids=sorted(by_id)
    root={i:i for i in ids}

    def find(i):
        while root[i]!=i:
            root[i]=root[root[i]]
            i=root[i]
        return i

    def join(a,b):
        x,y=sorted((find(a),find(b)))
        root[y]=x

    members={}
    text_semantics={}
    for i in ids:
        row=by_id[i]
        n=normal[i]
        previous=text_semantics.setdefault(n,row["semantic_key"])
        need(previous==row["semantic_key"],"duplicate-semantic-conflict")
        for k,v in (("group",row["semantic_group"]),("family",row["family"]),
                    ("semantic",row["semantic_key"]),("normalized",n)):
            key=k,v
            if key in members:
                join(i,members[key])
            else:
                members[key]=i
        if row["parent"] is not None:
            join(i,row["parent"])
    fuzzy=[]
    for a,b in combinations(ids,2):
        if normal[a]!=normal[b] and similar(normal[a],normal[b]):
            fuzzy.append((a,b))
            join(a,b)
    components=defaultdict(list)
    for i in ids:
        components[find(i)].append(i)
    groups=[(sha(encoded(v)),v) for v in components.values()]
    groups.sort(key=lambda x:(-len(x[1]),sha(f"{SEED}/{x[0]}".encode())))
    totals=Counter()
    def strata(i):
        x=by_id[i]
        return ("all","intent:"+x["intent"],"language:"+x["language"],
                "joint:"+x["intent"]+"/"+x["language"])
    for i in ids:
        totals.update(strata(i))
    assigned={s:Counter() for s in SPLITS}
    result={}
    for gid,items in groups:
        add=Counter(k for i in items for k in strata(i))
        # Squared deviation, integer arithmetic, stable ties. Normalize the
        # delta by stratum size to avoid common categories swamping rare ones.
        def cost(s):
            delta=0
            for k,n in add.items():
                before=100*assigned[s][k]-SPLITS[s]*totals[k]
                after=before+100*n
                delta+=(after*after-before*before)*1000//totals[k]
            return delta,sha(f"{SEED}/{gid}/{s}".encode())
        split=min(SPLITS,key=cost)
        assigned[split].update(add)
        for i in items:
            result[i]={"component":gid,"split":split,
                       "raw_sha256":sha(by_id[i]["text"].encode()),
                       "normalized_sha256":sha(normal[i].encode())}
    need(set(result)==set(ids),"partition")
    for _,items in groups:
        need(len({result[i]["split"] for i in items})==1,"split-leak")
    report={"status":"MECHANICAL-ONLY-NOT-ACTUAL-SPLIT","seed":SEED,"target_percent":SPLITS,
            "rows":result,"counts":{s:dict(sorted(c.items())) for s,c in assigned.items()},
            "component_count":len(groups),"fuzzy_candidate_count":len(fuzzy),
            "fuzzy_review_required":bool(fuzzy),"training_allowed":False,
            "distribution_allowed":False,"human_gold_count":0}
    report["manifest_sha256"]=sha(encoded(report))
    return report


if __name__=="__main__":
    print("F1_CORPUS_INVENTORY",json.dumps(inventory(),sort_keys=True,separators=(",",":")))
