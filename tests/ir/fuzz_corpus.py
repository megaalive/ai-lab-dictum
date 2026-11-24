"""Materialize synthetic seeds only; never source data from the operating host."""
import json
import sys
from pathlib import Path
from run import fixture, sample_bytes, edit
from v2_vectors import chains as v2_chains

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
chains = {x["id"]: x for x in fixture("chains")["chains"]}
payloads = [sample_bytes(x) for x in fixture("raw")]
payloads += [json.dumps(v).encode() for x in chains.values() for v in x["objects"].values()]
payloads += [json.dumps(edit(chains[x["base"]]["objects"][x["stage"]], x["edits"])).encode()
             for x in fixture("schema")]
payloads += [json.dumps(v,ensure_ascii=False).encode() for c in v2_chains() for v in c.values()]
for i, data in enumerate(sorted(set(payloads))):
    (out / f"seed-{i:03}").write_bytes(data)
print("synthetic corpus unique", len(set(payloads)))
