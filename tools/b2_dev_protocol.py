"""Exact in-memory development transport, not a product pack or loader."""
import json
import struct
import subprocess
from b2_linear import CLASSES,DIM,Linear

def model_frame(model,margin):
    if type(margin) is not int or not 1<=margin<=0xffffffff:
        raise ValueError("margin")
    if len(model.weights)!=CLASSES or len(model.bias)!=CLASSES:
        raise ValueError("model-shape")
    flat=[]
    for bias,weights in zip(model.bias,model.weights):
        if len(weights)!=DIM:
            raise ValueError("model-dimension")
        flat.extend((bias,*weights))
    if any(type(v) is not int or not -32768<=v<=32767 for v in flat):
        raise ValueError("model-range")
    return struct.pack("<I",margin)+struct.pack("<"+"h"*len(flat),*flat)

def call(probe,frame,raw):
    if type(raw) is not bytes or len(raw)>4096:
        raise ValueError("request-bound")
    p=subprocess.run([str(probe)],input=frame+raw,capture_output=True,timeout=5)
    if p.returncode!=0 or p.stderr or len(p.stdout)>65536:
        raise ValueError("native-dev-probe")
    stdout=p.stdout.decode("utf-8","strict").rstrip("\n")
    return json.loads(stdout),stdout
