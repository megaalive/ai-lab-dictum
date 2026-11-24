"""Compile a pinned synthetic F0-C catalog and grammar, not release trust."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fixture_path = ROOT / "spec/pipeline/f0-c-fixture-v1.json"
raw = fixture_path.read_bytes()
f = json.loads(raw)
def need(ok, why):
    if not ok:
        raise ValueError(why)
def pin(path, expected):
    data = (ROOT / path).read_bytes()
    actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    need(actual == expected, f"Fixture source pin mismatch: {path}")
    return data
paths = ["catalog/core/intents-v1.json", "catalog/debian-13/v1.json",
         "tests/spikes/s2/development-v1.json"]
catalog, profile, s2 = [pin(path, f["source_git_blobs"][path]) for path in paths]
registry = {x["id"]: x for x in json.loads(catalog)["intents"] if x["skeleton"]}
p = json.loads(profile)
bindings = {x["intent"]: x for x in p["bindings"]}
ids = list(f["patterns"])
need(len(ids) == len(registry) == 8 and set(ids) == set(registry), "Skeleton coverage")
need(p["trust_status"] == "NOT VERIFIED", "Profile must remain unverified")
need(all(bindings[i]["capability_status"] == "BLOCKED" and
         bindings[i]["compatibility"] == "NOT VERIFIED" for i in ids), "No opened capability")
need(f["mode"] == "F0-C-SYNTHETIC-NONEXECUTABLE", "Fixture trust only")
recipes = {x["intent"]: x for x in f["recipes"]}
need(len(f["recipes"]) == len(recipes) == 8 and set(recipes) == set(ids), "Recipe coverage")
def c(s):
    need(isinstance(s,str) and s.isascii() and "\0" not in s, "ASCII catalog strings only")
    return '"' + "".join("\\%03o" % ord(ch) for ch in s) + '"'
slots = ["port","protocol","unit","window","limit","root","depth","extension","filename"]
kinds = {"port":"K_INTEGER","protocol":"K_PROTOCOL","unit-name":"K_LITERAL",
         "time-window":"K_TIME","positive-int":"K_INTEGER","path":"K_LITERAL",
         "depth":"K_INTEGER","extension":"K_LITERAL","filename":"K_LITERAL"}
slot = {s: "S_" + s.upper() for s in slots}
lines = ["/* Generated from pinned source, not executable authority. */",
         "#define FIXTURE_CATALOG_SHA " + c(hashlib.sha256(catalog).hexdigest()),
         "#define FIXTURE_PROFILE_SHA " + c(hashlib.sha256(profile).hexdigest()),
         "#define FIXTURE_POLICY_SHA " + c(hashlib.sha256(raw).hexdigest()),
         "static const struct intent_rule rules[] = {"]
for i in ids:
    reg = registry[i]
    recipe = recipes[i]
    need(reg["proposal_eligible"] and reg["effect"]["class"] in {"READ","CHANGE"}, "effect")
    need(recipe == {"intent":i,"handler":"proposal."+i,"mode":"structured-proposal",
                    "copyable":False,"execution_allowed":False}, "nonexecutable recipe only")
    effect = json.dumps(reg["effect"],separators=(",",":"),sort_keys=True)
    lines.append("    {" + ",".join([c(i),c(recipe["handler"]),c(reg["effect"]["class"]),c(effect),
                                    c(reg["description"]["id"]),c(reg["description"]["en"])]) + ", {")
    for s in reg["slots"]:
        default = s["default"]
        v = default["value"] if default else None
        string = c(v) if isinstance(v,str) else "NULL"
        n = v if type(v) is int else 0
        lines.append("        {" + ",".join([slot[s["name"]],kinds[s["kind"]],c(s["kind"]),
            "true" if s["required"] else "false","true" if default else "false",
            str(s["minimum"] or 0),str(s["maximum"] or 0),str(n),string]) + "},")
    lines.append("    }, " + str(len(reg["slots"])) + "u},")
lines.append("};")
lines.append("static const struct grammar grammar[] = {")
seen = set()
for i, patterns in f["patterns"].items():
    allowed = {s["name"] for s in registry[i]["slots"]}
    for pattern in patterns:
        need(pattern not in seen, "duplicate grammar")
        seen.add(pattern)
        for token in pattern.split(" "):
            need(token.isascii() and token, "grammar token")
            if token.startswith("{"):
                name = token[1:-1]
                need((name in allowed or name == "minutes" and "window" in allowed), "unknown slot")
        lines.append(f"    {{{ids.index(i)}u,{c(pattern)}}},")
lines.append("};")
for name, items in list(f["scope"].items()) + [("deny_tokens",f["deny_tokens"])]:
    need(len(items)==len(set(items)), "duplicate allow/deny value")
    lines.append(f"static const char *const {name}[] = {{" + ",".join(c(x) for x in items) + "};")
lines.append("static const struct reference references[] = {")
refs = json.loads(s2)["reference"]
need(len(refs) == 32 and len({x["id"] for x in refs}) == 32, "S2 refs")
for x in refs:
    lines.append(f"    {{{ids.index(x['intent'])}u,{c(x['text'])}}},")
lines.append("};")
Path(sys.argv[1]).write_text("\n".join(lines)+"\n",encoding="ascii")
