"""Lint kontrak A3; tidak menjalankan target OS, bukan oracle semantik host."""

import hashlib
import json
import re
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "spec/catalog/catalog-v1.schema.json"
FILES = {
    "registry": "catalog/core/intents-v1.json",
    "profile": "catalog/debian-13/v1.json",
    "fixtures": "tests/catalog/fixtures/intent-contracts-v1.json",
}
PLAN = "plans/drafts/rencana-v3.md"
F0 = "plans/drafts/f0-v3.md"
BASELINE_BLOBS = {
    PLAN: "b3554946d62549b7417ea451294ff65b4f01a1fe",
    F0: "20afaa1cf4999d36de78dacf812bae2a7e512c34",
}
SENSITIVE = {
    "shadow", "ssh-keys", "cloud-kube-credentials", "dotenv", "shell-history",
    "proc-environ-mem", "device-nodes", "database-data", "browser-profiles",
    "unknown-sensitive",
}
INTEGER_BOUNDS = {
    "port": (1, 65535), "positive-int": (1, 1000),
    "depth": (1, 32), "duration-seconds": (1, 604800),
}
# Independent scope expectations from baseline, not derived from registry.
ROOT_GROUPS = {
    "verified-catalog": {1, 2}, "system-metadata": {3, 4, 35, 36},
    "local-network-metadata": set(range(5, 12)),
    "local-metadata-guidance": {12, 41, 42, 43, 44},
    "local-service-metadata": {13, 14, 15, 16, 45, 46},
    "local-journal": {17, 18, 19},
    "local-mount-metadata": {20, 21, 23, 24},
    "explicit-data-root": {22, 25, 26, 48},
    "explicit-data-file": {27, 28, 29},
    "explicit-archive-file": {30, 47},
    "local-process-metadata": {31, 32, 33, 34},
    "local-package-metadata": {37, 38},
    "local-session-metadata": {39}, "current-identity": {40},
    "explicit-new-data-root": {47}, "explicit-new-archive-file": {48},
}
PENDING = {1, 10, 11, 12, 26, 29, 33, 37, 38}
PERMANENT = set(range(10, 20)) | set(range(41, 49))
EXPECTED_CONSTRAINTS = {
    "network.listener.lookup": [
        {"kind": "at-least-one-explicit", "slots": ["port", "protocol"]}],
    "file.search": [
        {"kind": "at-least-one", "slots": ["extension", "filename", "window"]}],
}


class Reject(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise Reject(code)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate-key")
        result[key] = value
    return result


def invalid_number(_):
    raise Reject("number-syntax")


def read_json(path):
    data = (ROOT / path).read_bytes()
    require(0 < len(data) <= 256 * 1024, "file-size")
    return json.loads(data.decode("utf-8", errors="strict"),
                      object_pairs_hook=unique_object,
                      parse_constant=invalid_number,
                      parse_float=invalid_number)


def baseline_ids():
    texts = {}
    for path, expected in BASELINE_BLOBS.items():
        data = (ROOT / path).read_bytes()
        # Git blob SHA-1 identifies immutable baseline, not publisher trust.
        git_blob = hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\x00" + data
        ).hexdigest()
        require(git_blob == expected, "baseline-blob")
        texts[path] = data.decode("utf-8")
    appendix = texts[PLAN].split("## Lampiran A.", 1)[1].split("### A.1", 1)[0]
    ids = re.findall(r"^(\d+)\. \x60([a-z][a-z0-9_.]+)\x60", appendix, re.M)
    require([int(n) for n, _ in ids] == list(range(1, 49)), "baseline-ids")
    require(len({i for _, i in ids}) == 48, "baseline-ids")
    skeleton_section = texts[F0].split("## 4. F0-C", 1)[1].split(
        "### Acceptance checklist", 1)[0]
    skeleton = re.findall(r"^\|\s*([a-z][a-z0-9_.]+)\s*\|",
                          skeleton_section, re.M)
    require(len(skeleton) == len(set(skeleton)) == 8, "baseline-skeleton")
    require(set(skeleton) <= {i for _, i in ids}, "baseline-skeleton")
    return [i for _, i in ids], set(skeleton)


def make_validator():
    schema = read_json(SCHEMA)
    docs = [schema]
    for name in ("nlu-proposal", "resolved-ir", "policy-decision", "execution-plan"):
        docs.append(read_json(f"spec/ir/{name}-v1.schema.json"))
    for doc in docs:
        Draft202012Validator.check_schema(doc)
    attempts = []

    def deny_retrieval(uri):
        attempts.append(uri)
        raise NoSuchResource(ref=uri)

    registry = Registry(retrieve=deny_retrieval).with_resources(
        (doc["$id"], Resource.from_contents(doc)) for doc in docs
    )
    return Draft202012Validator(schema, registry=registry), attempts


def shape(document, validator):
    require(validator.is_valid(document), "schema")


def lint(data, ids, skeleton):
    intents, bindings, fixtures = (
        data["registry"]["intents"], data["profile"]["bindings"],
        data["fixtures"]["fixtures"])
    require([i["id"] for i in intents] == ids, "canonical-ids")
    require([i["ordinal"] for i in intents] == list(range(1, 49)), "ordinal")
    require({i["id"] for i in intents if i["skeleton"]} == skeleton,
            "skeleton")
    require([b["intent"] for b in bindings] == ids, "profile-join")
    require([f["intent"] for f in fixtures] == ids, "fixture-join")
    require(len({b["capability_id"] for b in bindings}) == 48, "capability-id")
    require(len({f["id"] for f in fixtures}) == 48, "fixture-id")
    for n, (i, b, f) in enumerate(zip(intents, bindings, fixtures), start=1):
        effect, scope = i["effect"], i["scope"]
        cls = "INFO" if n <= 4 else "CHANGE" if n >= 45 else "READ"
        require(effect["class"] == cls, "effect-class")
        axes = effect["axes"]
        require(axes == sorted(set(axes)), "effect-order")
        require(("network" in axes) == (n in {10, 11}), "net-effect")
        require(("persistent-mutation" in axes) == (cls == "CHANGE"),
                "mutation-effect")
        if cls == "INFO":
            require(set(axes) <= {"filesystem-read"}, "info-effect")
            require(b["backend_candidate"] in {"native-metadata", "indexed-documentation"},
                    "info-backend")
        if n in {12, 41, 42, 43, 44}:
            require(b["backend_candidate"] == "diagnostic-guide" and
                    not b["socket_domains"] and not b["ipc_candidates"],
                    "diagnosis-backend")
        expected = ("PERMANENT-PROPOSAL-ONLY" if n in PERMANENT
                    else "NO-EXECUTOR-NEEDED" if cls == "INFO"
                    else "F5-CANDIDATE-BLOCKED")
        require(i["future_execution"] == expected, "future-execution")
        privilege = "requires-privilege" in axes
        require(i["requires_privilege"] == ("POSSIBLE" if privilege else "NOT VERIFIED")
                and b["rights"]["privilege_may_be_required"] == privilege, "privilege")
        require(not b["ipc_candidates"] or "ipc" in axes, "ipc-effect")
        require(not (set(b["socket_domains"]) & {"AF_INET", "AF_INET6"})
                or n in {10, 11}, "network-domain")
        require(b["capability_id"] == "linux." + i["id"], "capability-id")
        require(i["source"]["baseline_ordinal"] == n, "source-ordinal")
        require(i["source"]["external_reference_candidate"] == b["data_source_candidate"],
                "source-join")
        require(i["fixture_id"] == b["fixture_id"] == f["id"] == f"CAT-{n:02d}",
                "fixture-id")
        require(set(scope["allowed_root_types"]) ==
                {name for name, ordinals in ROOT_GROUPS.items() if n in ordinals},
                "scope-roots")
        require(set(scope["forbidden_path_classes"]) == SENSITIVE, "sensitive-classes")
        require(scope["limits"]["max_depth"] <= 8, "scope-depth")
        slots = i["slots"]
        names = {s["name"] for s in slots}
        deferred = i["deferred_slots"]
        deferred_names = {s["name"] for s in deferred}
        require(len(names) == len(slots) and len(deferred_names) == len(deferred)
                and not names & deferred_names and len(names | deferred_names) <= 16,
                "slot-names")
        require(bool(deferred) == (n in PENDING), "deferred-slots")
        require(i["slot_constraints"] == EXPECTED_CONSTRAINTS.get(i["id"], []),
                "slot-constraint")
        for constraint in i["slot_constraints"]:
            require(set(constraint["slots"]) <= names, "slot-constraint")
        for s in slots:
            kind, value, lo, hi = s["kind"], s["default"], s["minimum"], s["maximum"]
            require(value is None or value["kind"] == kind, "default-kind")
            if kind in INTEGER_BOUNDS:
                a, z = INTEGER_BOUNDS[kind]
                require(lo is not None and hi is not None and a <= lo <= hi <= z,
                        "slot-bound")
                require(value is None or lo <= value["value"] <= hi, "default-bound")
            else:
                require(lo is None and hi is None, "slot-bound")
            if kind in {"path", "unit-name", "filename", "extension", "time-window"}:
                require(value is None, "target-default")
            if kind == "depth":
                require(hi <= scope["limits"]["max_depth"], "scope-depth")
            if s["name"] == "limit":
                require(hi <= scope["limits"]["max_entries"], "scope-limit")
    require(Counter(i["effect"]["class"] for i in intents) ==
            {"INFO": 4, "READ": 40, "CHANGE": 4}, "class-count")


def compare_a2(data):
    """A2 is a synthetic subset: compare vocabulary and present slots, not host recipes."""
    reg = {i["id"]: i for i in data["registry"]["intents"]}
    chains = read_json("tests/ir/fixtures/chains.json")["chains"]
    require(len(chains) == 8 and {c["rule"]["intent"] for c in chains} ==
            {i["id"] for i in reg.values() if i["skeleton"]}, "a2-skeleton")
    for c in chains:
        i = reg[c["rule"]["intent"]]
        slots = {s["name"]: s for s in i["slots"]}
        for name, rule in c["rule"]["slots"].items():
            require(name in slots and slots[name]["kind"] == rule["kind"], "a2-kind")
            if "default" in rule:
                require(slots[name]["default"] == rule["default"], "a2-default")
        for s in c["objects"]["ir"]["slots"]:
            current = slots[s["name"]]
            require(s["value"]["kind"] == current["kind"], "a2-kind")
            if current["kind"] in INTEGER_BOUNDS:
                require(current["minimum"] <= s["value"]["value"] <= current["maximum"],
                        "a2-bound")


def render_matrix(data):
    lines = [
        "# Matriks efek dan capability DCT-003", "",
        "Ditampilkan dari registry dan profil Debian 13; semua capability BLOCKED, compatibility NOT VERIFIED, execute_eligible=false, host-equivalence NOT RUN. Efek adalah proyeksi operasi, bukan izin atau aktivitas yang dijalankan. P = permanen proposal-only; C = kandidat F5 masih BLOCKED; I = INFO tanpa executor.",
        "",
        "| # | Intent | Kelas / efek | Status masa depan | Capability | Sumber kandidat |",
        "|---:|---|---|---|---|---|",
    ]
    tick = chr(96)
    statuses = {"PERMANENT-PROPOSAL-ONLY": "P", "F5-CANDIDATE-BLOCKED": "C",
                "NO-EXECUTOR-NEEDED": "I"}
    for i, b in zip(data["registry"]["intents"], data["profile"]["bindings"]):
        marker = " †" if i["skeleton"] else ""
        axes = ", ".join(i["effect"]["axes"]) or "—"
        lines.append(
            f"| {i['ordinal']} | {tick}{i['id']}{tick}{marker} | "
            f"{i['effect']['class']} / {axes} | {statuses[i['future_execution']]} | "
            f"{tick}{b['capability_id']}{tick} | {b['data_source_candidate']} |"
        )
    lines += ["", "† Walking skeleton F0-C. Rincian rights, namespace, socket/IPC, scope, output, fixture dan oracle terdapat pada pasangan record JSON. Tidak ada resep executable yang siap dipakai.", ""]
    return "\n".join(lines)


def set_value(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def main():
    ids, skeleton = baseline_ids()
    validator, retrievals = make_validator()
    data = {k: read_json(v) for k, v in FILES.items()}
    passed, failures = 0, 0

    def run(name, expected, procedure):
        nonlocal passed, failures
        actual = "ok"
        try:
            procedure()
        except Reject as exc:
            actual = str(exc)
        if actual == expected:
            passed += 1
            status = "PASS"
        else:
            failures += 1
            status = "FAIL"
        print(f"{status} {name} expected={expected} actual={actual}")

    def validate(candidate):
        for doc in candidate.values():
            shape(doc, validator)
        lint(candidate, ids, skeleton)

    for name, document in data.items():
        run("CAT-SCHEMA-" + name, "ok", lambda: shape(document, validator))
    run("CAT-CANONICAL-LINT", "ok", lambda: lint(data, ids, skeleton))
    run("CAT-A2-COMPAT", "ok", lambda: compare_a2(data))
    run("CAT-MATRIX", "ok", lambda: require(
        (ROOT / "catalog/core/effect-capability-matrix.md").read_text(encoding="utf-8")
        == render_matrix(data), "matrix-drift"))
    # Independent negative cases: mutate a copy, preserve source files.
    mutations = [
        ("registry-47", "schema", ["registry", "intents"], data["registry"]["intents"][:-1]),
        ("canonical-id", "canonical-ids", ["registry", "intents", 0, "id"], "fixture.other"),
        ("duplicate-id", "canonical-ids", ["registry", "intents", 0, "id"], ids[1]),
        ("ordinal", "ordinal", ["registry", "intents", 0, "ordinal"], 2),
        ("skeleton", "skeleton", ["registry", "intents", 0, "skeleton"], True),
        ("unknown-field", "schema", ["registry", "intents", 0, "approval"], True),
        ("unknown-axis", "schema", ["registry", "intents", 0, "effect", "axes"], ["magic"]),
        ("duplicate-axis", "effect-order", ["registry", "intents", 2, "effect", "axes"], ["filesystem-read"] * 2),
        ("effect-class", "effect-class", ["registry", "intents", 0, "effect", "class"], "HIGH"),
        ("info-spawn", "info-effect", ["registry", "intents", 0, "effect", "axes"], ["spawn"]),
        ("net-missing", "net-effect", ["registry", "intents", 9, "effect", "axes"], ["ipc", "spawn"]),
        ("change-missing", "mutation-effect", ["registry", "intents", 44, "effect", "axes"], ["ipc", "requires-privilege", "spawn"]),
        ("execute-true", "schema", ["registry", "intents", 4, "execute_eligible"], True),
        ("permanent-ping", "future-execution", ["registry", "intents", 10, "future_execution"], "F5-CANDIDATE-BLOCKED"),
        ("permanent-diagnosis", "future-execution", ["registry", "intents", 40, "future_execution"], "F5-CANDIDATE-BLOCKED"),
        ("permanent-service", "future-execution", ["registry", "intents", 12, "future_execution"], "F5-CANDIDATE-BLOCKED"),
        ("permanent-change", "future-execution", ["registry", "intents", 44, "future_execution"], "F5-CANDIDATE-BLOCKED"),
        ("recursive-cwd", "schema", ["registry", "intents", 24, "scope", "recursive_cwd_default"], True),
        ("no-auth", "schema", ["registry", "intents", 24, "scope", "explicit_authorization"], False),
        ("arbitrary-root", "schema", ["registry", "intents", 24, "scope", "allowed_root_types"], ["any"]),
        ("scope-broaden", "scope-roots", ["registry", "intents", 24, "scope", "allowed_root_types"], ["explicit-data-root", "local-journal"]),
        ("sensitive-missing", "schema", ["registry", "intents", 24, "scope", "forbidden_path_classes"], sorted(SENSITIVE - {"dotenv"})),
        ("unknown-output", "schema", ["registry", "intents", 30, "output_projection"], ["raw_cmdline"]),
        ("unbounded-output", "schema", ["registry", "intents", 24, "scope", "limits", "max_output_bytes"], 65537),
        ("slot-type", "schema", ["registry", "intents", 4, "slots", 0, "kind"], "arbitrary"),
        ("default-kind", "default-kind", ["registry", "intents", 4, "slots", 1, "default"], {"kind": "port", "value": 5432}),
        ("default-over", "default-bound", ["registry", "intents", 10, "slots", 0, "default"], {"kind": "positive-int", "value": 5}),
        ("port-over", "slot-bound", ["registry", "intents", 4, "slots", 0, "maximum"], 65536),
        ("default-path", "target-default", ["registry", "intents", 21, "slots", 0, "default"], {"kind": "path", "value": "."}),
        ("slot-duplicate", "slot-names", ["registry", "intents", 4, "slots", 1, "name"], "port"),
        ("constraint-drop", "slot-constraint", ["registry", "intents", 24, "slot_constraints"], []),
        ("deferred-drop", "deferred-slots", ["registry", "intents", 9, "deferred_slots"], []),
        ("source-ordinal", "source-ordinal", ["registry", "intents", 0, "source", "baseline_ordinal"], 2),
        ("license-assume", "schema", ["registry", "intents", 0, "source", "license_status"], "VERIFIED"),
        ("profile-orphan", "profile-join", ["profile", "bindings", 0, "intent"], "fixture.other"),
        ("capability-fake", "schema", ["profile", "bindings", 0, "capability_status"], "VERIFIED"),
        ("version-fake", "schema", ["profile", "bindings", 0, "minimum_version"], "1.0"),
        ("group-elevation", "schema", ["profile", "bindings", 16, "rights", "required_groups"], ["adm"]),
        ("extra-rights", "schema", ["profile", "bindings", 16, "rights", "request_additional_groups"], True),
        ("privilege-mismatch", "privilege", ["profile", "bindings", 44, "rights", "privilege_may_be_required"], False),
        ("network-domain", "network-domain", ["profile", "bindings", 4, "socket_domains"], ["AF_INET"]),
        ("ipc-mismatch", "ipc-effect", ["profile", "bindings", 34, "ipc_candidates"], ["systemd-dbus"]),
        ("fake-host-pass", "schema", ["profile", "bindings", 0, "host_equivalence", "result"], "PASS"),
        ("fixture-orphan", "fixture-join", ["fixtures", "fixtures", 0, "intent"], "fixture.other"),
        ("fixture-duplicate", "fixture-id", ["fixtures", "fixtures", 0, "id"], "CAT-02"),
        ("fixture-execute", "schema", ["fixtures", "fixtures", 0, "execution_allowed"], True),
        ("fixture-fake-pass", "schema", ["fixtures", "fixtures", 0, "result"], "PASS"),
    ]
    for name, expected, path, replacement in mutations:
        candidate = deepcopy(data)
        set_value(candidate, path, replacement)
        run("CAT-NEG-" + name, expected, lambda: validate(candidate))

    print(f"Registry: {len(ids)} canonical, 4 INFO / 40 READ / 4 CHANGE, {len(skeleton)} skeleton")
    print(f"Profile: 48 BLOCKED; fixture contract: 48 positive/negative pairs, execution NOT RUN")
    print(f"Registry offline: {len(retrievals)} percobaan retrieval")
    print(f"Total A3: {passed}/{passed + failures} cocok, {failures} mismatch")
    return 1 if failures or retrievals else 0


if __name__ == "__main__":
    sys.exit(main())
