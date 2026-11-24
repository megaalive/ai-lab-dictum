"""Pinned Unicode 15.1 format/control ranges for renderer preview v1."""
import sys
import unicodedata
from pathlib import Path
if unicodedata.unidata_version != "15.1.0":
    raise ValueError("Renderer v1 requires pinned Unicode 15.1.0 (Debian 13 Python)")
extra = [(0x034f,0x034f),(0x115f,0x1160),(0x17b4,0x17b5),(0x180b,0x180f),
         (0x3164,0x3164),(0xfe00,0xfe0f),(0xffa0,0xffa0),(0xe0100,0xe01ef)]
bad = {i for i in range(0x110000) if unicodedata.category(chr(i)) in {"Cc","Cf","Zl","Zp"}}
for start,end in extra:
    bad.update(range(start,end+1))
ranges=[]
for cp in sorted(bad):
    if ranges and cp == ranges[-1][1]+1:
        ranges[-1][1]=cp
    else:
        ranges.append([cp,cp])
out = "/* Unicode 15.1.0; generated from stdlib plus v1 conservative exclusions. */\n"
out += "static const uint32_t forbidden_ranges[][2] = {\n"
out += "".join(f"    {{0x{a:x}u,0x{b:x}u}},\n" for a,b in ranges) + "};\n"
Path(sys.argv[1]).write_text(out,encoding="ascii")
