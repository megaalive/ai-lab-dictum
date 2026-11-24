"""Compile pinned synthetic F1 catalog/grammar; never release trust."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
fixture_path = ROOT / "spec/pipeline/f1-fixture-v2.json"
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
all_intents = json.loads(catalog)["intents"]
all_registry = {x["id"]: x for x in all_intents}
need(len(all_intents) == len(all_registry) == 48, "Canonical registry coverage")
need([x["ordinal"] for x in all_intents] == list(range(1, 49)), "Canonical ordinals")
skeleton = {x["id"]: x for x in all_intents if x["skeleton"]}
predecessor = json.loads(pin("spec/pipeline/f0-c-fixture-v1.json",
                             f["source_git_blobs"]["spec/pipeline/f0-c-fixture-v1.json"]))
domains = json.loads(pin("spec/catalog/f1-slot-domains-v1.json",
                        f["source_git_blobs"]["spec/catalog/f1-slot-domains-v1.json"]))
need(f["max_window_seconds"] == domains["max_window_seconds"] ==
     {"log.service.query": 86400, "log.system.errors": 86400, "file.search": 86400},
     "Window limits pinned")
need(all(f["patterns"].get(i) == predecessor["patterns"][i] for i in skeleton)
     and all(f["scope"].get(k)==v for k,v in predecessor["scope"].items())
     and f["deny_tokens"] == predecessor["deny_tokens"], "F0 contract preserved")
prior = json.loads(pin("spec/pipeline/f1-fixture-v1.json",
                       f["source_git_blobs"]["spec/pipeline/f1-fixture-v1.json"]))
need(all(f["patterns"].get(i)==p for i,p in prior["patterns"].items()) and
     all(f["scope"].get(k)==v for k,v in prior["scope"].items()) and
     f["additional_references"][:len(prior["additional_references"])]==prior["additional_references"],
     "F1 predecessor preserved")
overlay_raw=(ROOT/"spec/catalog/f1-runtime-catalog-v2.json").read_bytes()
overlay=json.loads(overlay_raw)
need(overlay=={"schema_version":2,"mode":"synthetic-proposal-only",
     "source_git_blobs":{"catalog/core/intents-v1.json":f["source_git_blobs"]["catalog/core/intents-v1.json"],
         "spec/catalog/f1-slot-domains-v1.json":f["source_git_blobs"]["spec/catalog/f1-slot-domains-v1.json"],
         "catalog/debian-13/v1.json":f["source_git_blobs"]["catalog/debian-13/v1.json"]},
     "deferred_slots":domains["deferred"],"additional_slots":domains["additional"],
     "narrative_only":domains["narrative_only"],"execution_allowed":False,"compatibility":"NOT VERIFIED"},
     "Exact runtime catalog overlay")
implemented=set(f["patterns"])
need(len(implemented)==48 and implemented==set(all_registry),"All canonical IDs")
registry={i:{**x,"slots":list(x["slots"])} for i,x in all_registry.items()}
for row in overlay["deferred_slots"]+overlay["additional_slots"]:
    spec={"name":row["slot"],"kind":row["kind"],"required":row["required"],
          "default":row["default"],"minimum":None,"maximum":None}
    need(spec["name"] not in {s["name"] for s in registry[row["intent"]]["slots"]},"Duplicate slot")
    registry[row["intent"]]["slots"].append(spec)
need({(x["intent"],x["slot"],x["required"]) for x in overlay["deferred_slots"]}==
     {(i,s["name"],s["required"]) for i,x in all_registry.items() for s in x["deferred_slots"]},
     "All deferred slots")
narrative=set(overlay["narrative_only"])
need(narrative=={i for i,x in registry.items() if x["operation_surface"]=="narrative-only"}==
     set(f["narratives"]) and len(narrative)==5,"Narrative surface")
need(set(f["scope"]["archives"])<=set(f["scope"]["files"]), "Synthetic archive scope")
need(not (set(f["scope"]["extract_destinations"]+f["scope"]["compress_destinations"]) &
          set(f["scope"]["files"]+f["scope"]["roots"]+f["scope"]["compress_sources"])),
     "Synthetic new destination identity only")
p = json.loads(profile)
bindings = {x["intent"]: x for x in p["bindings"]}
ids = list(f["patterns"])
need(len(skeleton)==8 and len(ids)==len(registry)==48 and set(ids)==set(registry), "Typed coverage")
need(p["trust_status"] == "NOT VERIFIED", "Profile must remain unverified")
need(len(p["bindings"]) == len(bindings) == 48 and set(bindings) == set(all_registry),
     "Complete profile registry bijection")
need(all(bindings[i]["capability_status"] == "BLOCKED" and
         bindings[i]["compatibility"] == "NOT VERIFIED" and
         bindings[i]["version_status"] == "NOT VERIFIED" for i in all_registry),
     "No opened capability")
need(all(not x["execute_eligible"] and not x["source"]["external_content_imported"]
         for x in all_intents), "Metadata must not imply execute authority or external import")
need(f["mode"] == "F1-V2-SYNTHETIC-NONEXECUTABLE" and f["schema_version"]==2, "Fixture trust only")
recipes = {x["intent"]: x for x in f["recipes"]}
need(len(f["recipes"]) == len(recipes) == 48 and set(recipes) == set(ids), "Recipe coverage")
def c(s):
    need(isinstance(s,str) and "\0" not in s, "Scalar fixture strings only")
    return '"' + "".join("\\%03o" % b for b in s.encode("utf-8", "strict")) + '"'
slots = ["port","protocol","unit","window","limit","root","depth","extension","filename","path",
         "utility","option","domain","target","text","direction","name","package","query",
         "record_type","count","archive","source","destination"]
kinds = {"port":"K_INTEGER","protocol":"K_PROTOCOL","unit-name":"K_LITERAL",
         "time-window":"K_TIME","positive-int":"K_INTEGER","path":"K_LITERAL",
         "depth":"K_INTEGER","extension":"K_LITERAL","filename":"K_LITERAL"}
kinds.update({k:"K_DOMAIN" for k in domains["scope"]})
slot = {s: "S_" + s.upper() for s in slots}
lines = ["/* Generated from pinned source, not executable authority. */",
         "#define FIXTURE_CATALOG_SHA " + c(hashlib.sha256(overlay_raw).hexdigest()),
         "#define FIXTURE_REGISTRY_SHA " + c(hashlib.sha256(catalog).hexdigest()),
         "#define FIXTURE_PROFILE_SHA " + c(hashlib.sha256(profile).hexdigest()),
         "#define FIXTURE_POLICY_SHA " + c(hashlib.sha256(raw).hexdigest()),
         "#define FIXTURE_MAX_WINDOW_SECONDS INT64_C(86400)",
         "static const struct intent_rule rules[] = {"]
for i in ids:
    reg = registry[i]
    recipe = recipes[i]
    need(reg["proposal_eligible"] and reg["effect"]["class"] in {"INFO","READ","CHANGE"}, "effect")
    expected={"intent":i,"mode":"narrative-guidance" if i in narrative else "structured-proposal",
              "copyable":False,"execution_allowed":False}
    if i not in narrative:
        expected["handler"]="proposal."+i
    need(recipe==expected,"Nonexecutable recipe only")
    effect = json.dumps(reg["effect"],separators=(",",":"),sort_keys=True)
    lines.append("    {" + ",".join([c(i),c(recipe["handler"]) if i not in narrative else "NULL",c(reg["effect"]["class"]),c(effect),
                                    c(reg["description"]["id"]),c(reg["description"]["en"]),
                                    c(f["narratives"][i]) if i in narrative else "NULL"]) + ", {")
    if not reg["slots"]:
        lines.append("        {0},")
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

refs = json.loads(s2)["reference"]
need(len(refs) == 32 and len({x["id"] for x in refs}) == 32, "S2 refs")
extra = f["additional_references"]
need(len(extra)==80 and len({x["id"] for x in refs+extra})==112 and
     {x["intent"] for x in extra}==implemented-set(skeleton) and
     all(sum(x["intent"]==i for x in extra)==2 for i in implemented-set(skeleton)),
     "Authored reference coverage")
refs = refs + extra
# Inverse intent-document-frequency lexical index. Only independent authored
# reference text and original catalog descriptions; no dev label/output access.
stop={"show","list","display","the","of","for","to","in","on","a","an","and","or","by",
      "please","could","can","you","what","is","how","with","last","local","propose","plan",
      "tampilkan","lihat","daftar","yang","di","dari","ke","dan","atau","untuk","tolong","mohon",
      "usulkan","rencana","usulan","limit","depth","count","batas","kedalaman","jumlah","protocol"}
term_masks={}
for i in ids:
    texts=[x["text"] for x in refs if x["intent"]==i]+list(registry[i]["description"].values())
    for term in {w.lower() for text in texts for w in re.findall(r"[A-Za-z][A-Za-z0-9-]*",text)}-stop:
        term_masks[term]=term_masks.get(term,0)|(1<<ids.index(i))
lines.append("static const struct lexical_term lexical_terms[] = {")
for term,mask in sorted(term_masks.items()):
    lines.append("    {"+c(term)+",UINT64_C("+str(mask)+"),"+str(1+256//mask.bit_count())+"u},")
lines.append("};")
lines.append("static const struct domain_pair domain_values[] = {")
for kind,values in sorted(domains["scope"].items()):
    need(len(values)==len(set(values)) and bool(values),"Domain scope")
    for value in values:
        lines.append("    {"+c(kind)+","+c(value)+"},")
lines.append("};")
need(set(f["help_index"])==set(domains["utility_options"]),"Utility index coverage")
lines.append("static const struct help_entry help_entries[] = {")
for utility,row in f["help_index"].items():
    need(set(row["options"])==set(domains["utility_options"][utility]),"Utility option pairing")
    lines.append("    {"+c(utility)+",NULL,"+c(row["summary"])+"},")
    for option,description in row["options"].items():
        lines.append("    {"+c(utility)+","+c(option)+","+c(row["summary"]+" "+description)+"},")
lines.append("};")
# Static metadata remains separate from all synthetic runtime rules.
# Do not feed this table to NLU, resolver, plan compiler or renderer.
lines.append("static const struct catalog_entry catalog_entries[] = {")
for x in all_intents:
    i = x["id"]
    binding = bindings[i]
    row = {"intent": i, "id": x["description"]["id"], "en": x["description"]["en"],
           "ordinal": x["ordinal"], "effect": x["effect"]["class"],
           "catalogued": True, "catalog_proposal_eligible": x["proposal_eligible"],
           "pipeline_status": "SYNTHETIC_PROPOSAL" if i in registry else "NOT_IMPLEMENTED",
           "typed_slot_count": len(x["slots"]), "deferred_slot_count": len(x["deferred_slots"]),
           "runtime_typed_slot_count":len(registry[i]["slots"]),
           "runtime_representation":"narrative-guidance" if i in narrative else "structured-proposal",
           "capability_status": binding["capability_status"],
           "compatibility": binding["compatibility"], "version_status": binding["version_status"],
           "source": "pinned original catalog metadata; not observed OS data",
           "copyable": False, "execution_allowed": False, "observed_os_data": False}
    encoded = json.dumps(row, ensure_ascii=True, separators=(",", ":"))
    need(len(encoded) < 8192, "Metadata frame limit")
    lines.append("    {" + c(i) + "," + c(encoded) + "},")
lines.append("};")
Path(sys.argv[1]).write_text("\n".join(lines)+"\n",encoding="ascii")
