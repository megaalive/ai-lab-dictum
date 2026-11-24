"""Compile the reviewed closed IR subset into C functions; build-time only."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/ir"))
from schema_profile import prepare_validators
from wire import read_source
from run import SCHEMAS

schemas = {name: read_source(ROOT / "spec/ir" / name) for name in SCHEMAS.values()}
prepare_validators(schemas)
# Match the typed-slot vocabulary across the four schemas, as in the oracle.
nlu = schemas[SCHEMAS["nlu"]]["$defs"]["slot_kind"]["enum"]
variants = schemas[SCHEMAS["ir"]]["$defs"]["slot_value"]["oneOf"]
if set(nlu) != {x["properties"]["kind"]["const"] for x in variants}:
    raise ValueError("Inconsistent typed-slot vocabulary")
functions = []
definitions = {}
patterns = {
    r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+(?![\s\S])": "P_INTENT",
    r"^[a-z][a-z0-9_]*(?![\s\S])": "P_NAME",
    r"^[0-9a-f]{32}(?![\s\S])": "P_HEX32",
    r"^[0-9a-f]{64}(?![\s\S])": "P_HEX64",
    r"^[A-Za-z0-9_][A-Za-z0-9_.:@-]*(?![\s\S])": "P_UNIT",
    "^/": "P_PATH",
    r"^--?[A-Za-z0-9][A-Za-z0-9-]*(?![\s\S])": "P_FLAG",
}


def literal(s):
    # Profile only permits ASCII; escape every byte for C, without ambiguity.
    return '"' + ''.join('\\%03o' % ord(c) for c in s) + '"'


def compile_node(file, node):
    if "$ref" in node:
        host, name = node["$ref"].split("#/$defs/")
        host = host or file
        key = host, name
        if key not in definitions:
            definitions[key] = compile_node(host, schemas[host]["$defs"][name])
        return definitions[key]
    body = []
    if "oneOf" in node:
        children = [compile_node(file, x) for x in node["oneOf"]]
        body = ["return (" + " + ".join(f"(unsigned int){x}(d, i)" for x in children) + ") == 1u;"]
    elif node["type"] == "object":
        props = node["properties"]
        children = [(name, compile_node(file, child)) for name, child in props.items()]
        required = sum(1 << j for j, (name, _) in enumerate(children) if name in node["required"])
        body = ["if (n->kind != IR_OBJECT) return false;", "uint32_t seen = 0;",
                "for (size_t k = n->first; k != 0; k = d->nodes[k].next) {"]
        for j, (name, child) in enumerate(children):
            body.extend([f'    {"if" if j == 0 else "else if"} (eq(d, k, {literal(name)})) {{',
                         f"        if (!{child}(d, d->nodes[k].first)) return false;",
                         f"        seen |= UINT32_C({1 << j});", "    }"])
        body += ["    else return false;" if children else "    return false;", "}",
                 f"return (seen & UINT32_C({required})) == UINT32_C({required});"]
        if not children:
            body = ["return n->kind == IR_OBJECT && n->count == 0;"]
    elif node["type"] == "array":
        child = compile_node(file, node["items"])
        body = [f"if (n->kind != IR_ARRAY || !bounds(n->count, {node['minItems']}u, {node['maxItems']}u)) return false;",
                f"for (size_t k = n->first; k != 0; k = d->nodes[k].next) if (!{child}(d, k)) return false;",
                "return true;"]
    elif node["type"] == "integer":
        lo = node.get("const", node.get("minimum"))
        hi = node.get("const", node.get("maximum"))
        body = [f"return n->kind == IR_INTEGER && n->integer >= INT64_C({lo}) && n->integer <= INT64_C({hi});"]
    else:
        body = ["if (n->kind != IR_STRING) return false;"]
        if "enum" in node or "const" in node:
            values = node["enum"] if "enum" in node else [node["const"]]
            body += ["return " + " || ".join(f"eq(d, i, {literal(v)})" for v in values) + ";"]
        else:
            body += [f"if (!bounds(n->scalars, {node['minLength']}u, {node['maxLength']}u)) return false;"]
            body += [f"return pattern(d, i, {patterns[node['pattern']]});" if "pattern" in node else "return true;"]
    name = f"validate_{len(functions)}"
    pre = [] if "oneOf" in node else ["const struct ir_node *n = &d->nodes[i];"]
    functions.append(f"static bool {name}(const struct ir_document *d, size_t i)\n{{\n" +
                     "\n".join("    " + line for line in pre + body) + "\n}\n")
    return name


roots = [compile_node(file, schemas[file]) for file in SCHEMAS.values()]
output = "/* Generated; do not edit. */\n" + "\n".join(functions)
output += "\nstatic bool root_valid(const struct ir_document *d, enum ir_stage stage)\n{\n    switch (stage) {\n"
for stage, fn in zip(("IR_NLU", "IR_RESOLVED", "IR_POLICY", "IR_PLAN"), roots):
    output += f"    case {stage}: return {fn}(d, 1);\n"
output += "    }\n    return false;\n}\n"
Path(sys.argv[1]).write_text(output, encoding="ascii")
