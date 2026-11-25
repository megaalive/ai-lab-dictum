"""V2 generated native structure vs closed Draft 2020-12 oracle.

Compare exact native decoded spans, both version families, mutation rejection
and independent domain-separated digests. Does not accept actual plan authority.
"""
import copy
import hashlib
import json
import random
import subprocess
import sys
from collections import Counter
from run import SCHEMAS as V1, SCHEMA_DIR
from schema_profile import prepare_validators
from wire import Reject,decode_frame,read_source
from differential import inspect
from v2_vectors import chains

probe=sys.argv[1]
V2={k:v.replace("-v1.schema.json","-v2.schema.json") for k,v in V1.items()}
validators,_,retrievals=prepare_validators({n:read_source(SCHEMA_DIR/n)
                                         for n in [*V1.values(),*V2.values()]})
seen=set()
stats=Counter()
rng=random.Random(23038)

def enc(obj,ascii_only=False,sort=False):
    return json.dumps(obj,ensure_ascii=ascii_only,sort_keys=sort,separators=(",",":")).encode()

def invoke(mode,raw):
    p=subprocess.run([probe,mode],input=raw,capture_output=True,timeout=5)
    assert p.returncode==0 and not p.stderr
    return p.stdout.decode("ascii").splitlines()

def case(stage,version,raw,expected=None,strict=True):
    key=(stage,version,raw)
    if key in seen:
        return
    seen.add(key)
    try:
        obj=decode_frame(raw)
        oracle="ok" if validators[(V2 if version==2 else V1)[stage]].is_valid(obj) else "schema/structure"
    except Reject as exc:
        obj=None
        oracle=str(exc)
    actual,*lines=invoke(stage+("-v2" if version==2 else ""),raw)
    if not strict and oracle.startswith("byte/") and actual.startswith("byte/"):
        pass
    else:
        assert actual==oracle,(stage,version,actual,oracle)
    if expected is not None:
        assert oracle==expected,(stage,version,oracle,expected)
    if actual=="ok":
        inspect(lines,raw,obj)
    else:
        assert not lines
    stats[stage,version,"positive" if oracle=="ok" else "negative"]+=1

def mutate(stage,obj,path,value):
    v=copy.deepcopy(obj)
    ptr=v
    for k in path[:-1]:
        ptr=ptr[k]
    ptr[path[-1]]=value
    case(stage,2,enc(v))

def digest(obj,version):
    return hashlib.sha256(f"dictum:execution-plan:v{version}\n".encode()+
        enc({k:v for k,v in obj.items() if k!="digest"},sort=True)).hexdigest()

base=list(chains())
digest_checks=0
for chain in base:
    for stage,obj in chain.items():
        raw=enc(obj)
        case(stage,2,raw,"ok")
        case(stage,2,enc(obj,True,True),"ok")
        case(stage,1,raw,"schema/structure")
        v=copy.deepcopy(obj)
        v["schema_version"]=1
        case(stage,2,enc(v),"schema/structure")
        v=copy.deepcopy(obj)
        v["schema_version"]=3
        case(stage,2,enc(v),"schema/structure")
        for name in obj:
            v=copy.deepcopy(obj)
            del v[name]
            case(stage,2,enc(v))
        for name,value in [("unknown",1),("schema_version",True),("schema_version","2")]:
            mutate(stage,obj,[name],value)
        for name in ("catalog","policy"):
            if name in obj:
                mutate(stage,obj,[name,"version"],1)
                mutate(stage,obj,[name,"version"],3)
    plan=copy.deepcopy(chain["plan"])
    plan["digest"]=digest(plan,2)
    for ascii_only,sort in [(False,False),(True,True)]:
        assert invoke("digest",enc(plan,ascii_only,sort))==[plan["digest"]+" match"]
        digest_checks+=1
    plan["digest"]=digest(plan,1)
    assert invoke("digest",enc(plan))==[digest(plan,2)+" mismatch"]
    digest_checks+=1
    plan["action"]["kind"]="execution-candidate"
    assert invoke("digest",enc(plan))==["invalid"]
    digest_checks+=1
    case("plan",2,enc(plan),"schema/structure")
    p=copy.deepcopy(chain["policy"])
    p["decision"]="allow-execute-eligible"
    case("policy",2,enc(p),"schema/structure")
    p=copy.deepcopy(chain["policy"])
    p["representation"]="executable"
    case("policy",2,enc(p),"schema/structure")

# Independent hand-written samples of all eleven added types.
samples={"utility-id":"ss","option-id":"--numeric","dns-name":"example.test",
    "network-target":"2001:db8::10","local-service":"demo.service",
    "literal-text":"café","head-tail-direction":"first","process-name":"demo-worker",
    "package-id":"demo-package:amd64","package-query":"fixture package","dns-record-type":"A"}
seed=next(c for c in base if c["ir"]["slots"])
for kind,value in samples.items():
    ir=copy.deepcopy(seed["ir"])
    ir["slots"][0]["value"]={"kind":kind,"value":value}
    case("ir",2,enc(ir),"ok")
    case("ir",2,enc(ir,True,True),"ok")
    case("ir",1,enc(ir),"schema/structure")
    # Version-only downgrade still rejected for an unknown v1 value kind.
    old=copy.deepcopy(ir)
    old["schema_version"]=1
    old["catalog"]["version"]=1
    case("ir",1,enc(old),"schema/structure")
    for wrong in ("",1,None,True,["x"],"x"*257):
        mutate("ir",ir,["slots",0,"value","value"],wrong)
    mutate("ir",ir,["slots",0,"value","kind"],"unknown")
    mutate("ir",ir,["slots",0,"value","extra"],1)
    nlu=copy.deepcopy(seed["nlu"])
    nlu["slot_candidates"]=[{"id":0,"slot":"candidate","source":{
        "kind":"context-ref","candidate_id":"a"*32,"expected_kind":kind}}]
    if nlu["intent_candidates"]:
        nlu["intent_candidates"][0]["slot_candidate_ids"]=[0]
    case("nlu",2,enc(nlu),"ok")
    case("nlu",1,enc(nlu),"schema/structure")
    mutate("nlu",nlu,["slot_candidates",0,"source","expected_kind"],"unknown")
for i in range(256):
    stage=rng.choice(list(V2))
    raw=bytearray(enc(rng.choice(base)[stage]))
    for _ in range(rng.randrange(1,4)):
        raw[rng.randrange(len(raw))]=rng.randrange(256)
    case(stage,2,bytes(raw),strict=False)
assert not retrievals
assert all(stats[s,2,"positive"] and stats[s,2,"negative"] for s in V2)
assert len(seen)>=300
print("F1_IR_V2_DIFFERENTIAL",len(seen),"unique stage/version/frame vectors; seed 23038",
      "digest checks",digest_checks,"mismatches 0; retrievals 0; counts",
      {"/".join(map(str,k)):v for k,v in sorted(stats.items())})
