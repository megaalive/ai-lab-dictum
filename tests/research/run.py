"""A7 data-only protocol/metric oracle; no training, corpus or host execution."""
import hashlib
import json
import math
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Z = 1.959963984540054
SUITES = {"supported", "ambiguity", "ood", "security", "executable"}
OUTCOMES = {"proposal", "clarify", "unsupported", "deny", "no-result"}
STATES = {"complete", "timeout", "invalid", "failure"}
FLAGS = ("raw_correct", "resolved_correct", "semantic_correct",
         "policy_correct", "execution_correct", "unauthorized_effect")
CASE_KEYS = {"id", "suite", "expected", "proposal_only"}
RESULT_KEYS = {"id", "status", "outcome", "execution_status", *FLAGS}
EXECUTION_STATES = {"NOT RUN", "COMPLETE", "TIMEOUT", "FAILURE"}
TERMINAL_OUTCOMES = {"proposal", "clarify", "unsupported", "deny"}
PIN = "0ed0b5a378afa4d32ea51c8222d2908ca42f57c5"
INTERNAL_SOURCES = {
    "internal-catalog-a3": "catalog/core/intents-v1.json",
    "internal-fixture-a3": "tests/catalog/fixtures/intent-contracts-v1.json",
    "internal-plan-v3": "plans/drafts/rencana-v3.md",
}



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
    need(type(reps) is int and reps >= 100 and len(groups) > 0 and
         all(type(k) is int and type(n) is int and 0 <= k <= n and n > 0
             for k,n in groups), "cluster-count")
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
    need(type(rows) is list, "record-list")
    out = {}
    for x in rows:
        need(type(x) is dict and type(x.get("id")) is str and
             1 <= len(x["id"]) <= 128, "case-id")
        need(x["id"] not in out, why)
        out[x["id"]] = x
    return out


def score(cases, results, harness):
    need(harness in {"SYNTHETIC-VERIFIED", "BLOCKED"}, "harness")
    manifest = index(cases,"duplicate-manifest")
    actual = index(results,"duplicate-result")
    for x in manifest.values():
        need(set(x) == CASE_KEYS and type(x["suite"]) is str and
             x["suite"] in SUITES and type(x["expected"]) is str and
             x["expected"] in TERMINAL_OUTCOMES and
             type(x["proposal_only"]) is bool, "manifest")
        need(not x["proposal_only"] or x["suite"] == "supported", "manifest")
        if x["suite"] in {"supported", "executable"}:
            need(x["expected"] == "proposal", "manifest")
        if x["suite"] == "ambiguity":
            need(x["expected"] == "clarify", "manifest")
        if x["suite"] == "ood":
            need(x["expected"] in {"unsupported", "deny"}, "manifest")
    needed = {k for k,x in manifest.items() if
              x["suite"] != "executable" or harness == "SYNTHETIC-VERIFIED"}
    need(actual.keys() == needed, "case-set")
    pairs = []
    for key,x in manifest.items():
        if key not in actual:
            continue
        y = actual[key]
        need(set(y) == RESULT_KEYS and type(y["status"]) is str and
             y["status"] in STATES and type(y["outcome"]) is str and
             y["outcome"] in OUTCOMES and type(y["execution_status"]) is str and
             y["execution_status"] in EXECUTION_STATES and
             all(type(y[f]) is bool for f in FLAGS), "result")
        need(y["status"] != "complete" or y["outcome"] in TERMINAL_OUTCOMES,
             "result-state")
        need(not y["execution_correct"] or y["execution_status"] == "COMPLETE",
             "execution-state")
        if x["suite"] != "executable":
            need(y["execution_status"] == "NOT RUN" and not y["execution_correct"],
                 "unexpected-execution")
        pairs.append((x,y))
    def completed(y):
        return y["status"] == "complete"
    def accepted(y):
        return completed(y) and y["outcome"] == "proposal"
    def correct(y):
        return accepted(y) and y["semantic_correct"] and y["policy_correct"] and not y["unauthorized_effect"]
    def expected(x,y):
        return (completed(y) and x["expected"] == y["outcome"] and
                y["semantic_correct"] and y["policy_correct"] and
                not y["unauthorized_effect"])
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
    raw = sum(accepted(y) and y["raw_correct"] for _,y in s)
    resolved = sum(accepted(y) and y["resolved_correct"] for _,y in s)
    pss = sum(correct(y) for _,y in p)
    security_k = sum(expected(x,y) for x,y in security)
    fes_n = sum(x["suite"] == "executable" for x in manifest.values())
    fes_k = None if harness == "BLOCKED" else sum(
        expected(x,y) and y["execution_status"] == "COMPLETE" and y["execution_correct"]
        for x,y in executable)
    counts = {"jia_raw": {"k":raw, "n":len(s)},
              "jia_resolved": {"k":resolved, "n":len(s)},
              "js": {"k":c, "n":len(s)}, "pss": {"k":pss, "n":len(p)},
              "ambiguity_recall": {"k":ac, "n":len(ambiguity)},
              "ood_recall": {"k":oc, "n":len(ood)},
              "security_expected": {"k":security_k, "n":len(security)},
              "fes": {"k":fes_k, "n":fes_n}}
    return {
        "supported_n":len(s),"accepted":a,"correct":c,
        "jia_raw":ratio(raw,len(s)), "jia_resolved":ratio(resolved,len(s)),
        "js":ratio(c,len(s)), "coverage":ratio(a,len(s)),
        "selective_accuracy":ratio(c,a), "selective_risk":ratio(a-c,a),
        "pss_n":len(p),"pss":ratio(pss,len(p)),
        "ambiguity_recall":ratio(ac,len(ambiguity)),"ood_recall":ratio(oc,len(ood)),
        "clarification_precision":ratio(ac,clarify_n),
        "false_abstain":sum(completed(y) and y["outcome"] in {"clarify","unsupported","deny"} for _,y in s),
        "security_expected":ratio(security_k,len(security)),
        "unauthorized_effects":violations,
        "fes_status":"NOT RUN" if harness == "BLOCKED" else "SYNTHETIC ONLY",
        "fes":None if fes_k is None else ratio(fes_k,fes_n),
        "counts":counts,
    }


def row(i, suite="supported", expected="proposal", proposal_only=False):
    return {"id":str(i),"suite":suite,"expected":expected,"proposal_only":proposal_only}


def result(i, outcome="proposal", status="complete", good=True, **overrides):
    d = {"id":str(i),"outcome":outcome,"status":status,
         **{f:good for f in FLAGS if f not in {"unauthorized_effect", "execution_correct"}},
         "unauthorized_effect":False,"execution_correct":False,
         "execution_status":"NOT RUN"}
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
            need(ids[x["parent"]]["group"] == x["group"], "parent-group")
    # Iterative lineage walk: no self-parent or cycle, no recursive traversal.
    finished = set()
    for key in ids:
        current, chain = key, set()
        while current is not None and current not in finished:
            need(current not in chain, "parent-cycle")
            chain.add(current)
            current = ids[current]["parent"]
        finished.update(chain)
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
        if s["source_id"] in INTERNAL_SOURCES:
            path = INTERNAL_SOURCES[s["source_id"]]
            need(s["hash_type"] == "git-blob-sha1" and
                 type(s["hash"]) is str and re.fullmatch(r"[0-9a-f]{40}",s["hash"]) and
                 type(s["version"]) is str and s["version"].endswith("@"+PIN) and
                 s["uri"] == "https://github.com/megaalive/ai-lab-dictum/blob/"+PIN+"/"+path,
                 "source-pin")
        else:
            need(s["hash_type"] is None, "source-pin")
    need(INTERNAL_SOURCES.keys() <= ids,"source-pin")
    return True


def arithmetic_gate(metric, k, n, method, groups=None):
    """Synthetic gate arithmetic only. Not a release/attestation decision."""
    minima = {"jia_resolved":300, "js":300, "pss":100, "fes":100,
              "ood_recall":150, "ambiguity_recall":150}
    need(metric in minima and type(n) is int and n >= 0 and
         (k is None or type(k) is int and 0 <= k <= n), "gate-count")
    need(method in {"wilson-singleton", "cluster-bootstrap"}, "gate-method")
    if k is None:
        return "NOT RUN"
    if n < minima[metric]:
        return "INSUFFICIENT"
    if method == "wilson-singleton":
        need(groups is None, "gate-method")
        lower,_ = wilson(k,n)
    else:
        need(type(groups) is list and all(type(a) is int and type(b) is int and
             0 <= a <= b and b > 0 for a,b in groups) and
             sum(a for a,_ in groups) == k and sum(b for _,b in groups) == n,
             "gate-groups")
        if len(groups) < 30:
            return "INSUFFICIENT"
        lower,_ = cluster_interval(groups)
    point_floor, lower_floor = ((.95,.90) if metric in
        {"ood_recall","ambiguity_recall"} else (.90,.85))
    return "SYNTHETIC-PASS" if k/n >= point_floor and lower >= lower_floor else "SYNTHETIC-FAIL"


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
    check("wrong-clarification-semantics","ok",lambda:need_subset(
          score([row(0,"ambiguity","clarify")],
                [result(0,outcome="clarify",semantic_correct=False)],"BLOCKED"),
          {"ambiguity_recall":0.,"clarification_precision":0.}))
    check("wrong-ood-semantics","ok",lambda:need_subset(
          score([row(0,"ood","unsupported")],
                [result(0,outcome="unsupported",semantic_correct=False)],"BLOCKED"),
          {"ood_recall":0.}))
    check("security-same-enum-wrong-semantics","ok",lambda:need_subset(
          score([row(0,"security","proposal")],
                [result(0,semantic_correct=False)],"BLOCKED"),
          {"security_expected":0.}))
    check("blocked-fes-denominator","ok",lambda:need(
          score(suites,rs,"BLOCKED")["counts"]["fes"] == {"k":None,"n":1},"metric"))
    check("fes-not-run-is-failure-in-verified-suite","ok",lambda:need_subset(
          score(suites,rs+[result(4)],"SYNTHETIC-VERIFIED"), {"fes":0.}))
    check("fes-completed-fixture","ok",lambda:need_subset(
          score(suites,rs+[result(4,execution_status="COMPLETE",execution_correct=True)],
                "SYNTHETIC-VERIFIED"),{"fes":1.}))
    check("fes-forged-correct","execution-state",lambda:score(
          suites,rs+[result(4,execution_correct=True)],"SYNTHETIC-VERIFIED"))
    check("unexpected-execution","unexpected-execution",lambda:score(
          [row(0)],[result(0,execution_status="COMPLETE")],"BLOCKED"))
    check("complete-no-result","result-state",lambda:score(
          [row(0)],[result(0,outcome="no-result")],"BLOCKED"))
    check("unknown-result-field","result",lambda:score(
          [row(0)],[result(0,approval=True)],"BLOCKED"))
    check("manifest-terminal-invalid","manifest",lambda:score(
          [row(0,"security","no-result")],[result(0)],"BLOCKED"))
    check("gate-minimum","ok",lambda:need(
          arithmetic_gate("js",299,299,"wilson-singleton") == "INSUFFICIENT","gate"))
    check("gate-not-run","ok",lambda:need(
          arithmetic_gate("fes",None,100,"wilson-singleton") == "NOT RUN","gate"))
    check("gate-270-of-300","ok",lambda:need(
          arithmetic_gate("js",270,300,"wilson-singleton") == "SYNTHETIC-PASS","gate"))
    check("gate-point-pass-ci-fail","ok",lambda:need(
          arithmetic_gate("pss",90,100,"wilson-singleton") == "SYNTHETIC-FAIL","gate"))
    check("gate-point-fail","ok",lambda:need(
          arithmetic_gate("js",269,300,"wilson-singleton") == "SYNTHETIC-FAIL","gate"))
    check("gate-cluster-minimum","ok",lambda:need(
          arithmetic_gate("js",300,300,"cluster-bootstrap",[(300,300)]) == "INSUFFICIENT","gate"))
    check("gate-cluster-count-mismatch","gate-groups",lambda:
          arithmetic_gate("js",300,300,"cluster-bootstrap",[(9,10)]*30))
    check("gate-cluster-perfect-synthetic","ok",lambda:need(
          arithmetic_gate("js",300,300,"cluster-bootstrap",[(10,10)]*30) ==
          "SYNTHETIC-PASS","gate"))
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
    cycle = [dict(x) for x in rec]
    cycle[0]["parent"] = cycle[1]["id"]
    check("lineage-cycle","parent-cycle",lambda:lint_split(cycle))
    self_parent = [dict(x) for x in rec]
    self_parent[0]["parent"] = self_parent[0]["id"]
    check("lineage-self","parent-cycle",lambda:lint_split(self_parent))
    ledger = json.loads((ROOT/"data/manifests/license-ledger-v1.json").read_text())
    check("license-ledger","ok",lambda:lint_ledger(ledger))
    import copy
    bad_ledger = copy.deepcopy(ledger)
    bad_ledger["sources"][3]["distribution_allowed"] = True
    check("unknown-distribution","rights-gate",lambda:lint_ledger(bad_ledger))
    bad_uri = copy.deepcopy(ledger)
    bad_uri["sources"][0]["uri"] = "https://github.com/megaalive/ai-lab-dictum/blob/"+PIN+"/../../outside"
    check("ledger-path-substitution","source-pin",lambda:lint_ledger(bad_uri))
    # File paths are selected from a fixed local map, never from ledger URI text.
    for s in ledger["sources"]:
        if s["source_id"] in INTERNAL_SOURCES:
            raw = (ROOT/INTERNAL_SOURCES[s["source_id"]]).read_bytes()
            check("blob-"+s["source_id"],"ok",lambda:need(hashlib.sha1(
                b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest() == s["hash"],"source-hash"))
    need(len({n for n,_ in checks}) == len(checks),"duplicate-check")
    total = len(checks)
    passed = sum(ok for _,ok in checks)
    print(f"A7 protocol/metric: {passed}/{total}; training, blind, FES actual NOT RUN")
    return passed != total


if __name__ == "__main__":
    raise SystemExit(main())
