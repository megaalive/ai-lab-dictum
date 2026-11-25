"""Private F1 development comparator. No blind or product model pack support.

Private entrypoint requires human-reviewed seed and rights/split lock. DEC-011
also permits a separate fixed project-original synthetic experiment; no fit on
repository regression/S2 cases or blind data.
All returned metrics are development, not a release/compatibility gate.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from f1_seed import (ROOT, MAX_PACKET, ID, SHA, SUITES, check_row, keys, load_contract,
                     match, parse, prepare, rights_check)
from f1_corpus import Reject, need, sha, encoded
from b2_linear import Linear, fit_numeric
from b2_dev_protocol import call, model_frame

SEED=20261124
EPOCHS=12
MARGINS=(1,2,4,8,16,32)
BUDGET={"seed":SEED,"epochs":EPOCHS,"margin_candidates":list(MARGINS),
        "fit_only":"supported-train","margin_selection":"max-dev-supported-exact-then-largest-margin"}
SYNTHETIC_BUDGET={**BUDGET,"margin_selection":"max-dev-supported-exact-then-raw-intent-then-largest-margin"}
LOCK_KEYS={"schema_version","role","scope","candidate_manifest_sha256","seed_sha256",
           "rights_sha256","owner_decision_ref","reviewer","review_evidence_sha256",
           "source_commit","binaries_sha256","fuzzy_review","budget",
           "allow_fit","allow_distribution","blind"}


def validate_lock(lock,candidate,source,binaries,*,mechanical=False):
    """Evidence shape + exact identity; never creates human approval."""
    keys(lock,LOCK_KEYS,"lock-shape")
    need(type(lock["schema_version"]) is int and lock["schema_version"]==1,"lock-version")
    need(lock["role"]==("MECHANICAL-TEST" if mechanical else "OWNER-REVIEWED-F1-DEVELOPMENT-LOCK")
         and candidate["role"]==("MECHANICAL-TEST" if mechanical else "PRIVATE-SPLIT-CANDIDATE"),
         "lock-role")
    need(lock["scope"]=="F1-B2-DEVELOPMENT-ONLY" and lock["allow_fit"] is (not mechanical)
         and lock["allow_distribution"] is False and lock["blind"] is False,"lock-scope")
    for field in ("seed_sha256","rights_sha256"):
        need(lock[field]==candidate[field] and match(lock[field],SHA),"lock-input")
    need(lock["candidate_manifest_sha256"]==candidate["manifest_sha256"] and
         candidate["manifest_sha256"]==sha(encoded({k:v for k,v in candidate.items() if k!="manifest_sha256"})),
         "lock-candidate")
    need(match(source,r"[0-9a-f]{40}") and lock["source_commit"]==source and
         lock["binaries_sha256"]==binaries and set(binaries)=={"probe","cli","b2_probe"} and
         all(match(x,SHA) for x in binaries.values()),"lock-build")
    need(match(lock["owner_decision_ref"],ID) and match(lock["reviewer"],ID) and
         match(lock["review_evidence_sha256"],SHA),"lock-review")
    need(encoded(lock["budget"])==encoded(BUDGET),"budget")
    expected={tuple(x) for x in candidate["fuzzy_pairs"]}
    need(type(lock["fuzzy_review"]) is list and len(lock["fuzzy_review"])==len(expected),"fuzzy-review")
    seen=set()
    for row in lock["fuzzy_review"]:
        keys(row,{"pair","decision","review_ref"},"fuzzy-shape")
        need(type(row["pair"]) is list and len(row["pair"])==2,"fuzzy-pair")
        p=tuple(row["pair"])
        need(p in expected and p not in seen and row["decision"] in
             {"KEEP-TOGETHER","FALSE-POSITIVE-KEEP-TOGETHER"} and match(row["review_ref"],ID),
             "fuzzy-decision")
        seen.add(p)
    if not mechanical:
        need(all(candidate["counts"][s].get("all",0)>0 for s in ("train","dev","test")),"empty-split")
        need(not candidate["missing_supported_intents"]["train"] and candidate["supported_intents"]==48,
             "train-class-coverage")
        need(bool(candidate["coverage"]["dev"]) and bool(candidate["coverage"]["test"]),
             "evaluation-supported-empty")
        # All 48 classes must occur in train. Never break canonical/lineage
        # groups just to improve dev/test class coverage. Report deficits.
        need(candidate["readiness"]=="REVIEW-REQUIRED" and candidate["blind"]=="NOT RUN","candidate")
    return True


def suite_of(row):
    return next(iter(set(row["tags"])&SUITES))


def score_rows(rows,results):
    """Full-denominator descriptive statistics, not an effects oracle."""
    expected={r["id"]:r for r in rows}
    need(len(expected)==len(rows) and len(rows)>0,"evaluation-ids")
    actual={r["id"]:r for r in results}
    need(len(actual)==len(results)==len(expected) and actual.keys()==expected.keys(),"evaluation-denominator")
    stats={s:Counter(total=0,accepted=0,correct=0,raw_joint=0,raw_intent=0) for s in sorted(SUITES)}
    by_intent={}
    by_language={}
    statuses=Counter()
    confusions=Counter()
    times=[]
    for i,row in expected.items():
        a=actual[i]
        s=suite_of(row)
        k=stats[s]
        need(a["status"] in {"complete","timeout","invalid","failure"} and
             all(type(a[f]) is bool for f in ("accepted","correct","raw_joint","raw_intent")),"result-shape")
        if a["status"]!="complete":
            need(not any(a[f] for f in ("accepted","correct","raw_joint","raw_intent")),"failed-result")
        if s=="supported":
            need(not a["correct"] or a["accepted"],"supported-result")
            need(not a["raw_joint"] or a["accepted"],"raw-joint")
        else:
            need(not a["raw_joint"] and not a["raw_intent"],"negative-raw")
        need(not (a["correct"] and s!="supported" and a["accepted"]),"negative-proposal")
        for f in ("accepted","correct","raw_joint","raw_intent"):
            k[f]+=int(a[f])
        k["total"]+=1
        statuses[a["status"]]+=1
        ms=a["cold_ms"]
        need(type(ms) in (int,float) and math.isfinite(ms) and ms>=0,"timing")
        times.append(ms)
        intent=row["expected"]["intent"]
        if s=="supported":
            for target,key in ((by_intent,intent),(by_language,row["language"])):
                c=target.setdefault(key,Counter(total=0,correct=0,accepted=0,raw_intent=0,raw_joint=0))
                c["total"]+=1
                c["correct"]+=a["correct"]
                c["accepted"]+=a["accepted"]
                c["raw_intent"]+=a["raw_intent"]
                c["raw_joint"]+=a["raw_joint"]
            confusions[str(intent)+" -> "+str(a["actual_intent"] or a["outcome"])]+=1
    n=stats["supported"]["total"]
    a=stats["supported"]["accepted"]
    c=stats["supported"]["correct"]
    ratio=lambda x,y:x/y if y else None
    times.sort()
    return {"suite_counts":{k:dict(v) for k,v in stats.items()},"statuses":dict(statuses),
            "resolved_JIA":ratio(c,n),"raw_JIA":ratio(stats["supported"]["raw_joint"],n),
            "raw_intent_accuracy":ratio(stats["supported"]["raw_intent"],n),
            "supported_coverage":ratio(a,n),"supported_selective_accuracy":ratio(c,a),
            "all_case_exact_outcome_accuracy":ratio(sum(x["correct"] for x in stats.values()),len(rows)),
            "ood_exact_recall":ratio(stats["ood"]["correct"],stats["ood"]["total"]),
            "ambiguity_exact_recall":ratio(stats["ambiguity"]["correct"],stats["ambiguity"]["total"]),
            "by_intent":{k:dict(v) for k,v in by_intent.items()},
            "by_language":{k:dict(v) for k,v in by_language.items()},"confusion":dict(confusions),
            "cold_process_p50_ms":statistics.median(times),"cold_process_p95_ms":times[math.ceil(.95*len(times))-1],
            "timing_n":len(times),"JS":"NOT EVALUATED — independent effects oracle not run",
            "PSS":"NOT EVALUATED","FES":"NOT RUN","gate":"NOT EVALUATED"}


def load_oracle(probe,cli):
    # Reuse the pinned independent semantic oracle, not outputs as labels.
    # Its historical regression inputs are not passed to the fitter.
    spec=importlib.util.spec_from_file_location("f1_private_oracle",ROOT/"tests/pipeline/run.py")
    module=importlib.util.module_from_spec(spec)
    saved=sys.argv
    try:
        sys.argv=[str(spec.origin),str(probe),str(cli)]
        spec.loader.exec_module(module)
    finally:
        sys.argv=saved
    return module


def bounded(path,limit=MAX_PACKET):
    with Path(path).open("rb") as f:
        data=f.read(limit+1)
    need(len(data)<=limit,"file-size")
    return data


def probe_result(probe,model,raw):
    p=subprocess.run([str(probe),model],input=raw,capture_output=True,timeout=5)
    need(p.returncode==0 and not p.stderr and len(p.stdout)<=65536,"native-probe")
    stdout=p.stdout.decode("utf-8","strict").rstrip("\n")
    return json.loads(stdout),stdout


def run_private(seed_bytes,rights_bytes,candidate,lock,source,binaries,probe,cli,b2_probe):
    need(__debug__,"oracle-asserts-required")
    # Recompute the candidate exactly; stale or hand-edited membership fails.
    need(prepare(seed_bytes,rights_bytes)==candidate,"candidate-drift")
    validate_lock(lock,candidate,source,binaries)
    rows=parse(seed_bytes)["records"]
    rights=rights_check(parse(rights_bytes),sha(seed_bytes),False)
    contract=load_contract()
    # Gold is human-supplied; only the native extractor supplies model features.
    raw_gold={}
    for row in rows:
        _,raw_slots,suite=check_row(row,contract,rights,False)
        if suite=="supported":
            raw_gold[row["id"]]={"intent":row["expected"]["intent"],"slots":raw_slots}
    return _compare_core(rows,raw_gold,candidate,lock,source,binaries,probe,cli,b2_probe)


def _compare_core(rows,raw_gold,candidate,lock,source,binaries,probe,cli,b2_probe,*,mechanical=False,synthetic=False,diagnostic=None):
    """Shared orchestration; private CLI always enters via validated run_private.

    The test-only mechanical invocation uses explicitly tagged artificial
    numeric/lexical vectors and never a rights-approved or human corpus.
    """
    need(__debug__,"oracle-asserts-required")
    need(not (mechanical and synthetic),"core-mode")
    role="MECHANICAL-TEST" if mechanical else "AI-SYNTHETIC-DEVELOPMENT" if synthetic else "HUMAN-DEVELOPMENT-SEED"
    need(all(r.get("role")==role for r in rows),"core-role")
    if synthetic:
        need(candidate["role"]=="LOCKED-SYNTHETIC-LEXICAL-DEVELOPMENT" and
             lock["owner_decision_ref"]=="DEC-011" and candidate["manifest_sha256"]==
             sha(encoded({k:v for k,v in candidate.items() if k!="manifest_sha256"})) and
             candidate["record_sha256"]=={r["id"]:sha(encoded(r)) for r in rows},"synthetic-lock")
    if diagnostic is not None:
        need(synthetic,"diagnostic-mode")
        diagnostic_rows,diagnostic_gold,dm=diagnostic
        need(dm["role"]=="LOCKED-SYNTHETIC-DIAGNOSTIC" and dm["fit_allowed"] is False and
             dm["base_manifest_sha256"]==candidate["manifest_sha256"] and
             dm["manifest_sha256"]==sha(encoded({k:v for k,v in dm.items() if k!="manifest_sha256"})) and
             dm["record_sha256"]=={r["id"]:sha(encoded(r)) for r in diagnostic_rows} and
             dm["accepted_rows"]==len(diagnostic_rows)==len(dm["record_sha256"]) and
             dm["gold_sha256"]==sha(encoded(diagnostic_gold)) and
             set(diagnostic_gold)=={r["id"] for r in diagnostic_rows if suite_of(r)=="supported"} and
             all(r["role"]=="AI-SYNTHETIC-DIAGNOSTIC" and r["split"]=="diagnostic" for r in diagnostic_rows) and
             not set(dm["record_sha256"])&set(candidate["rows"]),"diagnostic-lock")
    oracle=load_oracle(probe,cli)
    from wire import Reject as OracleReject
    oracle.raw_gold=raw_gold
    partitions={s:[r for r in rows if candidate["rows"][r["id"]]["split"]==s] for s in ("train","dev","test")}
    for s in partitions:
        partitions[s].sort(key=lambda row:row["id"])
    registry={i:n for n,i in enumerate(oracle.all_registry)}
    ids=list(oracle.all_registry)
    fit_rows=[]
    zero=model_frame(Linear.zero(),1)
    for row in partitions["train"]:
        if suite_of(row)!="supported":
            continue
        raw=row["text"].encode("utf-8")
        value,stdout=call(b2_probe,zero,raw)
        trace=value.pop("trace")
        try:
            oracle.check_invariants(value,raw,stdout)
        except (AssertionError,OracleReject,ValueError,KeyError,TypeError):
            raise Reject("training-invariant") from None
        need(trace["features_valid"],"training-feature-invalid")
        # Empty features are not silently dropped. Such a corpus cannot be
        # used with this baseline without a documented revision and lock.
        features=tuple(trace["features"])
        need(bool(features),"training-feature-empty")
        fit_rows.append((features,registry[row["expected"]["intent"]]))
    need(len({c for _,c in fit_rows})==(2 if mechanical else 48),"training-class-coverage")
    fit_started=time.perf_counter_ns()
    model=fit_numeric(fit_rows,epochs=EPOCHS,seed=SEED)
    fit_ms=(time.perf_counter_ns()-fit_started)/1e6
    weight_sha=sha(model_frame(model,1)[4:])

    def evaluate(rows,model_name,margin=None):
        frame=model_frame(model,margin) if model_name=="B2" else None
        result=[]
        for row in rows:
            raw=row["text"].encode("utf-8")
            started=time.perf_counter_ns()
            a={"id":row["id"],"status":"failure","outcome":"no-result","actual_intent":None,
               "accepted":False,"correct":False,"raw_joint":False,"raw_intent":False}
            try:
                if model_name=="B2":
                    obj,stdout=call(b2_probe,frame,raw)
                    trace=obj.pop("trace")
                    r=trace["rank"]
                    need(type(r) is int and -1<=r<len(ids),"rank")
                    predicted=ids[r] if r>=0 else None
                else:
                    obj,stdout=probe_result(probe,model_name,raw)
                    candidates=obj["nlu"]["intent_candidates"] if obj["nlu"] is not None else []
                    predicted=candidates[0]["intent"] if len(candidates)==1 else None
                oracle.check_invariants(obj,raw,stdout)
                accepted=obj["view"]["decision"]=="allow-proposal"
                supported=suite_of(row)=="supported"
                correct=oracle.gold_correct(row,obj)
                joint=bool(supported and accepted and oracle.raw_joint_correct(row,obj))
                a.update(status="complete",outcome=obj["view"]["decision"],
                         actual_intent=obj["view"].get("intent"),accepted=accepted,correct=correct,
                         raw_joint=joint,raw_intent=bool(supported and predicted==row["expected"]["intent"]))
            except subprocess.TimeoutExpired:
                a["status"]="timeout"
            except (AssertionError,OracleReject,ValueError,TypeError,KeyError,RuntimeError):
                a["status"]="invalid"
            except OSError:
                a["status"]="failure"
            a["cold_ms"]=(time.perf_counter_ns()-started)/1e6
            result.append(a)
        return {"metrics":score_rows(rows,result),"results":result}

    base={"schema_version":1,"role":"MECHANICAL-COMPARATOR-SMOKE" if mechanical else "SYNTHETIC-LEXICAL-DEVELOPMENT-RESULTS" if synthetic else "PRIVATE-DEVELOPMENT-RESULTS","source_commit":source,
          "candidate_manifest_sha256":candidate["manifest_sha256"],"rights_sha256":candidate["rights_sha256"],
          "owner_decision_ref":lock["owner_decision_ref"],"binaries_sha256":binaries,
          "budget":SYNTHETIC_BUDGET if synthetic else BUDGET,"weight_sha256":weight_sha,"training_supported_rows":len(fit_rows),
          "numeric_fit_wall_ms":fit_ms,"model_int16_bytes":len(model_frame(model,1))-4,
          "coverage_deficits":candidate["missing_supported_intents"],"blind":"NOT RUN",
          "reference_vm":"NOT RUN","FES":"NOT RUN","release_gate":"NOT EVALUATED",
          "timing":"cold subprocess wall time including model transport; no warm/RSS/reference claim",
          "rights_review":"MECHANICAL-NOT-AUTHORIZED" if mechanical else "DEC-011 project-original synthetic development only" if synthetic else "external decision recorded; not independently attested by program"}
    dev=partitions["dev"]
    need(any(suite_of(r)=="supported" for r in dev),"dev-supported-empty")
    dev_scores={}
    for margin in MARGINS:
        dev_scores[str(margin)]=evaluate(dev,"B2",margin)
    base["dev_margin_evaluation"]=dev_scores
    # Do not tune through timeouts/invalid execution or on the held-out test.
    if any(d["metrics"]["statuses"].get("complete",0)!=len(dev) for d in dev_scores.values()):
        base.update(status="INVALID-DEV-RUN",selected_margin=None,test="NOT RUN")
        return base
    selected=max(MARGINS,key=lambda m:(
        dev_scores[str(m)]["metrics"]["suite_counts"]["supported"]["correct"],
        dev_scores[str(m)]["metrics"]["suite_counts"]["supported"]["raw_intent"] if synthetic else 0,m))
    base["selected_margin"]=selected
    test=partitions["test"]
    base["test"]={m:evaluate(test,m,selected if m=="B2" else None) for m in ("B0","B1","B2")}
    base["status"]=("COMPLETE-MECHANICAL-SMOKE" if mechanical else "COMPLETE-SYNTHETIC-DEVELOPMENT" if synthetic else "COMPLETE-DEVELOPMENT") if all(
        v["metrics"]["statuses"].get("complete",0)==len(test) for v in base["test"].values()) else "COMPLETE-WITH-FAILURES"
    if diagnostic is not None:
        # Only now expose diagnostic labels to the semantic oracle, after
        # fitting, margin selection and frozen test evaluation are complete.
        oracle.raw_gold=diagnostic_gold
        base["diagnostic_manifest_sha256"]=dm["manifest_sha256"]
        base["diagnostic"]={m:evaluate(diagnostic_rows,m,selected if m=="B2" else None)
                            for m in ("B0","B1","B2")}
        base["diagnostic_status"]="COMPLETE-DIAGNOSTIC" if all(
            v["metrics"]["statuses"].get("complete",0)==len(diagnostic_rows)
            for v in base["diagnostic"].values()) else "COMPLETE-WITH-FAILURES"
    return base


def main():
    parser=argparse.ArgumentParser(description="Private approved F1 development comparison; no blind")
    for arg in ("seed","rights","candidate","lock","probe","cli","b2-probe","output"):
        parser.add_argument("--"+arg,required=True,type=Path)
    args=parser.parse_args()
    try:
        need(__debug__,"oracle-asserts-required")
        private=[p.resolve() for p in (args.seed,args.rights,args.candidate,args.lock,args.output)]
        need(len(set(private))==5 and all(not p.is_relative_to(ROOT.resolve()) for p in private),
             "private-path")
        need(not private[-1].exists(),"no-overwrite")
        source=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],timeout=5).decode().strip()
        dirty=subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain"],timeout=5)
        need(not dirty,"dirty-source")
        probes={k:p.resolve() for k,p in {"probe":args.probe,"cli":args.cli,"b2_probe":args.b2_probe}.items()}
        binaries={k:sha(bounded(p,128*1024*1024)) for k,p in probes.items()}
        seed,rights,candidate_raw,lock_raw=(bounded(p) for p in private[:4])
        candidate,lock=parse(candidate_raw),parse(lock_raw)
        # Shape checks are not identity/authentication of the human signers.
        result=run_private(seed,rights,candidate,lock,source,binaries,**probes)
        # Metrics contain floating values; use strict finite JSON encoding.
        raw=json.dumps(result,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()+b"\n"
        with private[-1].open("xb") as f:
            f.write(raw)
        print(json.dumps({"status":result["status"],"result_sha256":sha(raw),
                          "selected_margin":result["selected_margin"],"blind":"NOT RUN",
                          "release_gate":"NOT EVALUATED"},sort_keys=True))
    except (Reject,ValueError,TypeError,KeyError,AssertionError,OSError,subprocess.SubprocessError,RecursionError):
        raise SystemExit("F1 private comparator rejected (sanitized; no automatic retry)") from None


if __name__=="__main__":
    main()
