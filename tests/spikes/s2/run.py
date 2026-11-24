"""S2 data-only B0 and B1 development experiment; no model or product IR."""
import hashlib
import json
import math
import re
import resource
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RULES = [
 ("memory.summary", r"\b(?:ram|memori|memory)\b"),
 ("network.listener.lookup", r"\b(?:port|listener|listening|socket)\b"),
 ("service.failed.list", r"\b(?:gagal|failed)\b"),
 ("log.service.query", r"\b(?:log|logs|jurnal|journal|catatan)\b"),
 ("storage.filesystem.usage", r"\b(?:filesystem|sistem berkas|disk|partisi)\b"),
 ("storage.directory.usage", r"\b(?:direktori|folder|directories|directory|folders)\b"),
 ("file.search", r"\b(?:cari|temukan|find|locate)\b.*\b(?:file|files|berkas)\b"),
 ("service.restart", r"\b(?:restart|restarting|mulai ulang)\b"),
]
INTENTS = [x[0] for x in RULES]
REFUSAL = re.compile(r"\b(?:hapus|delete|execute|jalankan|sudo|remote|ping|dns|weather|cuaca)\b",re.I)
AMBIGUITY = re.compile(r"\b(?:jangan|don't|do not|since boot|sejak boot)\b",re.I)
ROOT_PATTERN = r'(?:"(/fixture/[^"\r\n]+)"|(/fixture/[\w./-]+))'
UNIT_PATTERN = r"(?<![\w.-])([A-Za-z0-9][A-Za-z0-9_.@-]*\.service)\b"
FIXED_END = 1760000600


def t(kind,v):
    return {"kind":kind,"value":v}


def only(pattern,text,flags=re.I):
    results = re.findall(pattern,text,flags)
    if len(results)>1:
        raise ValueError("ambiguous-slot")
    return results[0] if results else None


def integer(pattern,text,default,lo,hi):
    value = only(pattern,text)
    n = default if value is None else int(value)
    if n is None or not lo<=n<=hi:
        raise ValueError("integer-slot")
    return n


def path(text):
    hit = only(ROOT_PATTERN,text,0)
    if hit is None:
        raise ValueError("root-required")
    v = hit[0] or hit[1]
    if not v.startswith("/fixture/") or any(x in {"",".",".."} for x in v[1:].split("/")):
        raise ValueError("root-outside-fixture")
    return v


def slots(intent,text):
    result = {}
    if intent == "network.listener.lookup":
        result["port"] = t("port",integer(r"\bport\s+(\d+)\b",text,None,1,65535))
        protocol = only(r"\b(tcp|udp)\b",text) or "tcp"
        result["protocol"] = t("protocol",protocol.lower())
    elif intent in {"service.restart","log.service.query"}:
        unit = only(UNIT_PATTERN,text,0)
        if unit is None:
            raise ValueError("unit-required")
        result["unit"] = t("unit-name",unit)
        if intent == "log.service.query":
            mins = integer(r"\b(\d+)\s*(?:menit|minutes?)\b",text,None,1,1440)
            result["window"] = {"kind":"time-window","start_unix_s":FIXED_END-mins*60,
                                "end_unix_s":FIXED_END}
            result["limit"] = t("positive-int",integer(r"\blimit\s+(\d+)\b",text,30,1,100))
    elif intent in {"storage.directory.usage","file.search"}:
        result["root"] = t("path",path(text))
        if intent == "storage.directory.usage":
            numbers = re.findall(r"\b(?:top|limit)\s+(\d+)\b|\b(\d+)\s+direktori\b",text,re.I)
            if len(numbers)>1:
                raise ValueError("ambiguous-limit")
            limit = int(numbers[0][0] or numbers[0][1]) if numbers else 5
            if not 1<=limit<=100:
                raise ValueError("limit-bound")
            result["limit"] = t("positive-int",limit)
        else:
            ext = only(r"\b(?:ekstensi|extension)\s+([A-Za-z0-9]{1,16})\b",text)
            name = only(r"\b(?:nama|named)\s+([A-Za-z0-9_.-]{1,128})\b",text)
            if ext is None and name is None:
                raise ValueError("filter-required")
            if ext is not None:
                result["extension"] = t("extension",ext)
            if name is not None:
                result["filename"] = t("filename",name)
            result["limit"] = t("positive-int",integer(r"\blimit\s+(\d+)\b",text,30,1,100))
        result["depth"] = t("depth",integer(r"\bdepth\s+(\d+)\b",text,3,1,8))
    return result


def rule_rank(text):
    hits = [intent for intent,pattern in RULES if re.search(pattern,text,re.I)]
    # File-search vs directory terms may co-occur; multiple intents remain ambiguous.
    return hits[0] if len(hits)==1 else None


def features(text):
    # Ranking only, never alter original slot bytes.
    words = re.findall(r"\w+",text.casefold())
    norm = " ".join(words)
    return Counter(["w:"+x for x in words]+["g:"+norm[i:i+3] for i in range(max(0,len(norm)-2))])


class Retrieval:
    """TF-IDF word + character trigram cosine, references only."""
    def __init__(self,refs):
        self.docs = []
        counts = Counter()
        features_list = [features(x["text"]) for x in refs]
        for f in features_list:
            counts.update(f.keys())
        self.idf = {k:math.log((1+len(refs))/(1+n))+1 for k,n in counts.items()}
        for x,f in zip(refs,features_list):
            self.docs.append((x["intent"],x["id"],self.weight(f)))

    def weight(self,f):
        v = {k:n*self.idf[k] for k,n in f.items() if k in self.idf}
        norm = math.sqrt(sum(n*n for n in v.values()))
        return {k:n/norm for k,n in v.items()} if norm else {}

    def rank(self,text):
        q = self.weight(features(text))
        scores = defaultdict(float)
        for intent,_,v in self.docs:
            score = sum(q.get(k,0.)*n for k,n in v.items())
            scores[intent] = max(scores[intent],score)
        ranks = sorted(scores.items(),key=lambda x:(-x[1],x[0]))
        # Fixed prior to results. No dev threshold tuning.
        if not ranks or ranks[0][1] < .12:
            return None
        return ranks[0][0]


def predict(text,rank):
    if AMBIGUITY.search(text):
        return {"status":"clarify"}
    if REFUSAL.search(text):
        return {"status":"unsupported"}
    intent = rank(text)
    if intent is None:
        return {"status":"unsupported"}
    try:
        return {"status":"candidate","intent":intent,"slots":slots(intent,text)}
    except (ValueError,TypeError):
        return {"status":"clarify"}


def safe_manifest(data):
    refs,dev = data["reference"],data["development"]
    assert len(refs)==32 and len(dev)==100
    assert len({x["id"] for x in refs+dev})==132
    assert len({x["group"] for x in dev})==100
    assert len({x["text"].casefold().strip() for x in refs+dev})==132
    assert Counter(x["intent"] for x in refs)=={i:4 for i in INTENTS}
    assert Counter(x["expected"]["status"] for x in dev)=={"candidate":80,"clarify":10,"unsupported":10}
    assert Counter(x["expected"]["intent"] for x in dev if x["expected"]["status"]=="candidate")=={i:10 for i in INTENTS}
    catalog = json.loads((ROOT/"catalog/core/intents-v1.json").read_text())
    registry = {i["id"]:i for i in catalog["intents"] if i["skeleton"]}
    assert set(registry)==set(INTENTS)
    for row in dev:
        expected = row["expected"]
        if expected["status"]!="candidate":
            assert set(expected)=={"status"}
            continue
        spec = {s["name"]:s for s in registry[expected["intent"]]["slots"]}
        assert set(expected["slots"])<=spec.keys()
        assert all(not s["required"] or name in expected["slots"] for name,s in spec.items())
        for name,value in expected["slots"].items():
            s = spec[name]
            assert value["kind"]==s["kind"]
            if s["minimum"] is not None:
                assert s["minimum"]<=value["value"]<=s["maximum"]
    return refs,dev


def run(name,rank,dev):
    start = time.perf_counter_ns()
    results = [(row,predict(row["text"],rank)) for row in dev]
    elapsed = time.perf_counter_ns()-start
    supported = [(r,p) for r,p in results if r["expected"]["status"]=="candidate"]
    accepted = [(r,p) for r,p in supported if p["status"]=="candidate"]
    intent_correct = sum(p.get("intent")==r["expected"]["intent"] for r,p in supported)
    joint_correct = sum(p==r["expected"] for r,p in supported)
    confusion = defaultdict(Counter)
    errors = Counter()
    langs = defaultdict(lambda:[0,0])
    for row,p in supported:
        e = row["expected"]
        confusion[e["intent"]][p.get("intent",p["status"])]+=1
        langs[row["language"]][0]+=1
        langs[row["language"]][1]+=int(p==e)
        if p!=e:
            if p.get("intent")!=e["intent"]:
                errors["intent-or-abstention"]+=1
            else:
                for k in set(p["slots"])|set(e["slots"]):
                    if p["slots"].get(k)!=e["slots"].get(k):
                        errors[k]+=1
    timing = []
    for _ in range(20):
        for row in dev:
            t0 = time.perf_counter_ns()
            predict(row["text"],rank)
            timing.append((time.perf_counter_ns()-t0)/1000)
    timing.sort()
    result = {"model":name,"supported":len(supported),"accepted":len(accepted),
              "intent_correct":intent_correct,"prototype_joint_slot_correct":joint_correct,
              "coverage":len(accepted)/len(supported),
              "selective_joint_accuracy":joint_correct/len(accepted) if accepted else None,
              "clarify_correct":sum(p==r["expected"] for r,p in results if r["expected"]["status"]=="clarify"),
              "ood_correct":sum(p==r["expected"] for r,p in results if r["expected"]["status"]=="unsupported"),
              "confusion":dict(confusion),"slot_errors":dict(errors),"language_counts":dict(langs),
              "first_pass_ms":elapsed/1e6,"warm_p50_us":statistics.median(timing),
              "warm_p95_us":timing[math.ceil(.95*len(timing))-1],
              "timing_n":len(timing),"peak_rss_process_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    print("S2_RESULT "+json.dumps(result,sort_keys=True),flush=True)
    # Keep every incorrect ID and error class, never suppress denominator failures.
    for row,p in results:
        if p!=row["expected"]:
            print("S2_ERROR "+json.dumps({"model":name,"id":row["id"],"expected":row["expected"],"actual":p},ensure_ascii=True,sort_keys=True))


def main():
    raw = (HERE/"development-v1.json").read_bytes()
    data = json.loads(raw)
    refs,dev = safe_manifest(data)
    print("S2 corpus_sha256="+hashlib.sha256(raw).hexdigest()+" refs=32 dev=100 (80/10/10)")
    run("B0-rules",rule_rank,dev)
    b1 = Retrieval(refs)
    run("B1-tfidf",b1.rank,dev)
    print("S2 COMPLETE development-only; JS/PSS/FES, policy/renderer, native C-01..C-10, blind and training NOT RUN")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
