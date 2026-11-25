"""Mutate actual native v2 frames and prove oracle rejects inconsistent chains."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("pipeline_oracle", HERE/"run.py")
o=importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
from wire import Reject as WireReject
from f1_slot_domains import Reject as DomainReject

def result(text):
    p=subprocess.run([o.probe,"B0"],input=text.encode(),capture_output=True,timeout=5)
    assert p.returncode==0 and not p.stderr
    raw=p.stdout.decode().rstrip("\n")
    obj=json.loads(raw)
    o.check_invariants(obj,text.encode(),raw)
    assert obj["view"]["decision"]=="allow-proposal"
    return obj

count=0

def reject(text,obj,fn):
    global count
    bad=copy.deepcopy(obj)
    fn(bad)
    raw=json.dumps(bad,ensure_ascii=False,separators=(",",":"))
    try:
        o.check_invariants(bad,text.encode(),raw)
    except (AssertionError,WireReject,DomainReject,KeyError):
        count+=1
    else:
        raise AssertionError("semantic mutation accepted")

def put(path,value):
    def fn(obj):
        p=obj
        for key in path[:-1]:
            p=p[key]
        p[path[-1]]=value
    return fn

def resign(obj):
    plan=obj["plan"]
    unsigned={k:v for k,v in plan.items() if k!="digest"}
    plan["digest"]=hashlib.sha256(b"dictum:execution-plan:v2\n"+
        json.dumps(unsigned,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

t="propose dns lookup example.test"
v=result(t)
for path,value in [
    (["nlu","schema_version"],1),(["ir","catalog","version"],1),
    (["ir","context_id"],"a"*64),(["policy","representation"],"narrative-guidance"),
    (["policy","effect","axes"],[]),(["policy","decision"],"allow-execute-eligible"),
    (["plan","schema_version"],1),(["plan","digest"],"0"*64),
    (["ir","slots",0,"value","value"],"example.com"),
    (["ir","slots",0,"provenance","span","start"],0),
    (["ir","slots",1,"provenance","kind"],"input-span"),
    (["ir","slots",1,"value","value"],"AAAA"),
    (["view","execution_allowed"],True),(["view","warning"],"safe"),
]:
    reject(t,v,put(path,value))
for path,value in [
    (["plan","action","operation","handler"],"proposal.memory.summary"),
    (["plan","target_bindings"],[]),(["plan","action","operation","input_slots"],["domain"]),
]:
    def fn(obj,path=path,value=value):
        put(path,value)(obj)
        resign(obj)
    reject(t,v,fn)

t2="guide service crash diagnosis demo.service"
v2=result(t2)
assert v2["plan"] is None and v2["view"]["representation"]=="narrative-guidance"
reject(t2,v2,put(["plan"],v["plan"]))
reject(t2,v2,put(["view","slots"],{}))
reject(t2,v2,put(["view","guidance_text"],"restart automatically"))
reject(t2,v2,put(["policy","representation"],"structured-proposal"))

t3="propose archive compression /fixture/projects to /fixture/data/new-report.tar.gz"
v3=result(t3)
def nested(obj):
    for s in obj["ir"]["slots"]:
        if s["name"]=="destination":
            s["value"]["value"]="/fixture/projects/new-projects.tar.gz"
    obj["view"]["slots"]["destination"]["value"]="/fixture/projects/new-projects.tar.gz"
reject(t3,v3,nested)
reject(t3,v3,put(["view","limitations"],"safe and verified"))

t4="explain option --numeric for ss"
v4=result(t4)
def option(obj):
    for s in obj["ir"]["slots"]:
        if s["name"]=="option":
            s["value"]["value"]="--failed"
    obj["view"]["slots"]["option"]["value"]="--failed"
reject(t4,v4,option)
assert count==24
print("F1_V2_SEMANTIC_MUTATIONS",count,"inconsistent chains rejected including rehashed wrong recipes")
