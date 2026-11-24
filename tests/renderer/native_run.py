"""Native fixture adapter vs fixed A4 gold; optionally isolated real shells."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/"tests/spikes/s1"))
# run.py at tests/renderer is also named run; import the S1 harness explicitly.
import importlib.util
spec=importlib.util.spec_from_file_location("s1_harness", ROOT/"tests/spikes/s1/run.py")
s1=importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1)

probe = str(Path(sys.argv[1]).resolve())
profile = sys.argv[2] if len(sys.argv)==3 else None
gold_raw = (HERE/"fixtures/preview-v1.json").read_bytes()
gold = json.loads(gold_raw)

def invoke(raw):
    p = subprocess.run([probe],input=raw,capture_output=True,timeout=5,
        env={"LC_ALL":"C.UTF-8","TZ":"UTC","PATH":"/usr/bin:/bin"} if profile else None,
        preexec_fn=s1.load_network_filter if profile else None)
    assert p.returncode==0 and not p.stderr and len(p.stdout)<=32768+64
    tag,_,value=p.stdout.partition(b"\n")
    if tag==b"COPYABLE":
        return {"kind":"COPYABLE","preview":value.decode("utf-8")}
    assert tag==b"NON_COPYABLE"
    return {"kind":"NON_COPYABLE","reason":value.decode("ascii")}

def payload(c):
    # The expected preview is never supplied to the adapter, but the closed
    # fixture envelope keeps the expected field. No oracle output leakage.
    return json.dumps({**c,"expected":{}},ensure_ascii=True,separators=(",",":")).encode()

def main():
    if profile:
        assert profile in s1.SHELL
        s1.preflight()
        s1.trace_guard_regression()
        initial=(s1.sha(s1.SHELL[profile][0]),s1.sha(s1.DUMPER),s1.sha(probe))
    accepted=rejected=edge=0
    with tempfile.TemporaryDirectory(prefix="dictum-c05-") as temp:
        cwd=Path(temp)/"empty"
        cwd.mkdir()
        trace=Path(temp)/"trace"
        for c in gold["cases"]:
            if profile and c["shell"] in s1.SHELL and c["shell"]!=profile:
                continue
            actual=invoke(payload(c))
            assert actual==c["expected"], (c["id"],actual["kind"],actual.get("reason"))
            if actual["kind"]=="COPYABLE":
                accepted+=1
                if profile:
                    want=[s1.DUMPER]+["--" if a["kind"]=="option-end" else str(a["value"])
                        for a in c["action"]["operation"]["argv"]]
                    s1.roundtrip(actual["preview"],want,profile,trace,cwd)
                    edge+=1
            else:
                assert set(actual)=={"kind","reason"} and "CANARY_SECRET" not in json.dumps(actual)
                rejected+=1
        for h in gold["invalid_utf8_hex"]:
            actual=invoke(bytes.fromhex(h))
            assert actual["kind"]=="NON_COPYABLE" and "preview" not in actual
            rejected+=1
    assert accepted==(8 if profile else 16)
    if profile:
        assert edge==8 and initial==(s1.sha(s1.SHELL[profile][0]),s1.sha(s1.DUMPER),s1.sha(probe))
    else:
        assert accepted+rejected==gold["expected_count"]
    print("C05_NATIVE_GOLD",profile or "data-only","gold_sha256="+hashlib.sha256(gold_raw).hexdigest(),
        "accepted",accepted,"rejected",rejected,"actual_shell_roundtrips",edge,
        "mismatches 0; inert fixture only")
    return 0

if __name__=="__main__":
    sys.exit(main())
