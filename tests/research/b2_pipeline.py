"""Fixed-weight integration check; no fit to project text or labels."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/"tests/pipeline"
spec=importlib.util.spec_from_file_location("pipeline_oracle",HERE/"run.py")
o=importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
from b2_linear import CLASSES,DIM,Linear,extract,rank
from b2_dev_protocol import call,model_frame

b2probe=sys.argv[3]
fixed=Linear([[((c+3)*(i+7)+i//17)%23-11 for i in range(DIM)] for c in range(CLASSES)],
             [c%11-5 for c in range(CLASSES)])
fixed_frame=model_frame(fixed,1)
cases=o.cases+json.loads((HERE/"f1-functional-v1.json").read_bytes())["cases"]+json.loads((HERE/"f1-v2-functional.json").read_bytes())["cases"]
registry={i:n for n,i in enumerate(o.all_registry)}
stats={"all":0,"unchanged_negative":0,"guard_abstained":0,"guard_retained":0,"invalid_byte_cases":0,"oversize_rejected":0}
first={}
def run_b0(raw):
    p=subprocess.run([o.probe,"B0"],input=raw,capture_output=True,timeout=5)
    assert p.returncode==0 and not p.stderr
    stdout=p.stdout.decode().rstrip("\n")
    value=json.loads(stdout)
    o.check_invariants(value,raw,stdout)
    return value
def mask_spans(b0):
    spans=[]
    if b0["nlu"]:
        for x in b0["nlu"]["slot_candidates"]:
            s=x["source"]
            if s["kind"]=="context-ref":
                s=b0["context"]["time_candidate"]
            else:
                s=s["span"]
            spans.append((s["start"],s["end"]))
    out=[]
    for a,b in sorted(spans):
        if out and out[-1][1]>a:
            out[-1]=(out[-1][0],max(out[-1][1],b))
        else:
            out.append((a,b))
    return out
def verify(raw,b0,model,frame,margin):
    obj,stdout=call(b2probe,frame,raw)
    trace=obj.pop("trace")
    o.check_invariants(obj,raw,stdout)
    proposal=b0["view"]["decision"]=="allow-proposal"
    expected_class=registry[b0["view"]["intent"]] if proposal else -1
    assert trace["grammar_class"]==expected_class
    if b0["context"] is None:
        assert not trace["features_valid"] and trace["rank"]==-1 and obj==b0
        return "invalid_byte_cases"
    masks=mask_spans(b0)
    assert trace["masks"]==[list(x) for x in masks]
    features=extract(raw,masks)
    scores=model.scores(features)
    selected=rank(features,scores,margin)
    assert trace["features_valid"] and tuple(trace["features"])==features
    assert tuple(trace["scores"])==scores and trace["rank"]==selected
    if not proposal:
        assert obj==b0
        return "unchanged_negative"
    if selected==expected_class:
        assert obj==b0
        return "guard_retained"
    assert obj["view"]["decision"]=="unsupported" and obj["plan"] is None
    assert not obj["view"]["execution_allowed"]
    return "guard_abstained"

for row in cases:
    raw=o.data(row)
    b0=run_b0(raw)
    stats["all"]+=1
    if len(raw)>4096:
        p=subprocess.run([b2probe],input=fixed_frame+raw,capture_output=True,timeout=5)
        assert p.returncode==2 and not p.stdout
        stats["oversize_rejected"]+=1
        continue
    kind=verify(raw,b0,fixed,fixed_frame,1)
    stats[kind]+=1
    if b0["view"]["decision"]=="allow-proposal":
        first.setdefault(b0["view"]["intent"],(raw,b0))
assert stats["all"]==574 and len(first)==48
# Controlled one-hot bias vectors exercise retain and tie transitions for
# every intent; these are not classifier accuracy or fitted models.
zero=Linear.zero()
zero_frame=model_frame(zero,1)
for intent,(raw,b0) in first.items():
    model=Linear.zero()
    model.bias[registry[intent]]=100
    assert verify(raw,b0,model,model_frame(model,1),1)=="guard_retained"
    assert verify(raw,b0,zero,zero_frame,1)=="guard_abstained"
    assert verify(raw,b0,model,model_frame(model,101),101)=="guard_abstained"
for frame in (b"",fixed_frame[:100],b"\0\0\0\0"+fixed_frame[4:]):
    p=subprocess.run([b2probe],input=frame+b"x",capture_output=True,timeout=5)
    assert p.returncode==2 and not p.stdout
print("F1_B2_COMMON_EXTRACTOR",json.dumps(stats,sort_keys=True),
      "144 controlled guard transitions; 3 malformed transports rejected; no trained B2 metrics")
