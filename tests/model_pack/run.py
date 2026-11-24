"""A6 synthetic format oracle; not runtime loader or signature verifier."""
import hashlib
import json
import math
import struct
from pathlib import Path

PREFIX = struct.Struct("<4sHHIIQQ")
ENTRY = struct.Struct("<IIQQII")
TENSOR = struct.Struct("<IHBB4IQQiIQII")
META = struct.Struct("<9IQI16s")
MAX_FILE = 128 * 1024 * 1024
MAX_PARAMS = 50_000_000
CATALOG = hashlib.sha256(b"dictum-synthetic-catalog-v1").digest()


class Reject(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Reject(reason)


def digest(b):
    return hashlib.sha256(b).digest()


def bounds(off, size, limit, why):
    need(0 <= off <= limit and 0 <= size <= limit-off, why)


def build():
    """Deterministic reconstruction of the pinned golden."""
    b = bytearray(600)
    b[:32] = PREFIX.pack(b"DCTM", 1, 0, 32, 5, len(b), 32)
    for i, (kind, off, size, align) in enumerate([
        (1,192,128,8), (2,320,30,8), (3,352,128,8),
        (4,512,68,64), (5,584,16,8)
    ]):
        b[32+i*32:64+i*32] = ENTRY.pack(kind,1,off,size,align,0)
    w = struct.pack("<4f",1.,-2.,.5,0.) + bytes(48) + bytes([1,255,2,254])
    b[192:320] = digest(w) + CATALOG + META.pack(
        0x7fffffff,1,3,4,1,2,1,4,2,8,0,bytes(16))
    b[320:350] = struct.pack("<II",3,1) + b"\x01\x00a\x01\x00b\x02\x00ab" + struct.pack("<III",0,1,2)
    b[352:416] = TENSOR.pack(1,1,2,1,2,2,0,0,0,16,-1,0,0,0,0)
    b[416:480] = TENSOR.pack(2,2,2,1,2,2,0,0,64,4,0,1,0,2,0)
    b[512:580] = w
    b[584:600] = struct.pack("<fifi",.5,0,.25,0)
    return bytes(b)


def tokenizer(b, vocab):
    need(len(b) >= 8, "token-count")
    n, merges = struct.unpack_from("<II",b)
    need(n == vocab and merges <= 65536,"token-count")
    p, total = 8, 0
    tokens, seen = [], set()
    for _ in range(n):
        bounds(p,2,len(b),"token-length")
        size, = struct.unpack_from("<H",b,p)
        p += 2
        need(1 <= size <= 1024,"token-length")
        bounds(p,size,len(b),"token-length")
        value = b[p:p+size]
        p += size
        total += size
        need(total <= 8*1024*1024,"token-length")
        need(value not in seen,"token-duplicate")
        seen.add(value)
        tokens.append(value)
    need(merges*12 == len(b)-p,"merge-length")
    records = [struct.unpack_from("<III",b,p+12*i) for i in range(merges)]
    outputs = {out for _,_,out in records}
    available = set(range(n))-outputs
    pairs, emitted = set(), set()
    for left,right,out in records:
        need(left < out < n and right < out and left in available
             and right in available and out not in emitted,"merge-order")
        need((left,right) not in pairs and tokens[left]+tokens[right] == tokens[out],"merge-value")
        available.add(out)
        emitted.add(out)
        pairs.add((left,right))


def validate(b):
    need(32 <= len(b) <= MAX_FILE,"file-length")
    magic,major,minor,header,count,length,table = PREFIX.unpack_from(b)
    need(magic == b"DCTM","magic")
    need((major,minor) == (1,0),"version")
    need(header == table == 32,"header")
    need(4 <= count <= 5,"section-count")
    need(length == len(b),"file-length")
    bounds(table,count*ENTRY.size,length,"table-bounds")
    prev, prior_kind = table+count*ENTRY.size, 0
    sections = {}
    for i in range(count):
        kind,flags,off,size,align,reserved = ENTRY.unpack_from(b,table+i*ENTRY.size)
        need(kind in {1,2,3,4,5},"section-type")
        need(kind > prior_kind,"section-order")
        need(flags == 1 and reserved == 0,"section-flags")
        need(size > 0,"section-bounds")
        bounds(off,size,length,"section-bounds")
        need(align == (64 if kind == 4 else 8) and off % align == 0,"section-align")
        need(off >= prev,"section-overlap")
        need(not any(b[prev:off]),"section-padding")
        sections[kind] = b[off:off+size]
        prev, prior_kind = off+size, kind
    need(prev == length and set(sections) in ({1,2,3,4},{1,2,3,4,5}),"section-set")
    meta,tok,directory,weights = [sections[x] for x in (1,2,3,4)]
    need(len(meta) == 128,"metadata-length")
    need(meta[:32] == digest(weights),"weights-hash")
    need(meta[32:64] == CATALOG,"catalog-hash")
    arch,tk,vocab,ctx,layers,width,heads,ff,count,params,flags,reserved = META.unpack_from(meta,64)
    need(arch == 0x7fffffff,"architecture")
    need(tk == 1,"tokenizer-kind")
    need(1 <= vocab <= 65536 and 1 <= ctx <= 512 and 1 <= layers <= 32 and
         1 <= width <= 2048 and 1 <= heads <= 32 and width%heads == 0 and
         1 <= ff <= 8192 and 1 <= count <= 4096 and 1 <= params <= MAX_PARAMS,"metadata-bounds")
    need(flags == 0 and reserved == bytes(16),"metadata-flags")
    tokenizer(tok,vocab)
    need(len(directory) == count*TENSOR.size,"tensor-directory")
    prev,qprev,prior_id,total = 0,0,0,0
    observed = []
    quant = sections.get(5,b"")
    for i in range(count):
        tid,dtype,rank,layout,*rest = TENSOR.unpack_from(directory,i*TENSOR.size)
        dims = rest[:4]
        off,size,axis,group,qoff,qcount,reserved = rest[4:]
        need(tid > prior_id,"tensor-id")
        need(dtype in {1,2},"dtype")
        need(1 <= rank <= 4 and layout == 1 and reserved == 0 and
             all(1 <= d <= 16384 for d in dims[:rank]) and not any(dims[rank:]),"tensor-shape")
        product = 1
        for dim in dims[:rank]:
            need(product <= MAX_PARAMS//dim,"tensor-shape")
            product *= dim
        need(total <= MAX_PARAMS-product,"tensor-shape")
        total += product
        need(size == product*(4 if dtype == 1 else 1),"tensor-length")
        bounds(off,size,len(weights),"tensor-bounds")
        need(off%64 == 0,"tensor-align")
        need(off >= prev,"tensor-overlap")
        need(not any(weights[prev:off]),"tensor-padding")
        if dtype == 1:
            need((axis,group,qoff,qcount) == (-1,0,0,0),"quant-layout")
            need(all(math.isfinite(v[0]) for v in struct.iter_unpack("<f",weights[off:off+size])),"float-value")
        else:
            need(axis == 0 and group == 1 and qcount == dims[0] and
                 qoff == qprev and qoff%8 == 0,"quant-layout")
            bounds(qoff,qcount*8,len(quant),"quant-bounds")
            for scale,zero in struct.iter_unpack("<fi",quant[qoff:qoff+qcount*8]):
                need(math.isfinite(scale) and scale > 0 and zero == 0,"quant-value")
            qprev += qcount*8
        prev,prior_id = off+size,tid
        observed.append((tid,dtype,dims[:rank]))
    need(prev == len(weights) and qprev == len(quant) and
         (5 in sections) == any(t[1] == 2 for t in observed),"tensor-coverage")
    need(total == params,"parameter-count")
    need((vocab,ctx,layers,width,heads,ff) == (3,4,1,2,1,4) and
         observed == [(1,1,[2,2]),(2,2,[2,2])],"profile-shape")
    return {"length":len(b),"sha256":digest(b).hex(),
            "weights_sha256":digest(weights).hex(),"catalog_sha256":CATALOG.hex(),
            "tokenizer_sha256":digest(tok).hex(),"tensor_ids":[t[0] for t in observed],"params":total}


def main():
    here = Path(__file__).resolve().parent/"fixtures"
    vectors = json.loads((here/"dctm-v1.json").read_text(encoding="utf-8"))
    b = bytes.fromhex(vectors["pack_hex"])
    manifest = json.loads((here/"unsigned-dev-manifest.json").read_text(encoding="utf-8"))
    def check_manifest():
        info = validate(b)
        need(manifest["role"] == "synthetic-test-only" and manifest["signature"] is None
             and manifest["pack"] == {"sha256":info["sha256"],"length":info["length"]}
             and manifest["catalog_sha256"] == info["catalog_sha256"]
             and manifest["tokenizer_sha256"] == info["tokenizer_sha256"],"manifest-binding")
    tests = [("golden","ok",lambda:need(validate(b) == vectors["expected"],"golden")),
             ("regenerate","ok",lambda:need(build() == b,"regenerate")),
             ("dev-manifest-binding","ok",check_manifest)]
    for m in vectors["mutations"]:
        def mutate(m=m):
            x = bytearray(b)
            off,payload = m["offset"],bytes.fromhex(m["hex"])
            bounds(off,len(payload),len(x),"mutation")
            x[off:off+len(payload)] = payload
            if m["rehash_weights"]:
                x[192:224] = digest(x[512:580])
            validate(bytes(x))
        tests.append((m["id"],m["expected"],mutate))
    tests += [("truncated","file-length",lambda:validate(b[:-1])),
              ("trailing","file-length",lambda:validate(b+b"\0"))]
    need(len({t[0] for t in tests}) == len(tests),"duplicate-case")
    bad = 0
    for name,expected,fn in tests:
        actual = "ok"
        try:
            fn()
        except Reject as exc:
            actual = str(exc)
        bad += actual != expected
        print(f"{'PASS' if actual == expected else 'FAIL'} {name}: {actual} expected {expected}")
    print(f"A6 synthetic bytes: {len(tests)-bad}/{len(tests)}; F4 signature/loader/parity NOT RUN")
    return bool(bad)


if __name__ == "__main__":
    raise SystemExit(main())
