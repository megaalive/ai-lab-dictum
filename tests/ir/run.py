"""Oracle pengembangan untuk kontrak DCT-002."""

import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from jsonschema.exceptions import SchemaError

from schema_profile import ProfileError, prepare_validators
from semantics import validate_chain
from wire import Reject, check_input, decode_frame, read_source


HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE.parents[1] / "spec" / "ir"
SCHEMAS = {
    "nlu": "nlu-proposal-v1.schema.json",
    "ir": "resolved-ir-v1.schema.json",
    "policy": "policy-decision-v1.schema.json",
    "plan": "execution-plan-v1.schema.json",
}


def fixture(name):
    return read_source(HERE / "fixtures" / f"{name}.json")


def edit(value, changes):
    result = deepcopy(value)
    for change in changes:
        operation, path, *arguments = change
        current = result
        for key in path[:-1]:
            current = current[key]
        if operation == "put":
            current[path[-1]] = arguments[0]
        elif operation == "remove":
            del current[path[-1]]
        else:
            raise ValueError(f"Operasi fixture tidak dikenal {operation}")
    return result


def sample_bytes(case):
    if "hex" in case:
        return bytes.fromhex(case["hex"])
    if "repeat" in case:
        before, unit, count, after = case["repeat"]
        return (before + unit * count + after).encode("utf-8")
    return case["text"].encode("utf-8")


def check_schema(stage, instance, validators):
    data = json.dumps(instance, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    parsed = decode_frame(data)
    if not validators[SCHEMAS[stage]].is_valid(parsed):
        raise Reject("schema", "structure")


def check_chain(case, validators, catalog, identities):
    for stage, instance in case["objects"].items():
        check_schema(stage, instance, validators)
    validate_chain(case, catalog, identities)


def check_configuration(schemas):
    try:
        prepare_validators(schemas)
    except SchemaError as exc:
        raise Reject("profile", "metaschema") from exc
    except ProfileError as exc:
        raise Reject("profile", "subset") from exc


def main():
    schemas = {name: read_source(SCHEMA_DIR / name) for name in SCHEMAS.values()}
    validators, references, retrievals = prepare_validators(schemas)
    kinds = schemas[SCHEMAS["nlu"]]["$defs"]["slot_kind"]["enum"]
    variants = schemas[SCHEMAS["ir"]]["$defs"]["slot_value"]["oneOf"]
    if set(kinds) != {branch["properties"]["kind"]["const"] for branch in variants}:
        raise ValueError("Jenis context-ref dan slot ResolvedIR berbeda")
    print(f"Draft 2020-12 + profil Dictum {len(validators)}/4, {references} ref lokal ter-resolve")

    stats = Counter()
    schema_stats = Counter()
    test_ids = set()
    failures = 0

    def run(layer, test_id, expected, evaluate):
        nonlocal failures
        if test_id in test_ids:
            raise ValueError(f"ID fixture ganda {test_id}")
        test_ids.add(test_id)
        actual = "ok"
        try:
            evaluate()
        except Reject as rejection:
            actual = str(rejection)
        stats[layer, "positif" if expected == "ok" else "negatif"] += 1
        if expected != actual:
            failures += 1
        status = "PASS" if expected == actual else "FAIL"
        print(f"{status} {test_id} ({layer}) expected={expected} actual={actual}")

    for case in fixture("profile"):
        run("profile", case["id"], case["expect"],
            lambda: check_configuration(edit(schemas, case["edits"])))

    for case in fixture("raw"):
        decoder = check_input if case.get("target") == "input" else decode_frame
        run("byte", case["id"], case["expect"], lambda: decoder(sample_bytes(case)))

    gold = fixture("chains")
    chains = {case["id"]: case for case in gold["chains"]}
    catalog = {case["rule"]["intent"]: case["rule"] for case in chains.values()}
    if len(chains) != len(gold["chains"]) or len(catalog) != len(chains):
        raise ValueError("ID rantai atau intent fixture ganda")
    identities = gold["identities"]
    for case in chains.values():
        for stage, instance in case["objects"].items():
            run("schema", f"SC-{case['id']}-{stage}", "ok",
                lambda: check_schema(stage, instance, validators))
            schema_stats[stage, "positif"] += 1
        run("semantic", f"SE-{case['id']}", "ok",
            lambda: check_chain(case, validators, catalog, identities))

    for case in fixture("schema"):
        stage = case["stage"]
        instance = edit(chains[case["base"]]["objects"][stage], case["edits"])
        run("schema", case["id"], case["expect"], lambda: check_schema(stage, instance, validators))
        schema_stats[stage, "positif" if case["expect"] == "ok" else "negatif"] += 1

    for case in fixture("semantic"):
        chain = edit(chains[case["base"]], case["edits"])
        run("semantic", case["id"], case["expect"],
            lambda: check_chain(chain, validators, catalog, identities))

    for layer in ("byte", "schema", "semantic", "profile"):
        print(f"{layer}: positif={stats[layer, 'positif']} negatif={stats[layer, 'negatif']}")
    for stage in SCHEMAS:
        print(f"schema/{stage}: positif={schema_stats[stage, 'positif']} negatif={schema_stats[stage, 'negatif']}")
    print(f"Registry offline: {len(retrievals)} percobaan retrieval")
    print(f"Total {len(test_ids)} fixture, {failures} hasil tidak cocok")
    return 1 if failures or retrievals else 0


if __name__ == "__main__":
    sys.exit(main())
