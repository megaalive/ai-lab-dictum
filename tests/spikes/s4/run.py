"""S4 independent Python binary32 reference + C comparison."""
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATOL = 1e-3
RTOL = 1e-4


def f32(x):
    return struct.unpack("<f",struct.pack("<f",x))[0]


def quant(x,s):
    x,s = f32(x),f32(s)
    if not math.isfinite(x) or not math.isfinite(s) or s<=0:
        raise ValueError("invalid-quant")
    return min(127,max(-127,round(x/s)))


def f32_dot(x,w):
    acc = f32(0)
    for a,b in zip(x,w,strict=True):
        acc = f32(acc+f32(f32(a)*f32(b)))
    return acc


def parameters():
    """Enumerate candidate configuration, not an instantiated/trained model."""
    d,ff,vocab,ctx,layers,intents,tags = 128,512,4096,128,4,48,21
    shapes = {"token_embedding":[vocab,d],"position_embedding":[ctx,d],
              "final_norm.weight":[d],"final_norm.bias":[d],
              "intent.weight":[intents,d],"intent.bias":[intents],
              "slot.weight":[tags,d],"slot.bias":[tags]}
    for layer in range(layers):
        prefix = f"layer{layer}."
        for op in ("q","k","v","o"):
            shapes[prefix+op+".weight"]=[d,d]
            shapes[prefix+op+".bias"]=[d]
        for op,shape in (("ff.in",[ff,d]),("ff.out",[d,ff])):
            shapes[prefix+op+".weight"]=shape
            shapes[prefix+op+".bias"]=[shape[0]]
        for norm in ("norm1","norm2"):
            shapes[prefix+norm+".weight"]=[d]
            shapes[prefix+norm+".bias"]=[d]
    n=sum(math.prod(shape) for shape in shapes.values())
    # Bias, layernorm, positions, heads included; no weight sharing.
    independent = vocab*d+ctx*d+2*d+layers*(4*(d*d+d)+2*d*ff+ff+d+4*d)+(intents+tags)*(d+1)
    assert n==independent
    return {"config":{"vocab":vocab,"context":ctx,"layers":layers,"d_model":d,
                      "ff":ff,"heads":4,"intent_labels":intents,"slot_tags":tags},
            "tensor_count":len(shapes),"parameter_count":n,"fp32_payload_bytes":n*4,
            "int8_lower_bound_payload_bytes":n,"tensors":shapes,
            "limitations":"config enumeration, not actual trained weights; scales/alignment/metadata/activations excluded"}


def main():
    raw = (HERE/"vectors-v1.json").read_bytes()
    v = json.loads(raw)
    assert len(sys.argv)==2
    native=Path(sys.argv[1]).resolve(strict=True)
    # Fixed test binary compiled by CI; never a model-supplied command.
    p=subprocess.run([str(native)],stdin=subprocess.DEVNULL,capture_output=True,
                     check=True,timeout=5)
    assert not p.stderr and len(p.stdout)<65536
    records={}
    for line in p.stdout.decode("ascii").splitlines():
        fields=line.split()
        key=tuple(fields[:2]) if fields[0] in {"Q","R","ROW","TOP"} else (fields[0],)
        assert key not in records
        records[key]=fields[len(key):]
    passed=0
    def check(name,ok):
        nonlocal passed
        print(f"{'PASS' if ok else 'FAIL'} {name}")
        if not ok:
            raise AssertionError(name)
        passed+=1
    for i,q in enumerate(v["quant"]):
        check(f"q-{i}",quant(q["x"],q["scale"])==q["expected"]==
              int(records.pop(("Q",str(i)))[0]))
    invalid=[(math.nan,1),(math.inf,1),(-math.inf,1),(1,0),(1,-1),(1,math.nan),(1,math.inf)]
    for i,(x,s) in enumerate(invalid):
        rejected=False
        try:
            quant(x,s)
        except ValueError:
            rejected=True
        check(v["invalid"][i],rejected and records.pop(("R",str(i)))==["0"])
    for key,expected in [("OVERFLOW_POS",0),("OVERFLOW_NEG",0),("EDGE_MAX",2**31-1),("EDGE_MIN",-2**31)]:
        check(key,int(records.pop((key,))[0])==expected)
    qi=[quant(x,v["input_scale"]) for x in v["input"]]
    errors=[]
    relative=[]
    for i,(w,s) in enumerate(zip(v["weights"],v["row_scale"],strict=True)):
        qw=[quant(x,s) for x in w]
        acc=sum(a*b for a,b in zip(qi,qw,strict=True))
        fp=f32_dot(v["input"],w)
        deq=f32(f32(acc)*f32(f32(s)*f32(v["input_scale"])))
        a,b,c=records.pop(("ROW",str(i)))
        check(f"exact-acc-{i}",acc==v["expected_acc"][i]==int(a))
        for mode,expected,actual in [("fp32",fp,float(b)),("int8",deq,float(c))]:
            err=abs(actual-expected)
            errors.append(err)
            if expected!=0:
                relative.append(err/abs(expected))
            check(f"{mode}-parity-{i}",math.isfinite(actual) and err<=ATOL+RTOL*abs(expected))
    for i,scores in enumerate(v["tie_scores"]):
        best=max(range(len(scores)),key=lambda j:(f32(scores[j]),-j))
        check(f"tie-{i}",best==v["top"][i]==int(records.pop(("TOP",str(i)))[0]))
    check("no-extra-records",not records)
    param=parameters()
    print("S4_CONFIG "+json.dumps(param,sort_keys=True))
    print("S4_RESULT "+json.dumps({"checks":passed,"mismatch":0,"max_abs":max(errors),
          "max_relative":max(relative,default=0),"atol":ATOL,"rtol":RTOL,
          "fixture_sha256":hashlib.sha256(raw).hexdigest(),
          "native_sha256":hashlib.sha256(native.read_bytes()).hexdigest()},sort_keys=True))
    print("S4 PASS tiny synthetic only; full model, native pack loader, training and F2/F4 parity NOT RUN")


if __name__=="__main__":
    main()
