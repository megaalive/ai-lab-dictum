"""Actual C pipeline + independent oracle, synthetic functional development gold."""
import hashlib
import json
import math
import random
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tests/ir"))
from run import SCHEMAS, SCHEMA_DIR
from schema_profile import prepare_validators
from semantics import validate_chain
from wire import decode_frame, read_source

probe, cli = sys.argv[1:3]
manifest_raw = (HERE / "functional-v1.json").read_bytes()
manifest = json.loads(manifest_raw)
fixture_raw = (ROOT / "spec/pipeline/f0-c-fixture-v1.json").read_bytes()
fixture = json.loads(fixture_raw)
registry_raw = (ROOT / "catalog/core/intents-v1.json").read_bytes()
profile_raw = (ROOT / "catalog/debian-13/v1.json").read_bytes()
registry = {x["id"]: x for x in json.loads(registry_raw)["intents"] if x["skeleton"]}
catalog = {i: {"intent": i, "effect": x["effect"], "proposal_eligible": x["proposal_eligible"],
               "execute_eligible": False, "slots": {s["name"]: s for s in x["slots"]}}
           for i, x in registry.items()}
recipes = {x["intent"]: x for x in fixture["recipes"]}
identities = {"catalog": {"version": 1, "sha256": hashlib.sha256(registry_raw).hexdigest()},
              "policy": {"version": 1, "sha256": hashlib.sha256(fixture_raw).hexdigest()}}
validators, _, retrievals = prepare_validators({name: read_source(SCHEMA_DIR/name)
                                                 for name in SCHEMAS.values()})
reference = manifest["reference_unix_s"]
cases = manifest["cases"]
raw_gold_bytes = (HERE / "raw-gold-v1.json").read_bytes()
raw_gold = json.loads(raw_gold_bytes)["cases"]


def data(row):
    if "hex" in row:
        return bytes.fromhex(row["hex"])
    if "repeat" in row:
        return (row["repeat"][0] * row["repeat"][1]).encode()
    return row["text"].encode()


def hash_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def opaque(context_id, name):
    return hash_bytes((context_id + "/" + name).encode())[:32]


def parsed_stage(stage, obj):
    parsed = decode_frame(json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode())
    assert validators[SCHEMAS[stage]].is_valid(parsed), "stage-schema-" + stage


def check_invariants(result, raw, stdout):
    view = result["view"]
    assert view["copyability"] == "NON_COPYABLE" and view["execution_allowed"] is False
    assert view["observed_os_data"] is False and "command" not in view and "preview" not in view
    assert "CANARY_SECRET" not in stdout and "DCT008_CANARY" not in stdout
    if result["context"] is None:
        assert all(result[s] is None for s in SCHEMAS) and view["decision"] == "deny"
        return
    context = result["context"]
    assert context["mode"] == "synthetic-request-v1" and context["sequence"] == 1
    assert context["input_sha256"] == hash_bytes(raw) and context["reference_unix_s"] == reference
    assert context["catalog_sha256"] == identities["catalog"]["sha256"]
    assert context["policy_sha256"] == identities["policy"]["sha256"]
    assert context["profile_sha256"] == hash_bytes(profile_raw)
    # The probe embeds exact context snapshot bytes as its first JSON member.
    prefix = '{"context":'
    assert stdout.startswith(prefix)
    _, end = json.JSONDecoder().raw_decode(stdout, len(prefix))
    cid = hash_bytes(stdout[len(prefix):end].encode())
    trusted = {key+"_id": opaque(cid,key) for key in ("request","resolution","decision","action","scope")}
    trusted.update(context_id=cid, now_boottime_ms=1, context_until_boottime_ms=2,
                   phase="F0", candidates={})
    candidate = context["time_candidate"]
    if candidate is not None:
        a,b = candidate["start"],candidate["end"]
        token = raw[a:b]
        assert 0 <= a < b <= len(raw) and re.fullmatch(rb"[0-9]{1,16}",token)
        assert 1 <= int(token) <= 1440
        assert re.match(rb" (?:minutes|menit)(?: |[?]?$)",raw[b:],re.I)
        assert candidate["start_unix_s"] == reference - int(token)*60 and candidate["end_unix_s"] == reference
        trusted["candidates"][opaque(cid,"window")] = {"slot":"window","value":{
            "kind":"time-window","start_unix_s":candidate["start_unix_s"],"end_unix_s":reference}}
    stages = {s:result[s] for s in SCHEMAS if result[s] is not None}
    assert {"nlu","ir","policy"} <= stages.keys()
    for stage,obj in stages.items():
        parsed_stage(stage,obj)
    nlu, ir, policy = stages["nlu"],stages["ir"],stages["policy"]
    assert view["decision"] == policy["decision"] and view["reason"] == policy["reason"]
    allowed = policy["decision"] == "allow-proposal"
    assert allowed == ("plan" in stages)
    assert policy["decision"] != "allow-execute-eligible"
    values = {s["name"]:s["value"] for s in ir["slots"]}
    intent = ir.get("intent")
    if allowed:
        assert intent in registry and view["intent"] == intent and view["slots"] == values
        assert view["effect"] == registry[intent]["effect"]["class"]
        for name,v in values.items():
            spec = catalog[intent]["slots"][name]
            if spec["minimum"] is not None:
                assert spec["minimum"] <= v["value"] <= spec["maximum"]
            if name in {"root","unit","extension","filename"}:
                key = {"root":"roots","unit":"units","extension":"extensions","filename":"filenames"}[name]
                assert v["value"] in fixture["scope"][key]
        if intent == "network.listener.lookup":
            assert "port" in values and "protocol" in values
        if intent == "file.search":
            assert "root" in values and {"filename","extension","window"} & values.keys()
        if intent == "service.restart":
            assert "CHANGE" in view["warning"] and "no sudo" in view["warning"]
        plan = stages["plan"]
        operation = {"kind":"native","handler":recipes[intent]["handler"],
                     "input_slots":[s["name"] for s in registry[intent]["slots"] if s["name"] in values]}
        bindings = [{"slot":n,"binding_id":opaque(cid,n)} for n in operation["input_slots"] if n in {"root","unit"}]
        assert plan["action"] == {"kind":"structured-proposal","operation":operation}
        assert plan["target_bindings"] == bindings
        unsigned = {k:v for k,v in plan.items() if k!="digest"}
        assert plan["digest"] == hash_bytes(b"dictum:execution-plan:v1\n" +
            json.dumps(unsigned,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode())
        trusted["recipe"] = {"slots":values,"operation":operation,"target_bindings":bindings}
    else:
        assert "slots" not in view and "plan" not in stages
    # Existing oracle independently rechecks typed provenance, request identity,
    # transition, effect, scope and recipe. F0 has no boot-time authority.
    validate_chain({"input":raw.decode(),"trusted":trusted,"objects":stages},catalog,identities)


def gold_correct(row,result):
    e, view, ir = row["expected"],result["view"],result["ir"]
    if (view["decision"],view["reason"]) != (e["decision"],e["reason"]):
        return False
    if e["state"] is None:
        return ir is None
    if ir is None or ir["resolution"]["state"] != e["state"]:
        return False
    if e.get("intent") != ir.get("intent"):
        return False
    if e["decision"] == "allow-proposal":
        values = {s["name"]:s["value"] for s in ir["slots"]}
        return e["slots"] == values and result["nlu"]["intent_candidates"][0]["intent"] == e["intent"]
    if e["decision"] == "clarify":
        return (ir["resolution"]["unresolved"] == e["unresolved"] and
                ir["resolution"]["alternatives"] == e["alternatives"] and
                view["unresolved"] == e["unresolved"] and view["alternatives"] == e["alternatives"])
    return True


def raw_joint_correct(row,result):
    nlu = result["nlu"]
    expected = raw_gold[row["id"]]
    if nlu is None or nlu["abstain_hint"]!="none":
        return False
    intents = nlu["intent_candidates"]
    if len(intents)!=1 or intents[0]["intent"]!=expected["intent"]:
        return False
    slots=nlu["slot_candidates"]
    ids=intents[0]["slot_candidate_ids"]
    if len(ids)!=len(slots) or len(set(ids))!=len(ids) or set(ids)!={x["id"] for x in slots}:
        return False
    actual={}
    for x in slots:
        name=x["slot"]
        if name in actual:
            return False
        source=x["source"]
        if source["kind"]=="context-ref":
            context=result["context"]["time_candidate"]
            if context is None or source["expected_kind"]!="time-window":
                return False
            actual[name]={"kind":"context-ref","value":{"kind":"time-window",
                "start_unix_s":context["start_unix_s"],"end_unix_s":context["end_unix_s"]}}
        else:
            actual[name]=source
    return actual==expected["slots"]


def run(model):
    stats=Counter()
    timing=[]
    confusions=Counter()
    failures=[]
    for row in cases:
        raw=data(row)
        started=time.perf_counter_ns()
        p=subprocess.run([probe,model],input=raw,capture_output=True,timeout=5)
        timing.append((time.perf_counter_ns()-started)/1e6)
        stats[row["suite"],"total"]+=1
        try:
            assert p.returncode==0 and not p.stderr, "probe-process"
            stdout=p.stdout.decode("utf-8").rstrip("\n")
            result=json.loads(stdout)
            check_invariants(result,raw,stdout)
            correct=gold_correct(row,result)
            actual=result["view"]["decision"]
            accepted=actual=="allow-proposal"
            stats[row["suite"],"accepted"]+=accepted
            stats[row["suite"],"correct"]+=correct
            if row["suite"]=="supported":
                expected=row["expected"]
                raw_correct=(result["nlu"] is not None and
                    [x["intent"] for x in result["nlu"]["intent_candidates"]]==[expected["intent"]])
                stats["supported","raw_intent_correct"]+=raw_correct
                raw_joint=raw_joint_correct(row,result)
                stats["supported","raw_joint_correct"]+=raw_joint
                if not raw_joint:
                    print("RAW_JIA_MISS",model,row["id"])
                    if model=="B0":
                        failures.append(row["id"]+":raw-joint")
                confusions[expected["intent"],result["ir"].get("intent",actual) if result["ir"] else actual]+=1
                stats["language",row["language"],"total"]+=1
                stats["language",row["language"],"correct"]+=correct
            if not correct:
                failures.append(row["id"])
                print("GOLD_MISS",model,row["id"],"expected",row["expected"]["decision"],
                      "actual",actual)
            if row["suite"]=="security":
                assert not accepted, "security-proposal"
        except (AssertionError,ValueError,KeyError) as exc:
            # Never print raw bytes, paths, projected data or exception payload.
            print("INVARIANT_FAIL",model,row["id"],type(exc).__name__)
            raise SystemExit(1)
    n=stats["supported","total"]
    a=stats["supported","accepted"]
    c=stats["supported","correct"]
    all_n=sum(stats[x,"total"] for x in ("supported","ambiguity","ood","security"))
    all_a=sum(stats[x,"accepted"] for x in ("supported","ambiguity","ood","security"))
    all_c=sum(stats[x,"correct"] for x in ("supported","ambiguity","ood","security"))
    ordered=sorted(timing)
    print("PIPELINE_METRICS",model,json.dumps({
        "suite_counts":{x:{k:stats[x,k] for k in ("total","accepted","correct")} for x in ("supported","ambiguity","ood","security")},
        "raw_intent_accuracy":stats["supported","raw_intent_correct"]/n,
        "raw_JIA":stats["supported","raw_joint_correct"]/n,
        "resolved_JIA":c/n,"supported_JS":c/n,"supported_coverage":a/n,
        "supported_selective_accuracy":c/a if a else None,
        "all_case_outcome_accuracy":all_c/all_n,"all_case_coverage":all_a/all_n,
        "selective_accuracy":c/all_a if all_a else None,
        "language":{x:[stats["language",x,"correct"],stats["language",x,"total"]] for x in ("id","en")},
        "confusion":{a+" -> "+b:n for (a,b),n in confusions.items()},
        "cold_process_p50_ms":statistics.median(ordered),"cold_process_p95_ms":ordered[math.ceil(.95*len(ordered))-1],
        "timing_n":len(ordered),"failures":failures},sort_keys=True))
    return failures


def cli_checks():
    count=0
    for row in cases:
        if "text" not in row:
            continue
        p=subprocess.run([cli,"ask",row["text"]],capture_output=True,timeout=5)
        expected=row["expected"]
        assert not p.stderr and b"CANARY_SECRET" not in p.stdout and b"DCT008_CANARY" not in p.stdout
        view=json.loads(p.stdout)
        assert view["decision"]==expected["decision"] and view["reason"]==expected["reason"]
        assert p.returncode=={"allow-proposal":0,"unsupported":3,"deny":4,"clarify":5}[view["decision"]]
        assert view["copyability"]=="NON_COPYABLE" and "preview" not in view and "command" not in view
        if "intent" in expected and expected["intent"] is not None:
            assert view["intent"]==expected["intent"]
        if view["decision"]=="allow-proposal":
            assert view["observed_os_data"] is False and view["execution_allowed"] is False
            actual=view["slots"]
            for k,v in expected["slots"].items():
                if v["kind"]=="time-window":
                    assert actual[k]["end_unix_s"]-actual[k]["start_unix_s"]==v["end_unix_s"]-v["start_unix_s"]
                else:
                    assert actual[k]==v
        count+=1
    for args,rc in [(["explain","show available memory"],0),(["search","memory.summary"],0),
                    (["inspect"],0),(["show available memory"],0),
                    (["search","CANARY_SECRET"],3),(["run"],4),(["run","CANARY_SECRET"],4)]:
        p=subprocess.run([cli,*args],capture_output=True,timeout=5)
        assert p.returncode==rc and b"CANARY_SECRET" not in p.stdout+p.stderr
        count+=1
    print("ACTUAL_CLI_CHECKS",count)


def main():
    ids={r["id"] for r in cases}
    assert len(ids)==len(cases) and len({data(r) for r in cases})==len(cases)
    counts=Counter(r["suite"] for r in cases)
    assert counts["supported"]>=40 and counts["ambiguity"]+counts["ood"]>=20 and counts["security"]>=40
    for i in registry:
        items=[r for r in cases if r["suite"]=="supported" and r["expected"]["intent"]==i]
        assert len(items)>=5 and {r["language"] for r in items}=={"id","en"}
    assert set(raw_gold)=={r["id"] for r in cases if r["suite"]=="supported"}
    print("CORPUS",hash_bytes(manifest_raw),sorted(counts.items()),manifest["provenance"])
    print("RAW_GOLD",hash_bytes(raw_gold_bytes),len(raw_gold),"explicit slots only; SELF development labels")
    b0=run("B0")
    b1=run("B1")
    # B0 is primary functional gate; B1 misses retained (development baseline).
    if b0:
        return 1
    cli_checks()
    assert not retrievals
    return 0


if __name__=="__main__":
    sys.exit(main())
