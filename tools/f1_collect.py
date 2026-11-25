"""Prepare human author/reviewer worksheets and assemble a private seed request.

No generated utterances, auto-labeling, approval, training, model invocation,
network access or blind records. The mechanics do not attest human authorship
or legal rights. All actual decisions must come from the responsible people.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from f1_corpus import ROOT, Reject, need, sha, encoded, normalize
from f1_seed import (MAX_PACKET, ID, SHA, SUITES, check_row, exact_text, keys, load_contract,
                     match, parse, read_regression_texts, source_digest)

AUTHOR_FIELDS={"id","revision","text","language","dominant_language","semantic_group","family",
               "parent","source_id","source_version","author"}
REVIEW_FIELDS={"id","author_row_sha256","text","reviewer","decision","decision_ref","evidence_sha256",
               "sensitive_data","adjudicated","reason_code","fixture_id","expected","slot_sources","tags"}

def collection_plan(contract):
    """300 assignment cards, not a corpus; do not show grammar/gold to authors."""
    rows=[]
    # Opaque assignment IDs avoid revealing ordinal/suite to the reviewer.
    def task_id(key):
        return "F1-"+sha(("f1-collection-v1/"+key).encode())[:24]
    for index,(intent,c) in enumerate(contract["catalog"].items()):
        for j in range(5):
            lang="id" if j<3+index%2 else "en"
            rows.append({"id":task_id(f"{intent}/{j}"),"target_suite":"supported",
                         "target_language":lang,"intent":intent,"goal":c["description"][lang],
                         "fixture_id":c["fixture_id"]})
    negative_goals={
        "ambiguity":{"id":"Tulis kebutuhan dengan target atau maksud yang belum jelas.",
                     "en":"Write an incomplete or genuinely ambiguous request."},
        "ood":{"id":"Tulis kebutuhan yang berada di luar katalog atau cakupan sintetis.",
               "en":"Write a request outside the catalog or synthetic scope."},
        "security":{"id":"Tulis contoh kontras kebijakan sintetis yang harus ditolak; tanpa rahasia, target nyata atau langkah eksploitasi.",
                    "en":"Write a synthetic policy-denial contrast; no secrets, real targets or exploitation steps."}}
    for suite,goals in negative_goals.items():
        for j in range(20):
            lang="id" if j%10<7 else "en"
            rows.append({"id":task_id(f"{suite}/{j}"),"target_suite":suite,
                         "target_language":lang,"intent":None,"goal":goals[lang],"fixture_id":None})
    need(len(rows)==len({r["id"] for r in rows})==300,"plan")
    return {"schema_version":1,"role":"AUTHOR-ASSIGNMENTS-NOT-DATASET","identities":contract["identities"],
            "assignments":rows,"language_target":{"id":210,"en":90},"human_gold_count":0}

def author_blank(i):
    return {"id":i,"revision":1,"text":"","language":None,"dominant_language":None,
            "semantic_group":None,"family":None,"parent":None,"source_id":None,
            "source_version":None,"author":None}

def author_packet(plan):
    return {"schema_version":1,"role":"HUMAN-AUTHOR-DRAFTS","assignment_sha256":sha(encoded(plan)),
            "records":[author_blank(t["id"]) for t in plan["assignments"]]}

def author_rows(packet,plan):
    keys(packet,{"schema_version","role","assignment_sha256","records"},"author-packet")
    need(type(packet["schema_version"]) is int and packet["schema_version"]==1 and
         packet["role"]=="HUMAN-AUTHOR-DRAFTS" and packet["assignment_sha256"]==sha(encoded(plan)),
         "author-identity")
    allowed={t["id"] for t in plan["assignments"]}
    seen=set()
    out=[]
    skipped=[]
    need(type(packet["records"]) is list and len(packet["records"])==len(allowed),"author-count")
    for r in packet["records"]:
        keys(r,AUTHOR_FIELDS,"author-row")
        i=r["id"]
        need(i in allowed and i not in seen,"author-id")
        seen.add(i)
        if r==author_blank(i):
            skipped.append(i)
            continue
        need(type(r["revision"]) is int and r["revision"]>=1,"author-revision")
        raw=exact_text(r["text"])
        need(bool(normalize(r["text"])) and len(raw)<=4096,"author-text")
        for k in ("semantic_group","family","source_id","source_version","author"):
            need(match(r[k],ID),"author-field")
        need(r["parent"] is None or match(r["parent"],ID),"parent")
        need(r["language"] in {"id","en","mixed"} and
             (r["dominant_language"] in {"id","en"} if r["language"]=="mixed" else
              r["dominant_language"] is None),"author-language")
        out.append(r)
    need(seen==allowed,"author-coverage")
    return sorted(out,key=lambda x:x["id"]),sorted(skipped)

def review_sheet(author,plan):
    rows,skipped=author_rows(author,plan)
    need(bool(rows),"author-empty")
    # Reviewer receives exact text and row hash, not assignment hints or model
    # labels. Author pseudonym is available separately for conflict checks.
    return {"schema_version":1,"role":"HUMAN-REVIEW-WORKSHEET",
            "author_packet_sha256":sha(encoded(author)),"skipped_assignment_ids":skipped,
            "records":[{"id":r["id"],"author_row_sha256":sha(encoded(r)),"text":r["text"],
                        "reviewer":None,"decision":"PENDING","decision_ref":None,"evidence_sha256":None,
                        "sensitive_data":None,"adjudicated":None,"reason_code":None,"fixture_id":None,
                        "expected":None,"slot_sources":None,"tags":None} for r in rows]}

def assemble(author,review,plan,contract,*,mechanical=False,regression=None):
    rows,skipped=author_rows(author,plan)
    need(bool(rows),"author-empty")
    keys(review,{"schema_version","role","author_packet_sha256","skipped_assignment_ids","records"},"review-packet")
    need(type(review["schema_version"]) is int and review["schema_version"]==1 and
         review["role"]=="HUMAN-REVIEW-WORKSHEET" and
         review["author_packet_sha256"]==sha(encoded(author)) and review["skipped_assignment_ids"]==skipped,
         "review-identity")
    by_id={r["id"]:r for r in rows}
    need(type(review["records"]) is list and len(review["records"])==len(rows),"review-count")
    seen=set()
    accepted=[]
    rejects=[]
    sources={}
    source_meta={}
    for r in review["records"]:
        keys(r,REVIEW_FIELDS,"review-row")
        i=r["id"]
        need(i in by_id and i not in seen,"review-id")
        seen.add(i)
        draft=by_id[i]
        need(r["author_row_sha256"]==sha(encoded(draft)) and r["text"]==draft["text"],"review-drift")
        need(match(r["reviewer"],ID) and r["reviewer"]!=draft["author"] and
             match(r["decision_ref"],ID) and match(r["evidence_sha256"],SHA) and
             match(r["reason_code"],ID) and r["adjudicated"] is True and
             type(r["sensitive_data"]) is bool,"review-decision")
        need(r["decision"] in {"ACCEPTED","REJECTED"},"review-pending")
        if r["decision"]=="REJECTED":
            need(all(r[k] is None for k in ("fixture_id","expected","slot_sources","tags")),"rejected-label")
            rejects.append({"id":i,"author_row_sha256":r["author_row_sha256"],"reason_code":r["reason_code"],
                            "decision_ref":r["decision_ref"],"review_evidence_sha256":r["evidence_sha256"]})
            continue
        need(r["sensitive_data"] is False,"accepted-sensitive")
        source=draft["source_id"]
        meta=(draft["source_version"],draft["author"])
        need(source_meta.setdefault(source,meta)==meta,"source-author-version")
        sources.setdefault(source,[])
        rec={**draft,"role":"MECHANICAL-TEST" if mechanical else "HUMAN-DEVELOPMENT-SEED",
             "derivation":"MECHANICAL-TEST" if mechanical else "HUMAN-AUTHORED",
             "text_sha256":sha(draft["text"].encode()),"normalized_sha256":sha(normalize(draft["text"]).encode()),
             "fixture_id":r["fixture_id"],"expected":r["expected"],"slot_sources":r["slot_sources"],"tags":r["tags"],
             "review":{k:r[k] for k in ("reviewer","decision_ref","evidence_sha256","decision","sensitive_data","adjudicated")}}
        accepted.append(rec)
        sources[source].append(rec)
    need(seen==set(by_id),"review-coverage")
    need((1 if mechanical else 200)<=len(accepted)<=500,"accepted-count")
    # Validate reviewed labels using the actual candidate contract without
    # constructing an affirmative rights record. Do not use model predictions.
    source_map={i:{"version":v[0]} for i,v in source_meta.items()}
    if regression is None:
        regression=read_regression_texts()
    supported=set()
    suites=Counter()
    language=Counter()
    ids={r["id"] for r in accepted}
    for rec in accepted:
        _,_,suite=check_row(rec,contract,source_map,mechanical)
        n=normalize(rec["text"])
        # Candidate validator repeats exact/fuzzy checks after external approval.
        need(n not in regression,"visible-exact-contamination")
        need(rec["parent"] is None or rec["parent"] in ids,"accepted-parent")
        suites[suite]+=1
        language[rec["language"]]+=1
        if suite=="supported":
            supported.add(rec["expected"]["intent"])
    if not mechanical:
        need(supported==set(contract["catalog"]) and set(suites)==SUITES,"reviewed-coverage")
        need(set(language)>={"id","en"},"reviewed-language")
    seed={"schema_version":1,"role":"MECHANICAL-TEST" if mechanical else "PRIVATE-HUMAN-DEVELOPMENT-SEED",
          "records":sorted(accepted,key=lambda x:x["id"])}
    seed_bytes=encoded(seed)+b"\n"
    request={"schema_version":1,"role":"RIGHTS-REVIEW-REQUEST-NOT-APPROVAL",
             "seed_sha256":sha(seed_bytes),"sources":[{"id":i,"version":source_meta[i][0],
                 "record_set_sha256":source_digest(sources[i]),"origin":"MECHANICAL-TEST" if mechanical else
                 "ORIGINAL-HUMAN-CONTRIBUTION","attribution":source_meta[i][1],
                 "rights_decision_ref":None} for i in sorted(sources)],
             "owner_decision_ref":None,"allow_development_fit":False,
             "allow_development_evaluation":False,"allow_distribution":False,"blind":False}
    audit={"role":"COLLECTION-MECHANICS-ONLY" if mechanical else "PRIVATE-COLLECTION-REVIEW-RECORD",
           "author_packet_sha256":sha(encoded(author)),"review_packet_sha256":sha(encoded(review)),
           "assignment_sha256":sha(encoded(plan)),"seed_sha256":sha(seed_bytes),"accepted_count":len(accepted),
           "rejected_count":len(rejects),"skipped_assignment_ids":skipped,"rejected":sorted(rejects,key=lambda x:x["id"]),
           "suite_counts":dict(suites),"language_counts":dict(language),"supported_intents":len(supported),
           "rights":"HOLD","review_identity_attested_by_tool":False,"training":"NOT RUN","blind":"NOT RUN"}
    return seed_bytes,request,audit

def reference(contract):
    return {"role":"SEMANTIC-REFERENCE-NOT-GOLD","identities":contract["identities"],
            "reference_unix_s":1760000600,"scope":contract["scope"],
            "typed_domains":contract["domains"]["scope"],"utility_options":contract["domains"]["utility_options"],
            "max_window_seconds":contract["max_window_seconds"],
            "intents":[{k:c[k] for k in ("id","ordinal","description","slots","slot_constraints","effect","fixture_id","operation_surface")}
                       for c in contract["catalog"].values()],"execution_allowed":False}

def private(path):
    p=Path(path).resolve()
    need(not p.is_relative_to(ROOT.resolve()),"private-path")
    return p

def read(path):
    with private(path).open("rb") as f:
        return parse(f.read(MAX_PACKET+1))

def write(path,obj):
    with path.open("xb") as f:
        f.write(obj if type(obj) is bytes else encoded(obj)+b"\n")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    x=sub.add_parser("init")
    x.add_argument("--output",required=True)
    x=sub.add_parser("review-sheet")
    for field in ("author","output"):
        x.add_argument("--"+field,required=True)
    x=sub.add_parser("assemble")
    for field in ("author","review","output"):
        x.add_argument("--"+field,required=True)
    a=parser.parse_args()
    try:
        contract=load_contract()
        plan=collection_plan(contract)
        out=private(a.output)
        if a.action=="init":
            out.mkdir(exist_ok=False)
            write(out/"assignments.json",plan)
            write(out/"author-drafts.json",author_packet(plan))
            write(out/"semantic-reference.json",reference(contract))
            summary={"status":"EMPTY-AUTHOR-PACK","assignments":300,"human_gold_count":0}
        elif a.action=="review-sheet":
            sheet=review_sheet(read(a.author),plan)
            write(out,sheet)
            summary={"status":"REVIEW-WORKSHEET-PENDING","records":len(sheet["records"]),
                     "skipped":len(sheet["skipped_assignment_ids"])}
        else:
            seed,request,audit=assemble(read(a.author),read(a.review),plan,contract)
            out.mkdir(exist_ok=False)
            write(out/"seed.json",seed)
            write(out/"rights-review-request.json",request)
            write(out/"collection-audit.json",audit)
            summary={"status":"RIGHTS-REVIEW-REQUIRED","seed_sha256":sha(seed),
                     "accepted":audit["accepted_count"],"rejected":audit["rejected_count"],
                     "supported_intents":audit["supported_intents"],"training":"NOT RUN"}
        print(json.dumps(summary,sort_keys=True))
    except (Reject,ValueError,TypeError,KeyError,OSError,RecursionError):
        raise SystemExit("F1 collection rejected (sanitized); preserve private originals") from None

if __name__=="__main__":
    main()
