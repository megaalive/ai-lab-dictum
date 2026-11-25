"""Standalone native candidate domain parity; v1 rejection stays intact."""
import copy
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path
from wire import Reject as WireReject,decode_frame
from run import fixture

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from f1_slot_domains import Reject,load,validate_value

contract,validator=load()
probe,v1=sys.argv[1:3]
seen=set()
stats=Counter()
rng=random.Random(23031)

def call(program,args,data):
    p=subprocess.run([program,*args],input=data,capture_output=True,timeout=5)
    assert p.returncode==0 and not p.stderr
    return p.stdout.decode("ascii").strip()

def case(data,expected=None,strict=True):
    if data in seen:
        return
    seen.add(data)
    try:
        obj=decode_frame(data)
        try:
            validate_value(obj,contract,validator)
            oracle="ok"
        except Reject:
            oracle="schema/structure"
    except WireReject as exc:
        oracle=str(exc)
    actual=call(probe,[],data)
    if not strict and oracle.startswith("byte/") and actual.startswith("byte/"):
        pass
    else:
        assert oracle==actual,(oracle,actual)
    if expected is not None:
        assert oracle==expected,(expected,oracle)
    stats["positive" if oracle=="ok" else "negative"]+=1

def enc(obj,ascii_only=True,sort=False):
    return json.dumps(obj,ensure_ascii=ascii_only,sort_keys=sort,separators=(",",":")).encode()

scope=contract["scope"]
for kind,values in scope.items():
    for value in values:
        obj={"kind":kind,"value":value}
        case(enc(obj), "ok")
        case(enc({"value":value,"kind":kind},False), "ok")
        for wrong in scope:
            if wrong!=kind and value not in scope[wrong]:
                case(enc({"kind":wrong,"value":value}),"schema/structure")
        for altered in (value+" ", " "+value, value+"\u202e", value+"\u0001",
                        value+"/", value.upper(), value+"CANARY_SECRET"):
            if altered not in values:
                case(enc({"kind":kind,"value":altered}),"schema/structure")
        case(enc({**obj,"authority":True}),"schema/structure")
        case(enc({"kind":kind}),"schema/structure")
        case(enc({"kind":kind,"value":1}),"schema/structure")
for obj in (None,[],{},True,{"kind":"filename","value":"demo-worker"},
            {"kind":"dns-record-type","value":"AAAA"},{"kind":"literal-text","value":"é"*129},
            {"kind":"network-target","value":"127.0.0.1"}):
    case(enc(obj),"schema/structure")
for data in (b'{"kind":"dns-name","kind":"dns-name","value":"example.test"}',
             b'{"kind":"dns-name","k\\u0069nd":"dns-name","value":"example.test"}',
             b'{"kind":"literal-text","value":"\\ud800"}',b'{"kind":"literal-text","value":"\\u0000"}',
             b'{"kind":"literal-text","value":"\xff"}',b'\xef\xbb\xbf{}',b'{}{}',
             b' '*32769,b'{"kind":"literal-text","value":"'+b'a'*4097+b'"}'):
    case(data)
for i in range(256):
    kind=rng.choice(list(scope))
    data=bytearray(enc({"kind":kind,"value":rng.choice(scope[kind])}))
    for _ in range(rng.randrange(1,4)):
        data[rng.randrange(len(data))]=rng.randrange(256)
    case(bytes(data),strict=False)
# A v2 candidate must never be interpreted as one of the old v1 value kinds.
chain=next(c for c in fixture("chains")["chains"] if c["objects"]["ir"]["slots"])
for kind,values in scope.items():
    ir=copy.deepcopy(chain["objects"]["ir"])
    ir["slots"][0]["value"]={"kind":kind,"value":values[0]}
    assert call(v1,["ir"],enc(ir))=="schema/structure",kind
assert stats["positive"]>=40 and stats["negative"]>=100
print("F1_NATIVE_CANDIDATE_DIFF",dict(stats),"unique",len(seen),
      "v1 rejection",len(scope),"seed 23031; no full native IR v2 or authority")
