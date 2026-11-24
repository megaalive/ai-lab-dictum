"""Locked v2 functional suite; predecessor suites remain immutable."""
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("prior_oracle", HERE/"run.py")
oracle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
raw=(HERE/"f1-v2-functional.json").read_bytes()
manifest=json.loads(raw)
labels=(HERE/"f1-v2-raw-gold.json").read_bytes()
gold=json.loads(labels)["cases"]
cases=manifest["cases"]
prior=oracle.cases+json.loads((HERE/"f1-functional-v1.json").read_bytes())["cases"]
assert len(cases)==len({r["id"] for r in cases})==len({oracle.data(r) for r in cases})==202
assert not {oracle.data(r) for r in cases}&{oracle.data(r) for r in prior}
assert manifest["reference_unix_s"]==oracle.reference
counts=Counter(r["suite"] for r in cases)
assert counts=={"supported":102,"ambiguity":24,"ood":14,"security":62}
new=set(oracle.registry)-set(oracle.prior["patterns"])
assert len(new)==15
for i in new:
    rows=[r for r in cases if r["suite"]=="supported" and r["expected"]["intent"]==i and not r["id"].startswith("V2-C-")]
    assert len(rows)==6 and Counter(r["language"] for r in rows)=={"id":3,"en":3}
assert len([r for r in cases if r["id"].startswith("V2-C-")])==12
assert set(gold)=={r["id"] for r in cases if r["suite"]=="supported"}
print("V2_FUNCTIONAL_CORPUS",hashlib.sha256(raw).hexdigest(),"raw gold",
      hashlib.sha256(labels).hexdigest(),dict(counts),manifest["provenance"])
oracle.cases=cases
oracle.raw_gold=gold
b0=oracle.run("B0","V2_PIPELINE_METRICS")
b1=oracle.run("B1","V2_PIPELINE_METRICS")
assert not b0,"V2 B0 functional regression"
oracle.cli_checks()
assert not oracle.retrievals
