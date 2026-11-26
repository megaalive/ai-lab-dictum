"""Grammar-independent mask parity and veto-only boundary; no fit."""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/"tests/pipeline"
spec=importlib.util.spec_from_file_location("pipeline_oracle",HERE/"run.py")
o=importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
from b2_linear import CLASSES,DIM,Linear,extract,rank
from b2_dev_protocol import call,model_frame
from f1_compare import probe_result

compose,cli,stable=sys.argv[1:4]
allowed={x.encode() for vs in o.fixture["scope"].values() for x in vs}
allowed|={x.encode() for vs in o.domains["scope"].values() for x in vs}
allowed|={b"tcp",b"udp",b"all"}
registry={i:n for n,i in enumerate(o.all_registry)}
fixed=Linear([[((c+3)*(i+7)+i//17)%23-11 for i in range(DIM)] for c in range(CLASSES)],
             [c%11-5 for c in range(CLASSES)])

def tokens(raw):
    """Independent byte-token oracle; retain completed spans on rejection."""
    result=[]
    pos=0
    while pos<len(raw):
        while pos<len(raw) and raw[pos]==32:
            pos+=1
        if pos==len(raw) or len(result)==64:
            break
        if raw[pos]==34:
            a=pos+1
            end=raw.find(b'"',a)
            if end<=a or (end+1<len(raw) and raw[end+1]!=32):
                break
            result.append((a,end,True))
            pos=end+1
        else:
            a=pos
            end=raw.find(b" ",a)
            if end<0:
                end=len(raw)
            if b'"' in raw[a:end]:
                break
            pos=end
            if end==len(raw) and raw[end-1:end]==b"?" and re.fullmatch(rb"[A-Za-z0-9]*",raw[a:end-1]):
                end-=1
            if a<end:
                result.append((a,end,False))
    return result

def masks(raw):
    runs=[]
    previous=False
    for a,b,quoted in tokens(raw):
        value=raw[a:b]
        masked=quoted or value.startswith(b"/") or value.isdigit() or value in allowed
        if masked:
            if previous:
                runs[-1]=(runs[-1][0],b)
            else:
                runs.append((a,b))
        previous=masked
    assert len(runs)<=32
    return tuple(runs)

def baseline(raw):
    value,stdout=probe_result(compose,"B0",raw)
    o.check_invariants(value,raw,stdout)
    return value

def verify(raw,b0,model,margin):
    obj,stdout=call(stable,model_frame(model,margin),raw)
    trace=obj.pop("trace")
    o.check_invariants(obj,raw,stdout)
    proposal=b0["view"]["decision"]=="allow-proposal"
    expected_class=registry[b0["view"]["intent"]] if proposal else -1
    assert trace["grammar_class"]==expected_class
    if b0["context"] is None:
        assert obj==b0 and not trace["features_valid"] and trace["rank"]==-1
        return None
    expected=masks(raw)
    features=extract(raw,expected)
    scores=model.scores(features)
    selected=rank(features,scores,margin)
    assert trace["masks"]==[list(x) for x in expected],(raw,trace["masks"],expected)
    assert trace["features_valid"] and tuple(trace["features"])==features
    assert tuple(trace["scores"])==scores and trace["rank"]==selected
    if not proposal or selected==expected_class:
        assert obj==b0
    else:
        assert obj["view"]["decision"]=="unsupported" and obj["plan"] is None
        assert obj["view"]["execution_allowed"] is False
    return features

cases=o.cases+json.loads((HERE/"f1-functional-v1.json").read_bytes())["cases"]+json.loads((HERE/"f1-v2-functional.json").read_bytes())["cases"]
first={}
checked=invalid=oversize=0
for row in cases:
    raw=o.data(row)
    if len(raw)>4096:
        oversize+=1
        continue
    b0=baseline(raw)
    feature=verify(raw,b0,fixed,1)
    checked+=1
    invalid+=feature is None
    if b0["view"]["decision"]=="allow-proposal":
        first.setdefault(b0["view"]["intent"],raw)
assert len(cases)==574 and len(first)==48
zero=Linear.zero()
for intent,raw in first.items():
    b0=baseline(raw)
    model=Linear.zero()
    model.bias[registry[intent]]=100
    for weights,margin in ((model,1),(model,101),(zero,1)):
        verify(raw,b0,weights,margin)

pairs=[
 (b"Rinci keadaan unit layanan demo.service sekarang",b"Rinci keadaan unit layanan worker.service sekarang"),
 (b"An unfamiliar sentence about demo.service status",b"An unfamiliar sentence about worker.service status"),
 (b"Locate literal text under /fixture/data",b"Locate literal text under /fixture/logs"),
 ('Locate exact literal "café" in text files under /fixture/data'.encode(),
  'Locate exact literal "teks uji" in text files under /fixture/logs'.encode()),
 (b"Display active udp connections with a maximum of 15 entries",
  b"Display active tcp connections with a maximum of 7 entries"),
 (b"Report system error journal records over the last 42 minutes",
  b"Report system error journal records over the last 17 minutes"),
 (b"Find process identifiers associated with name demo-worker",
  b'Find process identifiers associated with name "fixture worker"'),
 (b"Show unknown option --numeric with package demo-package",
  b"Show unknown option --failed with package libdemo1"),
 (b"arbitrary 12345 tokens /outside/file",b'arbitrary 987 tokens "/different path"'),
]
for a,b in pairs:
    x=verify(a,baseline(a),fixed,1)
    y=verify(b,baseline(b),fixed,1)
    assert x is not None and x==y,(a,b,x,y)
for raw in (b" ".join([b"123"]*64),b" ".join([b"123",b"word"]*32),
            b" ".join([b"123",b"word"]*33),b'bad "unterminated',
            b'one "two"three',b"?",b"123?",b"word 123?"):
    verify(raw,baseline(raw),fixed,1)
print("F1_B2_STABLE_MASKS",checked,"old native cases;",invalid,"invalid bytes;",oversize,"oversize excluded;",
      len(first)*3,"veto transitions;",len(pairs),"value-substitution pairs; 8 token-boundary cases")
