"""Standalone F1 candidate values. No OS probes, DNS, I/O to targets or IR cast.

Only repository-pinned development contract; v1 native pipeline does not
consume this module or its value kinds. A valid value is not authority.
"""
import hashlib
import ipaddress
import json
import re
import unicodedata
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "spec/catalog/f1-slot-domains-v1.json"
SCHEMA = ROOT / "spec/catalog/f1-slot-candidate-v2.schema.json"


class Reject(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise Reject(code)


def load():
    contract = json.loads(CONTRACT.read_bytes())
    schema = json.loads(SCHEMA.read_bytes())
    Draft202012Validator.check_schema(schema)
    need(contract["status"] == "DEVELOPMENT_ONLY_NOT_INTEGRATED" and
         contract["candidate_value_version"] == 2 and contract["schema_version"] == 1 and
         contract["execution_allowed"] is False and contract["copyable"] is False and
         contract["compatibility"] == "NOT VERIFIED", "authority")
    for path, digest in contract["source_git_blobs"].items():
        data = (ROOT / path).read_bytes()
        actual = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        need(actual == digest, "source-pin")
    registry = json.loads((ROOT/"catalog/core/intents-v1.json").read_bytes())["intents"]
    profile = json.loads((ROOT/"catalog/debian-13/v1.json").read_bytes())
    need(len(registry)==48 and len(profile["bindings"])==48 and
         all(not x["execute_eligible"] for x in registry) and
         all(x["capability_status"]=="BLOCKED" and x["compatibility"]=="NOT VERIFIED"
             for x in profile["bindings"]), "authority")
    deferred = {(r["id"],s["name"]):s["required"] for r in registry for s in r["deferred_slots"]}
    rows = contract["deferred"]
    need(len(rows)==10 and len({x["intent"] for x in rows})==9 and
         len({(x["intent"],x["slot"]) for x in rows})==10 and
         {(x["intent"],x["slot"]):x["required"] for x in rows}==deferred and
         all(x["default"] is None for x in rows), "deferred-coverage")
    need(contract["additional"] == [{"intent":"network.dns.lookup","slot":"record_type",
         "kind":"dns-record-type","required":True,
         "default":{"kind":"dns-record-type","value":"A"},"provenance":"catalog-default"}],
         "dns-default")
    need(set(contract["narrative_only"])=={r["id"] for r in registry
         if r["operation_surface"]=="narrative-only"}, "narrative-surface")
    need(contract["max_window_seconds"] == {"log.service.query":86400,
         "log.system.errors":86400,"file.search":86400}, "window-bounds")
    kinds = {x["properties"]["kind"]["const"] for x in schema["oneOf"]}
    need(len(kinds)==len(schema["oneOf"])==11 and
         kinds==set(contract["scope"])=={x["kind"] for x in rows+contract["additional"]},
         "kind-coverage")
    return contract, Draft202012Validator(schema)


def scalar_text(value, max_bytes):
    try:
        size = len(value.encode("utf-8", "strict"))
    except UnicodeEncodeError:
        raise Reject("scalar") from None
    need(1 <= size <= max_bytes, "bytes")
    need(value == value.strip(), "outer-space")
    for c in value:
        cp = ord(c)
        need(unicodedata.category(c) not in {"Cc","Cf","Cs","Zl","Zp"} and
             not (0xfdd0 <= cp <= 0xfdef or (cp & 0xffff) in {0xfffe,0xffff}), "scalar")


def dns_name(value):
    labels=value.split(".")
    need(len(labels)>=2 and len(value)<=253 and
         all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", x)
             for x in labels), "dns-syntax")
    need(any(c.isalpha() for c in labels[-1]), "dns-syntax")


def validate_value(value, contract, validator):
    need(validator.is_valid(value), "shape")
    k,v=value["kind"],value["value"]
    scalar_text(v,{"literal-text":256,"process-name":64,"package-query":128,
                   "package-id":128}.get(k,255))
    if k=="dns-name":
        dns_name(v)
    elif k=="network-target":
        try:
            parsed=ipaddress.ip_address(v)
        except ValueError:
            dns_name(v)
        else:
            need(str(parsed)==v and "%" not in v, "ip-canonical")
    elif k in {"process-name","package-query"}:
        need(not v.startswith(("-", "@", "+")), "option-like")
    # Literal text is data, never regex/flag/command. For all kinds, exact
    # authored synthetic values only, no arbitrary user data projected.
    need(v in contract["scope"][k], "fixture-scope")


def validate_slots(intent, values, contract, validator):
    """No fallback, normalization or invented provenance. Caller supplies
    explicit typed values. A catalog default is inserted only for DNS A."""
    rules={x["slot"]:x for x in contract["deferred"]+contract["additional"]
           if x["intent"]==intent}
    need(bool(rules) and isinstance(values,dict) and values.keys()<=rules.keys(),
         "unknown-slot")
    result={}
    for name,rule in rules.items():
        if name in values:
            value=values[name]
            need(isinstance(value,dict) and value.get("kind")==rule["kind"], "slot-kind")
            validate_value(value,contract,validator)
            result[name]={"value":value,"provenance":"explicit-candidate"}
        elif rule["default"] is not None:
            validate_value(rule["default"],contract,validator)
            result[name]={"value":rule["default"],"provenance":"catalog-default"}
        else:
            need(not rule["required"],"missing-slot")
    if intent=="help.command.explain" and "option" in result:
        need(result["option"]["value"]["value"] in
             contract["utility_options"][result["utility"]["value"]["value"]], "option-binding")
    return result


def validate_window(intent, start, end, reference, contract):
    need(intent in contract["max_window_seconds"], "window-intent")
    need(all(type(v) is int for v in (start,end,reference)) and
         0 <= start < end <= reference <= 253402300799, "window-order")
    need(end-start <= contract["max_window_seconds"][intent], "window-bound")
    # Half-open UTC epoch interval. No local timezone inference.
