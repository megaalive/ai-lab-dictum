"""Pemeriksaan lintas objek terhadap konteks sintetis yang disiapkan harness."""

import re

from wire import Reject, check_input, scalar_bytes


NO_SCOPE = {"kind": "none"}
UNKNOWN_EFFECT = {"class": "UNKNOWN", "axes": []}
TRANSITIONS = {
    "resolved": {"allow-proposal": {"proposal-eligible"},
                 "allow-execute-eligible": {"execute-eligible"}, "deny": {"policy-restriction"}},
    "incomplete": {"clarify": {"missing-slot"}, "deny": {"policy-restriction"}},
    "ambiguous": {"clarify": {"ambiguous"}, "deny": {"policy-restriction"}},
    "unsupported": {"unsupported": {"unsupported-intent", "unsupported-profile"},
                    "deny": {"policy-restriction"}},
    "invalid": {"deny": {"invalid-candidate", "policy-restriction"}},
}
INTEGER_SLOT_KINDS = {"port", "positive-int", "depth", "duration-seconds"}
MAX_PATH_BYTES = 1024
MAX_EXECUTION_TTL_MS = 120_000


def require(condition, code):
    if not condition:
        raise Reject("semantic", code)


def span_text(data, span):
    start, end = span["start"], span["end"]
    require(0 <= start < end <= len(data), "span")
    try:
        return data[start:end].decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise Reject("semantic", "span") from exc


def named_entries(items, key, code):
    entries = {item[key]: item for item in items}
    require(len(entries) == len(items), code)
    return entries


def check_proposal(proposal, trusted, data):
    candidates = named_entries(proposal["slot_candidates"], "id", "duplicate-candidate")
    intents = named_entries(proposal["intent_candidates"], "intent", "duplicate-intent")
    for candidate in candidates.values():
        source = candidate["source"]
        if source["kind"] == "input-span":
            span_text(data, source["span"])
        else:
            entry = trusted["candidates"].get(source["candidate_id"])
            require(entry is not None and entry["slot"] == candidate["slot"]
                    and entry["value"]["kind"] == source["expected_kind"], "candidate-reference")
    for intent in intents.values():
        ids = intent["slot_candidate_ids"]
        require(len(ids) == len(set(ids)) and set(ids) <= candidates.keys(), "candidate-reference")
    return {
        intent: [candidates[identifier] for identifier in candidate["slot_candidate_ids"]]
        for intent, candidate in intents.items()
    }


def check_provenance(slot, slot_rule, selected, trusted, data):
    value, source = slot["value"], slot["provenance"]
    kind = value["kind"]
    require(kind == slot_rule["kind"], "slot-type")
    if kind == "time-window":
        require(value["start_unix_s"] < value["end_unix_s"], "time-order")
    if kind in {"path", "filename", "extension"}:
        bound = {"path": MAX_PATH_BYTES, "filename": 255, "extension": 32}[kind]
        require(len(value["value"].encode("utf-8")) <= bound, "literal-bytes")

    if source["kind"] == "catalog-default":
        require(slot_rule.get("default") == value and not selected, "provenance")
    elif source["kind"] == "context-ref":
        bound_candidate = {"kind": "context-ref", "candidate_id": source["candidate_id"],
                           "expected_kind": kind}
        require(bound_candidate in selected, "provenance")
        entry = trusted["candidates"][source["candidate_id"]]
        require(entry == {"slot": slot["name"], "value": value}, "provenance")
    else:
        require(source in selected and kind != "time-window", "provenance")
        token = span_text(data, source["span"])
        actual = value["value"]
        if kind in INTEGER_SLOT_KINDS:
            require(re.fullmatch(r"[0-9]{1,16}", token) and int(token) == actual, "provenance")
        else:
            require(token == actual, "provenance")


def check_resolution(resolved, catalog, proposals, trusted, data):
    intent = resolved.get("intent")
    require(intent is None or intent in catalog, "unknown-intent")
    rule = catalog.get(intent)
    slot_rules = rule["slots"] if rule else {}
    slots = named_entries(resolved["slots"], "name", "contradictory-slots")
    resolution = resolved["resolution"]
    pending = named_entries(resolution["unresolved"], "slot", "contradictory-slots")
    known = slot_rules.keys()
    require(slots.keys() <= known and pending.keys() <= known, "unknown-slot")
    require(not slots.keys() & pending.keys(), "contradictory-slots")
    alternatives = resolution["alternatives"]
    require(len(alternatives) == len(set(alternatives)) and set(alternatives) <= catalog.keys(),
            "unknown-alternative")
    missing = {name for name in known if slot_rules[name]["required"]} - slots.keys()
    state = resolution["state"]
    if state == "resolved":
        require(intent is not None and not pending and not alternatives, "resolution-state")
        require(not missing, "mandatory-slot")
    elif state == "incomplete":
        require(intent is not None and missing and pending.keys() == missing and not alternatives
                and all(entry["problem"] == "missing" for entry in pending.values()), "resolution-state")
    elif state == "ambiguous":
        if intent is None:
            require(len(alternatives) >= 2 and not slots and not pending, "resolution-state")
        else:
            require(not alternatives and missing <= pending.keys() and
                    any(entry["problem"] != "missing" for entry in pending.values()), "resolution-state")
    else:
        require(not slots and not pending and not alternatives, "resolution-state")

    for name, slot in slots.items():
        sources = [item["source"] for item in proposals.get(intent, ()) if item["slot"] == name]
        check_provenance(slot, slot_rules[name], sources, trusted, data)
    return rule, {name: slot["value"] for name, slot in slots.items()}


def check_policy(decision, state, rule, trusted):
    outcome = decision["decision"]
    require(decision["reason"] in TRANSITIONS[state].get(outcome, ()), "transition")
    effect = rule["effect"] if state == "resolved" else UNKNOWN_EFFECT
    require(decision["effect"] == effect, "effect")
    require(effect["axes"] == sorted(set(effect["axes"])), "effect")
    if outcome == "allow-execute-eligible":
        require(trusted["phase"] == "F5" and rule["execute_eligible"]
                and effect["class"] in {"INFO", "READ"} and "network" not in effect["axes"],
                "execute-eligibility")
    if outcome == "allow-proposal":
        require(rule["proposal_eligible"] and effect["class"] in {"INFO", "READ", "CHANGE"},
                "proposal-eligibility")
    allowed = outcome in {"allow-proposal", "allow-execute-eligible"}
    scope = {"kind": "local", "scope_id": trusted["scope_id"]} if allowed else NO_SCOPE
    require(decision["scope"] == scope, "scope")


def check_plan(plan, decision, values, trusted):
    action = plan["action"]
    candidate = action["kind"] == "execution-candidate"
    required = "allow-execute-eligible" if candidate else "allow-proposal"
    require(decision["decision"] == required, "plan-eligibility")
    require(plan["effect"] == decision["effect"], "effect")
    require(plan["scope"] == decision["scope"], "scope")
    operation = action["operation"]
    if operation["kind"] == "executable":
        require("spawn" in plan["effect"]["axes"], "effect")
        require(len(operation["identity"]["path"].encode("utf-8")) <= MAX_PATH_BYTES
                and all(arg["kind"] != "literal" or len(arg["value"].encode("utf-8")) <= MAX_PATH_BYTES
                        for arg in operation["argv"]), "literal-bytes")
    else:
        inputs = operation["input_slots"]
        require(len(inputs) == len(set(inputs)) and set(inputs) <= values.keys(), "plan-recipe")
    recipe = trusted["recipe"]
    bindings = named_entries(plan["target_bindings"], "slot", "target-binding")
    require(bindings.keys() <= values.keys(), "target-binding")
    require(plan["target_bindings"] == recipe["target_bindings"], "target-binding")
    require(values == recipe["slots"] and operation == recipe["operation"], "plan-recipe")
    if candidate:
        now = trusted["now_boottime_ms"]
        expiry = action["expires_boottime_ms"]
        require(now < expiry <= trusted["context_until_boottime_ms"]
                and expiry - now <= MAX_EXECUTION_TTL_MS, "plan-expiry")
        require(all(value <= recipe["constraints"][key]
                    for key, value in action["constraints"].items()), "plan-constraints")


def validate_chain(case, catalog, identities):
    trusted = case["trusted"]
    objects = case["objects"]
    data = check_input(scalar_bytes(case["input"]))
    require(trusted["now_boottime_ms"] < trusted["context_until_boottime_ms"], "stale-context")
    for stage in ("ir", "policy", "plan"):
        if stage not in objects:
            continue
        record = objects[stage]
        require(record["request_id"] == trusted["request_id"], "request-identity")
        require(record["resolution_id"] == trusted["resolution_id"], "resolution-identity")
        require(record["context_id"] == trusted["context_id"], "context-identity")
        require(record["catalog"] == identities["catalog"], "catalog-identity")
        if stage in {"policy", "plan"}:
            require(record["decision_id"] == trusted["decision_id"], "decision-identity")
            require(record["policy"] == identities["policy"], "policy-identity")
        if stage == "plan":
            require(record["action_id"] == trusted["action_id"], "action-identity")

    proposals = check_proposal(objects["nlu"], trusted, data)
    resolved, decision = objects["ir"], objects["policy"]
    rule, values = check_resolution(resolved, catalog, proposals, trusted, data)
    check_policy(decision, resolved["resolution"]["state"], rule, trusted)
    if "plan" in objects:
        check_plan(objects["plan"], decision, values, trusted)
