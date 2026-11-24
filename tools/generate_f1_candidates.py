"""Generate an exact synthetic candidate value table, never IR v1 types."""
import hashlib
import sys
from pathlib import Path
from f1_slot_domains import CONTRACT, SCHEMA, load, validate_value

pins={CONTRACT:"62d31e7f180cb74a944168538f26d921653ea2693914f82e4814200fe65dc90b",
      SCHEMA:"64ed9d662cb98fcb4e1135294958e70047cbd99faf8d36f33cb1e40553e1370e"}
for path,digest in pins.items():
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        raise ValueError("Candidate contract drift requires review")
contract,validator=load()
def lit(s):
    return '"' + ''.join('\\%03o'%b for b in s.encode("utf-8"))+'"'
rows=[]
for kind,values in sorted(contract["scope"].items()):
    if len(values)!=len(set(values)) or not values:
        raise ValueError("Duplicate or empty fixture domain")
    for value in sorted(values):
        validate_value({"kind":kind,"value":value},contract,validator)
        rows.append("    {"+lit(kind)+","+lit(value)+"},")
if len(contract["scope"])!=11:
    raise ValueError("Candidate kind coverage")
Path(sys.argv[1]).write_text("/* Exact reviewed fixture values only. */\nstatic const struct pair pairs[] = {\n"+"\n".join(rows)+"\n};\n",encoding="ascii")
