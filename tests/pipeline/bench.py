"""C-09: warm native pipeline, isolated B0/B1 processes, all fixed cases."""
import hashlib
import json
import math
import platform
import random
import statistics
import struct
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
name=sys.argv[2] if len(sys.argv)==3 else "functional-v1.json"
assert name in {"functional-v1.json","f1-functional-v1.json"}
raw=(HERE/name).read_bytes()
manifest=json.loads(raw)
cases=manifest["cases"]
n={"functional-v1.json":140,"f1-functional-v1.json":232}[name]
assert len(cases)==n and len({r["id"] for r in cases})==n
assert manifest["reference_unix_s"]==1760000600

def payload(row):
    if "hex" in row:
        return bytes.fromhex(row["hex"])
    if "repeat" in row:
        return (row["repeat"][0]*row["repeat"][1]).encode()
    return row["text"].encode()

# Fixed reproducible order, shared between models; one full unmeasured pass.
order=list(range(len(cases)))
random.Random(23009).shuffle(order)
frames=[payload(cases[i]) for i in order]
batch=b"".join(struct.pack("<I",len(f))+f for f in frames)*11
print("WARM_ENV",name,platform.platform(),"machine",platform.machine(),"python",platform.python_version(),
      "corpus",hashlib.sha256(raw).hexdigest(),"order_seed",23009,
      "executable_sha256",hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())

for model in ("B0","B1"):
    p=subprocess.run([sys.argv[1],model,str(n)],input=batch,capture_output=True,timeout=60)
    assert p.returncode==0 and not p.stderr
    lines=p.stdout.decode("ascii").splitlines()
    assert len(lines)==10*n+1 and lines[-1].startswith("RSS_KIB ")
    rss=int(lines.pop().split()[1])
    times=[]
    seen={}
    for row,line in enumerate(lines):
        rep,i,ns,outcome=map(int,line.split())
        assert (rep,i)==(1+row//n,row%n)
        assert ns>=0 and 0<=outcome<4
        if i in seen:
            assert outcome==seen[i],"nondeterministic outcome"
        seen[i]=outcome
        times.append(ns/1000)
    assert len(seen)==n and rss>0
    supported=[t for j,t in enumerate(times) if cases[order[j%n]]["suite"]=="supported"]
    def latency(values):
        v=sorted(values)
        return {"n":len(v),"p50_us":statistics.median(v),"p95_us":v[math.ceil(.95*len(v))-1]}
    print("WARM_PIPELINE" if n==140 else "F1_WARM_PIPELINE",model,json.dumps({"all":latency(times),"supported":latency(supported),
        "peak_rss_kib":rss,"warmup":n,"repeats":10,"clock":"CLOCK_MONOTONIC",
        "scope":"in-process input through rendered view; excludes subprocess launch and harness I/O",
        "rss_scope":"entire benchmark process including libcrypto, buffers, loader"},sort_keys=True))
