"""DEC-011: bounded actual B2 fit on new project-original synthetic text.

Only the exact checked-in, reviewed template spec is supported. No external
corpus import, human-gold claim, arbitrary model loader, blind or execution.
"""
import argparse
import json
import re
import string
import subprocess
import sys
from collections import Counter
from pathlib import Path

from f1_corpus import ROOT, Reject, need, sha, encoded, normalize, similar
from f1_seed import (REFERENCE, blob, check_slots, exact_text, keys, load_contract,
                     read_regression_texts, SUITES, parse)
from f1_compare import (_compare_core, SYNTHETIC_BUDGET, bounded)

SPEC=ROOT/"data/synthetic/f1-template-families-v1.json"
SPEC_BLOB="d962635f082ed29b155f0bb46771654c48b467ca"
DIAGNOSTIC_SPEC=ROOT/"data/synthetic/f1-diagnostic-families-v1.json"
DIAGNOSTIC_BLOB="4720cafe0508c90e2329206740d74cc9cbb6b2a1"
DECISION_BLOB="235bbe0e82f5caf38662e6f9527b0c999be3d4a4"
SPLITS=("train","dev","test")
SPEC_KEYS={"schema_version","role","decision","author","generator_version","generation_seed",
           "split_protocol","families","negatives"}
FAMILY_KEYS={"id","intent","split","language","template"}
NEGATIVE_KEYS={"id","split","language","suite","text","intent","unresolved"}
PROTOCOL="LEXICAL-TEMPLATE-HOLDOUT-SHARED-CANONICAL-SEMANTICS"

def validate_spec(spec,contract):
    keys(spec,SPEC_KEYS,"spec-keys")
    need(type(spec["schema_version"]) is int and spec["schema_version"]==1 and
         spec["role"]=="PROJECT-ORIGINAL-SYNTHETIC-TEMPLATE-FAMILIES" and spec["decision"]=="DEC-011"
         and spec["author"]=="ChatGPT-GPT-6.2-SELF" and spec["generator_version"]=="f1-synthetic-v1"
         and spec["generation_seed"]==20261124 and spec["split_protocol"]==PROTOCOL,"spec-identity")
    need(type(spec["families"]) is list and len(spec["families"])==384 and
         type(spec["negatives"]) is list and len(spec["negatives"])==36,"spec-size")
    ids=set()
    for f in spec["families"]:
        keys(f,FAMILY_KEYS,"family")
        need(f["intent"] in contract["catalog"] and f["split"] in SPLITS and f["language"] in {"id","en"}
             and type(f["id"]) is str and re.fullmatch(r"SYN-F[0-9]+-[0-9]+",f["id"])
             and f["id"] not in ids,"family-identity")
        ids.add(f["id"])
        exact_text(f["template"])
    counts=Counter((f["intent"],f["split"],f["language"]) for f in spec["families"])
    need(counts==Counter({(i,s,l):2 if s=="train" else 1 for i in contract["catalog"]
                          for s in SPLITS for l in ("id","en")}),"family-coverage")
    for n in spec["negatives"]:
        keys(n,NEGATIVE_KEYS,"negative")
        need(n["split"] in SPLITS and n["language"] in {"id","en"} and n["suite"] in SUITES-{"supported"}
             and type(n["id"]) is str and re.fullmatch(r"SYN-N[0-9]+",n["id"]) and n["id"] not in ids,"negative-id")
        ids.add(n["id"])
        exact_text(n["text"])
    need(Counter((n["split"],n["language"],n["suite"]) for n in spec["negatives"])==
         Counter({(s,l,k):2 for s in SPLITS for l in ("id","en") for k in SUITES-{"supported"}}),
         "negative-coverage")

def values(f,contract,fields):
    i=f["intent"]
    c=contract["catalog"][i]
    scope=contract["scope"]
    domains=contract["domains"]["scope"]
    def pick(name,options):
        k=int(sha((f["id"]+"/"+name+"/20261124").encode())[:8],16)
        return options[k%len(options)]
    options={"utility":domains["utility-id"],"port":[8080,8443,3306,5432,9090,2200],
             "protocol":["tcp","udp"],"limit":[5,10,20,25],"depth":[2,3,4],
             "count":[1,2,3,4],"target":domains["network-target"],
             "domain":domains["dns-name"],"unit":scope["units"],"window":[7,15,25,45,90],
             "root":[x for x in scope["roots"] if " " not in x],
             "extension":scope["extensions"],"text":domains["literal-text"],
             "direction":["first","last"],"name":domains["process-name"],
             "package":domains["package-id"],"query":domains["package-query"],
             "path":scope["archives"] if i=="archive.contents.list" else
                   [x for x in scope["files"] if x not in scope["archives"] and " " not in x],
             "archive":scope["archives"],"source":scope["compress_sources"],
             "destination":scope["extract_destinations"] if i=="archive.extract.safe" else scope["compress_destinations"]}
    if i=="network.connection.active":
        options["protocol"]=["tcp","udp","all"]
    need(fields<=c["slots"].keys(),"template-slot")
    out={}
    for name in sorted(fields):
        if name=="option":
            need("utility" in fields,"option-utility")
            out[name]=pick(name,contract["domains"]["utility_options"][pick("utility",options["utility"])])
        else:
            need(name in options,"slot-generator")
            out[name]=pick(name,options[name])
    if i=="file.compress.archive" and "source" in out and "destination" in out:
        allowed=[x for x in options["destination"] if x!=out["source"] and not x.startswith(out["source"]+"/")]
        need(bool(allowed),"destination")
        out["destination"]=pick("safe-destination",allowed)
    return out

def supported(f,contract):
    c=contract["catalog"][f["intent"]]
    pieces=list(string.Formatter().parse(f["template"]))
    fields=[field for _,field,_,_ in pieces if field is not None]
    need(len(fields)==len(set(fields)) and all(field in c["slots"] for field in fields) and
         all(not fmt and conv is None for _,field,fmt,conv in pieces if field is not None),"template-format")
    val=values(f,contract,set(fields))
    raw=b""
    slots={}
    sources={}
    for literal,field,_,_ in pieces:
        raw+=literal.encode("utf-8")
        if field is None:
            continue
        value=val[field]
        b=str(value).encode()
        ref={"start":len(raw),"end":len(raw)+len(b)}
        raw+=b
        kind=c["slots"][field]["kind"]
        if kind=="time-window":
            slots[field]={"kind":kind,"start_unix_s":REFERENCE-int(value)*60,"end_unix_s":REFERENCE}
            sources[field]={"kind":"context-ref","span":ref}
        else:
            slots[field]={"kind":kind,"value":value}
            sources[field]={"kind":"input-span","span":ref}
    for name,s in c["slots"].items():
        if s["required"] and name not in slots:
            need(s["default"] is not None,"missing-required-slot")
            slots[name]=s["default"]
            sources[name]={"kind":"catalog-default"}
    tags=["supported"]
    if "network" in c["effect"]["axes"]:
        tags.append("NET")
    if c["effect"]["class"]=="CHANGE":
        tags.append("CHANGE")
    row={"id":f["id"],"family":f["id"],"split":f["split"],"language":f["language"],"role":"AI-SYNTHETIC-DEVELOPMENT",
         "text":raw.decode("utf-8"),"fixture_id":c["fixture_id"],"slot_sources":sources,"tags":tags,
         "expected":{"intent":f["intent"],"state":"resolved","decision":"allow-proposal","reason":"proposal-eligible","slots":slots}}
    exact_text(row["text"])
    raw_slots=check_slots(row,raw,c,contract)
    return row,{"intent":f["intent"],"slots":raw_slots}

def negative(n,contract):
    suite=n["suite"]
    intent=n["intent"]
    unresolved=n["unresolved"]
    if suite=="ambiguity":
        need(intent in contract["catalog"] and type(unresolved) is list and len(unresolved)>0,"ambiguity")
        c=contract["catalog"][intent]
        seen=set()
        for item in unresolved:
            keys(item,{"slot","problem"},"unresolved")
            need(item["slot"] in c["slots"] and item["slot"] not in seen and
                 item["problem"]=="missing","unresolved-slot")
            seen.add(item["slot"])
        e={"intent":intent,"state":"incomplete","decision":"clarify","reason":"missing-slot",
           "unresolved":unresolved,"alternatives":[]}
    else:
        need(intent is None and unresolved==[],"negative-label")
        e={"intent":None,"state":"unsupported" if suite=="ood" else "invalid",
           "decision":"unsupported" if suite=="ood" else "deny",
           "reason":"unsupported-intent" if suite=="ood" else "invalid-candidate"}
    return {"id":n["id"],"family":n["id"],"split":n["split"],"language":n["language"],
            "role":"AI-SYNTHETIC-DEVELOPMENT","text":n["text"],"tags":[suite],
            "fixture_id":contract["catalog"][intent]["fixture_id"] if intent else "NO-INTENT",
            "slot_sources":{},"expected":e}

def freeze(spec,contract,regression):
    """Before any fit: quarantine exact/fuzzy collisions, whole families only.

    Single seed realization per family in v1. Canonical label/fixture reuse is
    explicit and intentional for the lexical-only diagnostic. No claim of
    semantic/compositional independence or user distribution.
    """
    validate_spec(spec,contract)
    rows=[]
    gold={}
    for f in spec["families"]:
        row,g=supported(f,contract)
        rows.append(row)
        gold[row["id"]]=g
    rows+= [negative(n,contract) for n in spec["negatives"]]
    normal={r["id"]:normalize(r["text"]) for r in rows}
    rejected={}
    for row in rows:
        i=row["id"]
        n=normal[i]
        if n in regression or any(similar(n,x) for x in regression):
            rejected[i]={"reason":"VISIBLE-REGRESSION-COLLISION"}
    # Quarantine both sides for exact duplicates and cross-split fuzzy
    # collisions; no model outcomes have been seen and no split reassignment.
    within_fuzzy=0
    for k,a in enumerate(rows):
        for b in rows[k+1:]:
            ai,bi=a["id"],b["id"]
            exact=normal[ai]==normal[bi]
            near=similar(normal[ai],normal[bi])
            if exact or (near and a["split"]!=b["split"]):
                for i,other in ((ai,bi),(bi,ai)):
                    rejected.setdefault(i,{"reason":"CROSS-FAMILY-COLLISION" if exact else
                                           "CROSS-SPLIT-FUZZY","peer":other})
            elif near:
                within_fuzzy+=1
    rows=[r for r in rows if r["id"] not in rejected]
    gold={i:g for i,g in gold.items() if i not in rejected}
    by_id={r["id"]:r for r in rows}
    counts={s:dict(Counter("all" for r in rows if r["split"]==s)) for s in SPLITS}
    suites={s:dict(Counter(next(t for t in r["tags"] if t in SUITES) for r in rows if r["split"]==s)) for s in SPLITS}
    coverage={s:sorted({r["expected"]["intent"] for r in rows if r["split"]==s and "supported" in r["tags"]}) for s in SPLITS}
    deficit={s:sorted(set(contract["catalog"])-set(coverage[s])) for s in SPLITS}
    need(len(rows)>=200 and not deficit["train"] and all(coverage[s] for s in SPLITS),"coverage-after-quarantine")
    need(all(set(suites[s])==SUITES for s in ("dev","test")),"negative-coverage-after-quarantine")
    # All rows were generated/validated prior to fitting; manifest records
    # exact hashes and fixed assignments, including every quarantine ID.
    manifest={"schema_version":1,"role":"LOCKED-SYNTHETIC-LEXICAL-DEVELOPMENT","decision":"DEC-011",
              "protocol":PROTOCOL,"generator_version":spec["generator_version"],"seed":20261124,
              "source_template_sha256":sha(SPEC.read_bytes()),"spec_blob":SPEC_BLOB,
              "owner_decision_blob":DECISION_BLOB,"contract":contract["identities"],
              "human_gold_count":0,"review":"SELF-AI; typed/provenance validation, not human semantics",
              "candidate_rows":420,"accepted_rows":len(rows),"quarantine":rejected,
              "within_split_fuzzy_pairs":within_fuzzy,"cross_split_retained_fuzzy_pairs":0,
              "counts":counts,"suite_counts":suites,"coverage":coverage,"missing_supported_intents":deficit,
              "language_counts":{s:dict(Counter(r["language"] for r in rows if r["split"]==s)) for s in SPLITS},
              "rows":{i:{"split":r["split"],"family":r["family"],"text_sha256":sha(r["text"].encode()),
                         "normalized_sha256":sha(normal[i].encode())} for i,r in by_id.items()},
              "record_sha256":{i:sha(encoded(r)) for i,r in by_id.items()},
              "rights":{"scope":"PROJECT-ORIGINAL-SYNTHETIC-DEVELOPMENT-ONLY","owner_decision":"DEC-011",
                        "allow_fit":True,"distribution_allowed":False,"third_party_data":False,"blind":False},
              "budget":SYNTHETIC_BUDGET,"blind":"NOT RUN","release_gate":"NOT EVALUATED"}
    manifest["rights_sha256"]=sha(encoded(manifest["rights"]))
    manifest["manifest_sha256"]=sha(encoded(manifest))
    return rows,gold,manifest

def prepare():
    raw=SPEC.read_bytes()
    need(blob(raw)==SPEC_BLOB and blob((ROOT/"plans/baseline-v3.md").read_bytes())==DECISION_BLOB,
         "source-or-decision-drift")
    return freeze(parse(raw),load_contract(),read_regression_texts())

def prepare_diagnostic(base_rows,base_manifest):
    """Freeze a separate original AI diagnostic before any new model outcome.

    No diagnostic record or label is used in fitting or margin selection.
    Quarantine collisions with the entire original 420-row experiment,
    visible regressions and other diagnostic families; report every loss.
    This is not a blind/human holdout or representative distribution.
    """
    raw=DIAGNOSTIC_SPEC.read_bytes()
    need(blob(raw)==DIAGNOSTIC_BLOB,"diagnostic-source-drift")
    spec=parse(raw)
    keys(spec,{"schema_version","role","decision","author","families","negatives"},"diagnostic-spec")
    need(type(spec["schema_version"]) is int and spec["schema_version"]==1 and
         spec["role"]=="PROJECT-ORIGINAL-LOCKED-DIAGNOSTIC" and spec["decision"]=="DEC-011" and
         spec["author"]=="ChatGPT-GPT-6.2-SELF","diagnostic-identity")
    contract=load_contract()
    families=spec["families"]
    negatives=spec["negatives"]
    need(type(families) is list and len(families)==96 and type(negatives) is list and
         len(negatives)==12,"diagnostic-size")
    seen=set()
    rows=[]
    gold={}
    for f in families:
        keys(f,FAMILY_KEYS,"diagnostic-family")
        need(f["intent"] in contract["catalog"] and f["split"]=="diagnostic" and
             f["language"] in {"id","en"} and type(f["id"]) is str and
             re.fullmatch(r"DIA-F[0-9]{2}-(id|en)",f["id"]) and
             f["id"].endswith("-"+f["language"]) and f["id"] not in seen,"diagnostic-family-id")
        seen.add(f["id"])
        exact_text(f["template"])
        row,g=supported(f,contract)
        rows.append(row)
        gold[row["id"]]=g
    need(Counter((f["intent"],f["language"]) for f in families)==
         Counter({(i,l):1 for i in contract["catalog"] for l in ("id","en")}),"diagnostic-class-coverage")
    for n in negatives:
        keys(n,NEGATIVE_KEYS,"diagnostic-negative")
        need(n["split"]=="diagnostic" and n["language"] in {"id","en"} and
             n["suite"] in SUITES-{"supported"} and type(n["id"]) is str and
             re.fullmatch(r"DIA-N[0-9]{2}",n["id"]) and n["id"] not in seen,"diagnostic-negative-id")
        seen.add(n["id"])
        exact_text(n["text"])
        rows.append(negative(n,contract))
    need(Counter((n["suite"],n["language"]) for n in negatives)==
         Counter({(k,l):2 for k in SUITES-{"supported"} for l in ("id","en")}),"diagnostic-negative-coverage")
    for row in rows:
        row["role"]="AI-SYNTHETIC-DIAGNOSTIC"
    normal={r["id"]:normalize(r["text"]) for r in rows}
    base_normal={normalize(r["text"]) for r in base_rows}|set(read_regression_texts())
    rejected={}
    for row in rows:
        i=row["id"]
        n=normal[i]
        if n in base_normal or any(similar(n,x) for x in base_normal):
            rejected[i]={"reason":"PREVIOUS-DEVELOPMENT-COLLISION"}
    for k,a in enumerate(rows):
        for b in rows[k+1:]:
            ai,bi=a["id"],b["id"]
            if normal[ai]==normal[bi] or similar(normal[ai],normal[bi]):
                for i,other in ((ai,bi),(bi,ai)):
                    rejected.setdefault(i,{"reason":"DIAGNOSTIC-FAMILY-COLLISION","peer":other})
    rows=[r for r in rows if r["id"] not in rejected]
    gold={i:g for i,g in gold.items() if i not in rejected}
    coverage=sorted({r["expected"]["intent"] for r in rows if "supported" in r["tags"]})
    suites=Counter(next(t for t in r["tags"] if t in SUITES) for r in rows)
    need(len(coverage)>=36 and set(suites)==SUITES and
         {r["language"] for r in rows if "supported" in r["tags"]}=={"id","en"},
         "diagnostic-coverage-after-quarantine")
    manifest={"schema_version":1,"role":"LOCKED-SYNTHETIC-DIAGNOSTIC","decision":"DEC-011",
              "source_spec_blob":DIAGNOSTIC_BLOB,"source_spec_sha256":sha(raw),
              "base_manifest_sha256":base_manifest["manifest_sha256"],
              "fit_allowed":False,"human_gold_count":0,"blind":"NOT RUN",
              "candidate_rows":108,"accepted_rows":len(rows),"quarantine":rejected,
              "suite_counts":dict(suites),"coverage":coverage,
              "missing_supported_intents":sorted(set(contract["catalog"])-set(coverage)),
              "language_counts":dict(Counter(r["language"] for r in rows)),
              "record_sha256":{r["id"]:sha(encoded(r)) for r in rows},
              "gold_sha256":sha(encoded(gold))}
    manifest["manifest_sha256"]=sha(encoded(manifest))
    return rows,gold,manifest


def summary(manifest):
    return {k:manifest[k] for k in ("manifest_sha256","source_template_sha256","candidate_rows","accepted_rows",
        "counts","suite_counts","language_counts","missing_supported_intents","human_gold_count",
        "within_split_fuzzy_pairs","cross_split_retained_fuzzy_pairs","protocol","review","rights","budget")}|{
        "quarantine_count":len(manifest["quarantine"]),"quarantined":manifest["quarantine"]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only",action="store_true")
    parser.add_argument("--diagnostic-replay",action="store_true")
    parser.add_argument("--locked-diagnostic",action="store_true")
    for arg in ("probe","cli","b2-probe","output"):
        parser.add_argument("--"+arg,type=Path)
    a=parser.parse_args()
    try:
        need(__debug__,"asserts-required")
        rows,gold,manifest=prepare()
        if a.diagnostic_replay:
            need(manifest["manifest_sha256"]=="aa4c817e14e7901d25e062bdd3d60943ea4f927e178ec904492cd3673882c68e",
                 "observed-diagnostic-manifest-drift")
        print("F1_SYNTHETIC_MANIFEST "+json.dumps(summary(manifest),sort_keys=True),flush=True)
        diagnostic=prepare_diagnostic(rows,manifest) if a.locked_diagnostic else None
        if diagnostic is not None:
            print("F1_LOCKED_DIAGNOSTIC_MANIFEST "+json.dumps(
                {k:v for k,v in diagnostic[2].items() if k!="record_sha256"},sort_keys=True),flush=True)
        if a.prepare_only:
            need(all(x is None for x in (a.probe,a.cli,a.b2_probe,a.output)),"prepare-arguments")
            return
        need(all(x is not None for x in (a.probe,a.cli,a.b2_probe,a.output)),"fit-arguments")
        output=a.output.resolve()
        need(not output.is_relative_to(ROOT.resolve()) and not output.exists(),"output")
        def git(*args):
            return subprocess.check_output(["git","-c",f"safe.directory={ROOT.as_posix()}","-C",str(ROOT),*args],timeout=10)
        source=git("rev-parse","HEAD").decode().strip()
        need(re.fullmatch(r"[0-9a-f]{40}",source) and not git("status","--porcelain"),"source")
        probes={k:v.resolve() for k,v in {"probe":a.probe,"cli":a.cli,"b2_probe":a.b2_probe}.items()}
        binaries={k:sha(bounded(v,128*1024*1024)) for k,v in probes.items()}
        out=_compare_core(rows,gold,manifest,{"owner_decision_ref":"DEC-011"},source,binaries,**probes,synthetic=True,diagnostic=diagnostic)
        out["evaluation_role"]="OBSERVED-TEST-DIAGNOSTIC-REPLAY" if a.diagnostic_replay else "FROZEN-LEXICAL-BASELINE-REPRODUCTION"
        payload={"manifest":manifest,"results":out}
        if diagnostic is not None:
            payload["diagnostic_manifest"]=diagnostic[2]
        data=json.dumps(payload,sort_keys=True,ensure_ascii=False,
                        separators=(",",":"),allow_nan=False).encode()+b"\n"
        with output.open("xb") as f:
            f.write(data)
        result={k:out[k] for k in ("status","source_commit","binaries_sha256","candidate_manifest_sha256",
            "weight_sha256","training_supported_rows","numeric_fit_wall_ms","model_int16_bytes",
            "selected_margin","budget","blind","release_gate")}
        result["result_sha256"]=sha(data)
        result["dev_margin_counts"]={k:v["metrics"]["suite_counts"] for k,v in out["dev_margin_evaluation"].items()}
        result["test"]={m:v["metrics"] for m,v in out["test"].items()} if type(out["test"]) is dict else out["test"]
        result["evaluation_role"]=out["evaluation_role"]
        if diagnostic is not None:
            result["diagnostic_manifest_sha256"]=diagnostic[2]["manifest_sha256"]
            result["diagnostic_status"]=out.get("diagnostic_status","NOT RUN")
            result["diagnostic"]={m:v["metrics"] for m,v in out.get("diagnostic",{}).items()}
        print(("F1_COMPOSITION_B2_RESULT " if a.diagnostic_replay else "F1_SYNTHETIC_B2_RESULT ")+json.dumps(result,sort_keys=True),flush=True)
        need(out["status"]=="COMPLETE-SYNTHETIC-DEVELOPMENT","incomplete-run")
        if diagnostic is not None:
            need(out.get("diagnostic_status")=="COMPLETE-DIAGNOSTIC","incomplete-diagnostic")
            # Report outcomes first; an unexpected negative proposal is not
            # a passing boundary even if the product is non-executable.
            need(all(v["metrics"]["suite_counts"][k]["accepted"]==0
                     for v in out["diagnostic"].values() for k in SUITES-{"supported"}),
                 "diagnostic-negative-proposal")
    except (Reject,ValueError,TypeError,KeyError,AssertionError,OSError,subprocess.SubprocessError,RecursionError) as exc:
        # No actual private inputs are accepted. Only fixed project data here.
        raise SystemExit("F1 synthetic experiment rejected: "+type(exc).__name__+" "+str(exc)[:160]) from None

if __name__=="__main__":
    main()
