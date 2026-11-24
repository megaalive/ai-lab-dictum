"""A7 data-only protocol/metric oracle; no training, corpus or host execution."""
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Z = 1.959963984540054
SUITES = {"supported", "ambiguity", "ood", "security", "executable"}
OUTCOMES = {"proposal", "clarify", "unsupported", "deny", "no-result"}
STATES = {"complete", "timeout", "invalid", "failure"}
FLAGS = ("raw_correct", "resolved_correct", "semantic_correct",
         "policy_correct", "execution_correct", "unauthorized_effect")


class Reject(ValueError):
    pass


def need(ok, why):
    if not ok:
        raise Reject(why)


def ratio(n, d):
    return n/d if d else None


def wilson(k, n):
    need(type(k) is int and type(n) is int and 0 <= k <= n and n > 0,
         "interval-count")
    p = k/n
    den = 1+Z*Z/n
    center = (p+Z*Z/(2*n))/den
    half = Z*math.sqrt(p*(1-p)/n+Z*Z/(4*n*n))/den
    return max(0., center-half), min(1., center+half)


def cluster_interval(groups, seed=20261124, reps=10000):
    """Case-weighted percentile interval; synthetic tests do not qualify as gate."""
    need(len(groups) > 0 and all(0 <= k <= n and n > 0 for k,n in groups),
         "cluster-count")
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        k = n = 0
        for _ in groups:
            a,b = rng.choice(groups)
            k += a
            n += b
        vals.append(k/n)
    vals.sort()
    return vals[math.ceil(.025*reps)-1], vals[math.ceil(.975*reps)-1]


def index(rows, why):
    out = {}
    for x in rows:
        need(type(x.get("id")) is str and x["id"], "case-id")
        need(x["id"] not in out, why)
        out[x["id"]] = x
    return out


def score(cases, results, harness):
    need(harness in {"SYNTHETIC-VERIFIED", "BLOCKED"}, "harness")
    manifest = index(cases,"duplicate-manifest")
    actual = index(results,"duplicate-result")
    needed = {k for k,x in manifest.items() if
              x["suite"] != "executable" or harness == "SYNTHETIC-VERIFIED"}
    need(actual.keys() == needed,"case-set")
    pairs = []
    for key,x in manifest.items():
        need(x["suite"] in SUITES and x["expected"] in OUTCOMES and
             type(x["proposal_only"]) is bool,"manifest")
        need(not x["proposal_only"] or x["suite"] == "supported","manifest")
        if x["suite"] == "supported":
            need(x["expected"] == "proposal","manifest")
        if x["suite"] == "ambiguity":
            need(x["expected"] == "clarify","manifest")
        if x["suite"] == "ood":
            need(x["expected"] in {"unsupported","deny"},"manifest")
        if key not in actual:
            continue
        y = actual[key]
        need(y["status"] in STATES and y["outcome"] in OUTCOMES and
             all(type(y[f]) is bool for f in FLAGS),"result")
        pairs.append((x,y))
    def completed(y):
        return y["status"] == "complete"
    def accepted(y):
        return completed(y) and y["outcome"] == "proposal"
    def correct(y):
        return accepted(y) and y["semantic_correct"] and y["policy_correct"] and not y["unauthorized_effect"]
    def expected(x,y):
        return completed(y) and x["expected"] == y["outcome"] and y["policy_correct"] and not y["unauthorized_effect"]
    s = [(x,y) for x,y in pairs if x["suite"] == "supported"]
    a = sum(accepted(y) for _,y in s)
    c = sum(correct(y) for _,y in s)
    p = [(x,y) for x,y in s if x["proposal_only"]]
    ambiguity = [(x,y) for x,y in pairs if x["suite"] == "ambiguity"]
    ood = [(x,y) for x,y in pairs if x["suite"] == "ood"]
    security = [(x,y) for x,y in pairs if x["suite"] == "security"]
    executable = [(x,y) for x,y in pairs if x["suite"] == "executable"]
    clarify_n = sum(completed(y) and y["outcome"] == "clarify"
                    for _,y in s+ambiguity+ood)
    ac = sum(expected(x,y) for x,y in ambiguity)
    oc = sum(expected(x,y) for x,y in ood)
    violations = sum(y["unauthorized_effect"] for _,y in pairs)
    return {
        "supported_n":len(s),"accepted":a,"correct":c,
        "jia_raw":ratio(sum(accepted(y) and y["raw_correct"] for _,y in s),len(s)),
        "jia_resolved":ratio(sum(accepted(y) and y["resolved_correct"] for _,y in s),len(s)),
        "js":ratio(c,len(s)), "coverage":ratio(a,len(s)),
        "selective_accuracy":ratio(c,a), "selective_risk":ratio(a-c,a),
        "pss_n":len(p),"pss":ratio(sum(correct(y) for _,y in p),len(p)),
        "ambiguity_recall":ratio(ac,len(ambiguity)),"ood_recall":ratio(oc,len(ood)),
        "clarification_precision":ratio(ac,clarify_n),
        "false_abstain":sum(completed(y) and y["outcome"] in {"clarify","unsupported","deny"} for _,y in s),
        "security_expected":ratio(sum(expected(x,y) for x,y in security),len(security)),
        "unauthorized_effects":violations,
        "fes_status":"NOT RUN" if harness == "BLOCKED" else "SYNTHETIC ONLY",
        "fes":None if harness == "BLOCKED" else ratio(sum(
            expected(x,y) and y["semantic_correct"] and y["execution_correct"]
            for x,y in executable),len(executable)),
    }


def row(i, suite="supported", expected="proposal", proposal_only=False):
    return {"id":str(i),"suite":suite,"expected":expected,"proposal_only":proposal_only}


def result(i, outcome="proposal", status="complete", good=True, **overrides):
    d = {"id":str(i),"outcome":outcome,"status":status,
         **{f:good for f in FLAGS if f != "unauthorized_effect"},
         "unauthorized_effect":False}
    d.update(overrides)
    return d


def lint_split(records):
    ids = index(records,"duplicate-record")
    memberships = {}
    for x in records:
        need(x["split"] in {"train","dev","test","blind","compositional","unseen"},
             "split")
        for field in ("group","family","normalized_hash"):
            value = x[field]
            need(isinstance(value,str) and value,"group")
            key = (field,value)
            need(key not in memberships or memberships[key] == x["split"],"cross-split")
            memberships[key] = x["split"]
        if x["parent"] is not None:
            need(x["parent"] in ids and ids[x["parent"]]["split"] == x["split"],
                 "parent-split")
    return True


def lint_ledger(data):
    need(data["license_decision"] == "PENDING-OWNER-AND-S5","license-gate")
    ids = set()
    for s in data["sources"]:
        need(s["source_id"] not in ids,"source-id")
        ids.add(s["source_id"])
        need(s["rights_status"] in {"UNKNOWN","NOT VERIFIED"} and
             s["training_allowed"] is False and s["distribution_allowed"] is False and
             s["decision"] == "HOLD","rights-gate")
        need((s["hash"] is None) == (s["hash_type"] is None) and
             (s["hash"] is None) == (s["version"] is None),"provenance")
    return True


def need_subset(actual, expected):
    for k,v in expected.items():
        if type(v) is float:
            need(type(actual[k]) in (int,float) and math.isclose(actual[k],v,abs_tol=1e-12),"metric")
        else:
            need(actual[k] == v,"metric")


def main():
    fixture = json.loads((Path(__file__).with_name("metric-vectors-v1.json")).read_text())
    checks = []
    def check(name, expected, fn):
        actual = "ok"
        try:
            fn()
        except Reject as exc:
            actual = str(exc)
        checks.append((name,actual == expected))
        print(f"{'PASS' if actual == expected else 'FAIL'} {name}: {actual} expected {expected}")
    s100 = [row(i) for i in range(100)]
    for v in fixture["metric_vectors"]:
        cases = [row(i, proposal_only=v.get("all_pss",False)) for i in range(v["n"])]
        results = [result(i,good=i < v["correct"]) if i < v["accepted"] else
                   result(i,outcome="clarify",good=False) for i in range(v["n"])]
        check(v["id"],"ok",lambda:need_subset(score(cases,results,"BLOCKED"),v["expected"]))
    check("missing","case-set",lambda:score(s100,[result(i) for i in range(99)],"BLOCKED"))
    check("duplicate-result","duplicate-result",lambda:score(s100,[result(i) for i in range(99)]+[result(98)],"BLOCKED"))
    check("duplicate-manifest","duplicate-manifest",lambda:score([row(0),row(0)],[result(0)],"BLOCKED"))
    check("unregistered","case-set",lambda:score([row(0)],[result(1)],"BLOCKED"))
    check("timeout","ok",lambda:need_subset(score([row(0)],[result(0,status="timeout")],"BLOCKED"),
          {"js":0.,"jia_resolved":0.,"coverage":0.}))
    check("invalid-ir","ok",lambda:need_subset(score([row(0)],[result(0,status="invalid")],"BLOCKED"),
          {"js":0.,"jia_raw":0.}))
    check("unsafe-proposal","ok",lambda:need_subset(score([row(0)],[result(0,unauthorized_effect=True)],"BLOCKED"),
          {"js":0.,"coverage":1.,"unauthorized_effects":1}))
    check("raw-v-resolved","ok",lambda:need_subset(score([row(0)],[result(0,raw_correct=False)],"BLOCKED"),
          {"jia_raw":0.,"jia_resolved":1.}))
    suites = [row(0),row(1,"ambiguity","clarify"),row(2,"ood","unsupported"),
              row(3,"security","deny"),row(4,"executable")]
    rs = [result(0,outcome="clarify",good=False),result(1,outcome="clarify"),
          result(2,outcome="unsupported"),result(3,outcome="deny")]
    check("suite-denominators","ok",lambda:need_subset(score(suites,rs,"BLOCKED"),
          {"js":0.,"ambiguity_recall":1.,"ood_recall":1.,"clarification_precision":.5,
           "security_expected":1.,"fes_status":"NOT RUN","fes":None}))
    check("fes-blocked-cannot-substitute","case-set",lambda:score(suites,rs+[result(4)],"BLOCKED"))
    check("fes-fixture-failure","ok",lambda:need_subset(score(suites,rs+[result(4,status="timeout")],"SYNTHETIC-VERIFIED"),
          {"fes":0.,"fes_status":"SYNTHETIC ONLY"}))
    check("wilson-270-of-300","ok",lambda:need(.86 < wilson(270,300)[0] < .87 and
          .92 < wilson(270,300)[1] < .94,"interval"))
    check("wilson-invalid","interval-count",lambda:wilson(11,10))
    check("cluster-perfect","ok",lambda:need(cluster_interval([(2,2),(4,4)]) == (1.,1.),"interval"))
    check("cluster-deterministic","ok",lambda:need(cluster_interval([(0,2),(4,4)]) ==
          cluster_interval([(0,2),(4,4)]),"interval"))
    rec = fixture["split_records"]
    check("grouped-split","ok",lambda:lint_split(rec))
    for m in fixture["split_mutations"]:
        import copy
        x = copy.deepcopy(rec)
        x[m["index"]][m["field"]] = m["value"]
        check(m["id"],m["expected"],lambda:lint_split(x))
    ledger = json.loads((ROOT/"data/manifests/license-ledger-v1.json").read_text())
    check("license-ledger","ok",lambda:lint_ledger(ledger))
    import copy
    bad_ledger = copy.deepcopy(ledger)
    bad_ledger["sources"][3]["distribution_allowed"] = True
    check("unknown-distribution","rights-gate",lambda:lint_ledger(bad_ledger))
    for s in ledger["sources"]:
        if s["hash_type"] == "git-blob-sha1":
            path = s["uri"].split("/",6)[-1]
            # URI /owner/repo/blob/SHA/path: obtain path after the exact base SHA.
            path = s["uri"].split("/blob/",1)[1].split("/",1)[1]
            raw = (ROOT/path).read_bytes()
            check("blob-"+s["source_id"],"ok",lambda:need(hashlib.sha1(
                b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest() == s["hash"],"source-hash"))
    need(len({n for n,_ in checks}) == len(checks),"duplicate-check")
    total = len(checks)
    passed = sum(ok for _,ok in checks)
    print(f"A7 protocol/metric: {passed}/{total}; training, blind, FES actual NOT RUN")
    return passed != total


if __name__ == "__main__":
    raise SystemExit(main())
