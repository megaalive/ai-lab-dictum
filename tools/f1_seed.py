"""Prepare a private F1 seed candidate, never train or attest human identity.

Inputs must be explicitly supplied outside the repository. External rights
and human review are prerequisites, not created by this code. No blind
corpus accepted. Outputs contain opaque IDs/hashes/counts, never raw text.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from jsonschema import Draft202012Validator

from f1_corpus import ROOT, Reject, need, sha, encoded, normalize, similar, group_partition, pinned
from f1_slot_domains import load as load_domains, validate_value as domain_validate, Reject as DomainReject

MAX_PACKET=8*1024*1024
REFERENCE=1760000600
PINS={
    "catalog/core/intents-v1.json":"110368054b8d9f1ffa89a18dc23f4927769a32e4",
    "spec/catalog/f1-runtime-catalog-v2.json":"10d14139224850c5bd0f952f48efcb93da312d4c",
    "spec/pipeline/f1-fixture-v2.json":"b64ac0ad6f91b78aba03a20a0c5e0e7298c65eed",
    "catalog/debian-13/v1.json":"2cc5431daaf3da0dcaaa7fdcacefdb7b04a8cae9",
    "spec/ir/resolved-ir-v2.schema.json":"4881ee1a332a2bc13aac0ee9c8c08be2e58cfe69",
    "spec/ir/policy-decision-v2.schema.json":"12d0eafe95d79a6a5ab0ada8a0725772dd72caf9",
}
RECORD_KEYS={"id","role","revision","text","text_sha256","normalized_sha256","language",
 "dominant_language","semantic_group","family","parent","source_id","source_version",
 "author","review","fixture_id","expected","slot_sources","tags","derivation"}
RIGHTS_KEYS={"schema_version","role","seed_sha256","owner_decision_ref","sources",
 "allow_development_fit","allow_development_evaluation","allow_distribution","blind"}
ID=r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}"
SHA=r"[0-9a-f]{64}"
SUITES={"supported","ambiguity","ood","security"}


def match(value,pattern):
    return type(value) is str and re.fullmatch(pattern,value) is not None


def keys(obj,expected,code):
    need(type(obj) is dict and set(obj)==expected,code)


def exact_text(s):
    need(type(s) is str and "\x00" not in s,"text")
    raw=s.encode("utf-8","strict")
    need(0<len(raw)<=4096 and all(not (0xfdd0<=ord(c)<=0xfdef or ord(c)&0xffff in (0xfffe,0xffff))
                                  for c in s),"text")
    return raw


def parse(data):
    need(len(data)<=MAX_PACKET and not data.startswith(b"\xef\xbb\xbf"),"packet-size")
    def closed(pairs):
        obj={}
        for k,v in pairs:
            need(k not in obj,"duplicate-json")
            obj[k]=v
        return obj
    def reject(_):
        raise Reject("number")
    return json.loads(data.decode("utf-8","strict"),object_pairs_hook=closed,
                      parse_float=reject,parse_constant=reject)


def blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()


def load_contract():
    raw={}
    for p,pin in PINS.items():
        raw[p]=(ROOT/p).read_bytes()
        need(pin is not None and blob(raw[p])==pin,"contract-pin")
    reg=json.loads(raw["catalog/core/intents-v1.json"])["intents"]
    need(len(reg)==48 and [x["ordinal"] for x in reg]==list(range(1,49)),"registry")
    catalog={x["id"]:{**x,"slots":{s["name"]:s for s in x["slots"]}} for x in reg}
    overlay=json.loads(raw["spec/catalog/f1-runtime-catalog-v2.json"])
    for x in overlay["deferred_slots"]+overlay["additional_slots"]:
        catalog[x["intent"]]["slots"][x["slot"]]={"name":x["slot"],"kind":x["kind"],
          "required":x["required"],"default":x["default"],"minimum":None,"maximum":None}
    fixture=json.loads(raw["spec/pipeline/f1-fixture-v2.json"])
    schema=json.loads(raw["spec/ir/resolved-ir-v2.schema.json"])
    validator=Draft202012Validator({"$ref":"#/$defs/slot_value","$defs":schema["$defs"]})
    domain,domain_schema=load_domains()
    policy=json.loads(raw["spec/ir/policy-decision-v2.schema.json"])
    return {"catalog":catalog,"scope":fixture["scope"],"domains":domain,
            "domain_schema":domain_schema,"validator":validator,
            "reasons":set(policy["properties"]["reason"]["enum"]),
            "narratives":set(overlay["narrative_only"]),
            "identities":{p:sha(b) for p,b in raw.items()}}


def read_regression_texts():
    """Read only visible repository development fixtures for contamination check.
    They are never included in the output seed or used to fit."""
    seen=set()
    for name in ("functional-v1.json","f1-functional-v1.json","f1-v2-functional.json"):
        for r in json.loads(pinned("tests/pipeline/"+name))["cases"]:
            if "text" in r:
                seen.add(normalize(r["text"]))
    s2=json.loads(pinned("tests/spikes/s2/development-v1.json"))
    for r in s2["reference"]+s2["development"]:
        seen.add(normalize(r["text"]))
    for r in json.loads((ROOT/"spec/pipeline/f1-fixture-v2.json").read_bytes())["additional_references"]:
        seen.add(normalize(r["text"]))
    return seen


def rights_check(rights,seed_sha,mechanical):
    keys(rights,RIGHTS_KEYS,"rights-shape")
    need(type(rights["schema_version"]) is int and rights["schema_version"]==1,"rights-version")
    need(rights["role"]==("MECHANICAL-TEST" if mechanical else "OWNER-APPROVED-DEVELOPMENT-SOURCES"),
         "rights-role")
    need(rights["seed_sha256"]==seed_sha and match(rights["owner_decision_ref"],ID),"rights-pin")
    need(rights["allow_development_fit"] is (not mechanical) and
         rights["allow_development_evaluation"] is (not mechanical) and
         rights["allow_distribution"] is False and rights["blind"] is False,"rights-scope")
    sources={}
    need(type(rights["sources"]) is list and 1<=len(rights["sources"])<=500,"sources")
    for x in rights["sources"]:
        keys(x,{"id","version","record_set_sha256","origin","rights_decision_ref","attribution"},"source-shape")
        need(match(x["id"],ID) and match(x["version"],ID) and x["id"] not in sources and
             match(x["record_set_sha256"],SHA) and match(x["rights_decision_ref"],ID) and
             match(x["attribution"],ID),"source-identity")
        need(x["origin"]==("MECHANICAL-TEST" if mechanical else "ORIGINAL-HUMAN-CONTRIBUTION"),
             "source-origin")
        sources[x["id"]]=x
    return sources


def source_digest(rows):
    return sha(encoded(sorted((x["id"],sha(encoded(x))) for x in rows)))


def span(raw,ref):
    keys(ref,{"start","end"},"span-shape")
    a,b=ref["start"],ref["end"]
    need(type(a) is int and type(b) is int and 0<=a<b<=len(raw),"span-bound")
    return raw[a:b].decode("utf-8","strict")


def check_slots(row,raw,catalog,contract):
    e=row["expected"]
    slots=e["slots"]
    sources=row["slot_sources"]
    spec=catalog["slots"]
    need(type(slots) is dict and type(sources) is dict and slots.keys()==sources.keys() and
         slots.keys()<=spec.keys(),"slot-keys")
    for name,s in spec.items():
        need(not s["required"] or name in slots,"required-slot")
    explicit={}
    spans=[]
    for name,v in slots.items():
        s=spec[name]
        need(contract["validator"].is_valid(v) and v["kind"]==s["kind"],"typed-value")
        if s["minimum"] is not None:
            need(s["minimum"]<=v["value"]<=s["maximum"],"range")
        if v["kind"] in contract["domains"]["scope"]:
            try:
                domain_validate(v,contract["domains"],contract["domain_schema"])
            except DomainReject:
                raise Reject("domain") from None
        key={"root":"roots","unit":"units","extension":"extensions","filename":"filenames",
             "path":"files","archive":"archives","source":"compress_sources",
             "destination":"extract_destinations" if e["intent"]=="archive.extract.safe" else "compress_destinations"}.get(name)
        if key:
            need(v["value"] in contract["scope"][key],"fixture-scope")
        src=sources[name]
        need(type(src) is dict and src.get("kind") in {"input-span","context-ref","catalog-default"},"provenance")
        if src["kind"]=="catalog-default":
            keys(src,{"kind"},"default-shape")
            need(s["default"] is not None and s["default"]==v,"default")
            continue
        keys(src,{"kind","span"},"provenance-shape")
        value=span(raw,src["span"])
        a,b=src["span"]["start"],src["span"]["end"]
        spans.append((a,b))
        if v["kind"]=="time-window":
            need(src["kind"]=="context-ref" and re.fullmatch(r"[0-9]{1,16}",value)
                 and 1<=int(value)<=1440 and
                 re.match(rb" (?:minutes|menit)(?: |[?]?$)",raw[b:],re.I) is not None and
                 v["start_unix_s"]==REFERENCE-int(value)*60 and v["end_unix_s"]==REFERENCE,
                 "window-provenance")
            explicit[name]={"kind":"context-ref","value":v}
        else:
            need(src["kind"]=="input-span","literal-provenance")
            if type(v["value"]) is int:
                need(re.fullmatch(r"[0-9]{1,16}",value) and int(value)==v["value"],"number-span")
            else:
                need(value==v["value"],"literal-span")
            explicit[name]=src
    spans.sort()
    need(all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),"overlap")
    for constraint in catalog["slot_constraints"]:
        candidates=explicit if constraint["kind"]=="at-least-one-explicit" else slots
        need(constraint["kind"] in {"at-least-one","at-least-one-explicit"}
             and bool(set(constraint["slots"])&candidates.keys()),"slot-constraint")
    intent=e["intent"]
    if intent=="help.command.explain" and "option" in slots:
        need(slots["option"]["value"] in contract["domains"]["utility_options"][slots["utility"]["value"]],"option-binding")
    if intent=="archive.contents.list":
        need(slots["path"]["value"] in contract["scope"]["archives"],"archive-source")
    if intent=="file.head_tail.view":
        need(slots["path"]["value"] not in contract["scope"]["archives"],"text-file")
    if intent in {"archive.extract.safe","file.compress.archive"}:
        a=slots["archive" if intent=="archive.extract.safe" else "source"]["value"]
        b=slots["destination"]["value"]
        need(a!=b and not b.startswith(a+"/"),"archive-destination")
    return explicit


def check_row(row,contract,sources,mechanical):
    keys(row,RECORD_KEYS,"record-shape")
    for k in ("id","semantic_group","family","source_id","source_version","author","fixture_id"):
        need(match(row[k],ID),"record-id")
    need(row["role"]==("MECHANICAL-TEST" if mechanical else "HUMAN-DEVELOPMENT-SEED") and
         type(row["revision"]) is int and row["revision"]>=1 and
         row["derivation"]==("MECHANICAL-TEST" if mechanical else "HUMAN-AUTHORED"),"record-role")
    need(row["parent"] is None or match(row["parent"],ID),"parent")
    need(row["source_id"] in sources and sources[row["source_id"]]["version"]==row["source_version"],"source-ref")
    raw=exact_text(row["text"])
    n=normalize(row["text"])
    need(bool(n) and row["text_sha256"]==sha(raw) and row["normalized_sha256"]==sha(n.encode()),"text-pin")
    need(row["language"] in {"id","en","mixed"} and
         (row["dominant_language"] in {"id","en"} if row["language"]=="mixed" else row["dominant_language"] is None),
         "language")
    review=row["review"]
    keys(review,{"reviewer","decision_ref","evidence_sha256","decision","sensitive_data","adjudicated"},"review")
    need(match(review["reviewer"],ID) and review["reviewer"]!=row["author"] and
         match(review["decision_ref"],ID) and match(review["evidence_sha256"],SHA) and
         review["decision"]=="ACCEPTED" and review["sensitive_data"] is False and
         review["adjudicated"] is True,"review")
    tags=row["tags"]
    need(type(tags) is list and len(tags)==len(set(tags)) and
         set(tags)<={"supported","ambiguity","ood","security","near-miss","NET","CHANGE","composition"} and
         len(set(tags)&SUITES)==1,"suite")
    suite=next(iter(set(tags)&SUITES))
    e=row["expected"]
    need(type(e) is dict and e.get("reason") in contract["reasons"],"expected-reason")
    decision=e.get("decision")
    common={"decision","reason","state","intent"}
    intent=e.get("intent")
    need(intent is None or intent in contract["catalog"],"intent")
    if suite=="supported":
        keys(e,common|{"slots"},"supported-shape")
        need(decision=="allow-proposal" and e["reason"]=="proposal-eligible" and e["state"]=="resolved" and
             intent is not None,"supported")
        c=contract["catalog"][intent]
        need(row["fixture_id"]==c["fixture_id"],"fixture")
        risk=set()
        if "network" in c["effect"]["axes"]:
            risk.add("NET")
        if c["effect"]["class"]=="CHANGE":
            risk.add("CHANGE")
        need(set(tags)&{"NET","CHANGE"}==risk,"effect-tags")
        raw_slots=check_slots(row,raw,c,contract)
    else:
        need(row["slot_sources"]=={},"negative-raw")
        raw_slots={}
        if suite=="ambiguity":
            keys(e,common|{"unresolved","alternatives"},"ambiguity-shape")
            need(decision=="clarify" and (e["state"],e["reason"]) in {("ambiguous","ambiguous"),("incomplete","missing-slot")} and
                 type(e["unresolved"]) is list and type(e["alternatives"]) is list,"ambiguity")
            need(len(e["alternatives"])==len(set(e["alternatives"]))<=2 and
                 all(i in contract["catalog"] for i in e["alternatives"]),"alternatives")
            names=set()
            for item in e["unresolved"]:
                keys(item,{"slot","problem"},"unresolved")
                need(intent is not None and item["slot"] in contract["catalog"][intent]["slots"] and
                     item["slot"] not in names and item["problem"] in {"missing","ambiguous"},"unresolved")
                names.add(item["slot"])
            need(bool(names or e["alternatives"]) and
                 (intent is not None or len(e["alternatives"])==2),"clarification-target")
        else:
            keys(e,common,"negative-shape")
            need((suite=="ood" and decision in {"unsupported","deny"}) or
                 (suite=="security" and decision=="deny"),"negative-outcome")
            need(e["state"]==("unsupported" if decision=="unsupported" else "invalid") and intent is None and
                 e["reason"] in ({"unsupported-intent"} if decision=="unsupported" else {"invalid-candidate"}),
                 "negative-state")
        need(row["fixture_id"]==(contract["catalog"][intent]["fixture_id"] if intent else "NO-INTENT"),"negative-fixture")
    # Derive semantic identity from canonical label+fixture, not author-claimed
    # grouping IDs; negative outcome alone is not a semantic scenario.
    semantic=sha(encoded({"fixture":row["fixture_id"],"expected":e})) if intent is not None else row["semantic_group"]
    return {"id":row["id"],"intent":intent or "@"+suite,"language":row["language"],"text":row["text"],
            "semantic_group":row["semantic_group"],"family":row["family"],"semantic_key":semantic,
            "parent":row["parent"]}, raw_slots, suite


def prepare(seed_bytes,rights_bytes,*,mechanical=False,regression=None):
    seed_sha=sha(seed_bytes)
    rights=parse(rights_bytes)
    sources=rights_check(rights,seed_sha,mechanical)
    seed=parse(seed_bytes)
    keys(seed,{"schema_version","role","records"},"seed-shape")
    need(type(seed["schema_version"]) is int and seed["schema_version"]==1 and
         seed["role"]==("MECHANICAL-TEST" if mechanical else "PRIVATE-HUMAN-DEVELOPMENT-SEED"),"seed-role")
    rows=seed["records"]
    need(type(rows) is list and (1 if mechanical else 200)<=len(rows)<=500,"seed-size")
    contract=load_contract()
    if regression is None:
        regression=read_regression_texts()
    by_id={}
    normal={}
    normalized_labels={}
    suites=Counter()
    supported=set()
    supported_ids=set()
    src_rows={i:[] for i in sources}
    for row in rows:
        g,_,suite=check_row(row,contract,sources,mechanical)
        i=g["id"]
        need(i not in by_id,"case-id")
        n=normalize(g["text"])
        # Reject exact or detected fuzzy matches to visible regression/S2.
        need(n not in regression and not any(similar(n,t) for t in regression),"regression-contamination")
        label=sha(encoded({"fixture":row["fixture_id"],"expected":row["expected"]}))
        need(normalized_labels.setdefault(n,label)==label,"duplicate-label-conflict")
        by_id[i]=g
        normal[i]=n
        suites[suite]+=1
        if suite=="supported":
            supported.add(g["intent"])
            supported_ids.add(i)
        src_rows[row["source_id"]].append(row)
    for i,items in src_rows.items():
        need(bool(items) and source_digest(items)==sources[i]["record_set_sha256"],"source-record-set")
    if not mechanical:
        need(supported==set(contract["catalog"]) and set(suites)==SUITES,"seed-coverage")
        need({r["language"] for r in rows}>={"id","en"},"language-coverage")
    out=group_partition(by_id,normal)
    out.pop("manifest_sha256")
    coverage={s:sorted({g["intent"] for i,g in by_id.items()
                        if out["rows"][i]["split"]==s and i in supported_ids})
              for s in ("train","dev","test")}
    deficits={s:sorted(supported-set(v)) for s,v in coverage.items()}
    out.update(role="MECHANICAL-TEST" if mechanical else "PRIVATE-SPLIT-CANDIDATE",
               seed_sha256=seed_sha,rights_sha256=sha(rights_bytes),contract=contract["identities"],
               algorithm="f1-group-v1",python_version=sys.version.split()[0],
               suites=dict(suites),supported_intents=len(supported),coverage=coverage,
               missing_supported_intents=deficits,
               record_sha256={r["id"]:sha(encoded(r)) for r in rows},
               human_review_evidence_status="SHAPE-ONLY-NOT-ATTESTED",
               actual_training="NOT RUN",blind="NOT RUN",
               readiness="REVIEW-REQUIRED")
    out["manifest_sha256"]=sha(encoded(out))
    return out


def main():
    parser=argparse.ArgumentParser(description="Private candidate split preparation only")
    parser.add_argument("--seed",required=True,type=Path)
    parser.add_argument("--rights",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    try:
        paths=[p.resolve() for p in (args.seed,args.rights,args.output)]
        need(len(set(paths))==3 and all(not p.is_relative_to(ROOT.resolve()) for p in paths),
             "private-path")
        def bounded(p):
            with p.open("rb") as f:
                return f.read(MAX_PACKET+1)
        result=prepare(bounded(paths[0]),bounded(paths[1]))
        # No overwrite of original data or candidate manifest.
        with paths[2].open("xb") as f:
            f.write(encoded(result)+b"\n")
        print(json.dumps({"status":"CANDIDATE-ONLY-NOT-A-LOCK","manifest_sha256":result["manifest_sha256"],
                          "suites":result["suites"],"supported_intents":result["supported_intents"],
                          "fuzzy_candidate_count":result["fuzzy_candidate_count"],
                          "missing_intent_counts":{s:len(v) for s,v in result["missing_supported_intents"].items()},
                          "training":"NOT RUN"},sort_keys=True))
    except (Reject,DomainReject,ValueError,TypeError,KeyError,OSError,RecursionError):
        raise SystemExit("F1 seed candidate rejected (sanitized; inspect private records)") from None


if __name__=="__main__":
    main()
