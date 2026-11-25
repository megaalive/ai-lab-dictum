"""Additional locked SELF functional vectors; F0 and S2 suites remain separate."""
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("f0_oracle", HERE/"run.py")
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
raw = (HERE/"f1-functional-v1.json").read_bytes()
manifest = json.loads(raw)
raw_labels = (HERE/"f1-raw-gold-v1.json").read_bytes()
gold = json.loads(raw_labels)["cases"]
cases = manifest["cases"]
assert len(cases) == len({r["id"] for r in cases}) == len({oracle.data(r) for r in cases}) == 232
assert not {oracle.data(r) for r in cases} & {oracle.data(r) for r in oracle.cases}
assert manifest["reference_unix_s"] == oracle.reference
counts=Counter(r["suite"] for r in cases)
assert counts == {"supported":150,"ambiguity":18,"ood":19,"security":45}
extra = set(oracle.prior["patterns"])-set(oracle.skeleton)
assert len(extra)==25
for i in extra:
    rows=[r for r in cases if r["suite"]=="supported" and r["expected"]["intent"]==i]
    assert len(rows)==6 and Counter(r["language"] for r in rows)=={"id":3,"en":3}
assert set(gold)=={r["id"] for r in cases if r["suite"]=="supported"}
print("F1_FUNCTIONAL_CORPUS", hashlib.sha256(raw).hexdigest(),
      "raw gold", hashlib.sha256(raw_labels).hexdigest(), dict(counts), manifest["provenance"])
oracle.cases=cases
oracle.raw_gold=gold
b0=oracle.run("B0","F1_PIPELINE_METRICS")
b1=oracle.run("B1","F1_PIPELINE_METRICS")
# B1 remains diagnostic; no supported or negative case is removed.
assert not b0, "F1 B0 functional regression"
oracle.cli_checks()
assert not oracle.retrievals
