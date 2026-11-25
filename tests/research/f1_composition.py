"""Research composition must preserve old B0 regression and abstain on contrasts."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/"tests/pipeline"
spec=importlib.util.spec_from_file_location("pipeline_oracle",HERE/"run.py")
o=importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
from b2_linear import Linear
from b2_dev_protocol import call,model_frame

original,cli,compose,b2=sys.argv[1:5]
def invoke(probe,raw):
    p=subprocess.run([probe,"B0"],input=raw,capture_output=True,timeout=5)
    assert p.returncode==0 and not p.stderr
    stdout=p.stdout.decode("utf-8").rstrip("\n")
    obj=json.loads(stdout)
    o.check_invariants(obj,raw,stdout)
    return obj
cases=o.cases+json.loads((HERE/"f1-functional-v1.json").read_bytes())["cases"]+json.loads((HERE/"f1-v2-functional.json").read_bytes())["cases"]
for row in cases:
    raw=o.data(row)
    before=invoke(original,raw)
    after=invoke(compose,raw)
    # Research fallback is not allowed to alter previous gold/negative
    # outcomes, including clarification, policy denial, and exact spans.
    assert before==after,row["id"]
assert len(cases)==574

positive=[
 ("Report Linux kernel architecture","system.os.info"),
 ("Rinci durasi uptime dan beban rata-rata","system.uptime.summary"),
 ("Enumerate current active connections","network.connection.active"),
 ("Inspect assigned interface addresses","network.interface.list"),
 ("Rinci tabel rute dan gateway IP","network.route.table"),
 ("Describe configured DNS resolver settings","network.dns.config"),
 ("Enumerate currently active service units","service.list.active"),
 ("Rinci unit layanan berstatus gagal sekarang","service.failed.list"),
 ("Inspect boot enablement of services","service.enabled.list"),
 ("Report accessible kernel boot records","log.boot.messages"),
 ("Rinci kapasitas dan ruang bebas filesystem","storage.filesystem.usage"),
 ("Inspect free inode counts by filesystem","storage.inode.usage"),
 ("Describe block storage devices and partitions","storage.block.list"),
 ("Rinci titik mount sistem berkas","storage.mount.list"),
 ("Rank processes by highest CPU utilization","process.list.top_cpu"),
 ("Rank processes by largest resident RAM","process.list.top_mem"),
 ("Inspect process parent child relationships","process.tree.view"),
 ("Rinci memori fisik tersedia dan swap","memory.summary"),
 ("Describe CPU architecture and logical cores","cpu.hardware.info"),
 ("Identify visible user login sessions","user.session.who"),
 ("Report numeric UID GID identity","user.identity.info"),
]
registry={i:n for n,i in enumerate(o.all_registry)}
novel=0
zero=Linear.zero()
for text,intent in positive:
    raw=text.encode()
    before=invoke(original,raw)
    after=invoke(compose,raw)
    assert after["view"]["decision"]=="allow-proposal" and after["view"]["intent"]==intent,(text,after["view"])
    assert after["nlu"]["slot_candidates"]==[]
    assert after["view"]["execution_allowed"] is False
    novel+=before["view"]["decision"]!="allow-proposal"
    model=Linear.zero()
    model.bias[registry[intent]]=100
    for weights,expected in ((model,"allow-proposal"),(zero,"unsupported")):
        obj,stdout=call(b2,model_frame(weights,1),raw)
        trace=obj.pop("trace")
        o.check_invariants(obj,raw,stdout)
        assert obj["view"]["decision"]==expected and trace["grammar_class"]==registry[intent]
        if expected=="allow-proposal":
            assert obj==after
    for neg in (raw+b" not",b"jangan "+raw,raw+b" arbitrarytoken",
                raw+b' "target"',raw+b";",raw+b" or report user identity UID GID"):
        obj=invoke(compose,neg)
        assert obj["view"]["decision"]!="allow-proposal",(neg,obj["view"])
assert novel>=10
for text in ("Report service active and failed","Show active network connections and route table",
             "Show memory available and CPU architecture","Report cpu processes",
             "Report process resident memory","Guide diagnosis disk","Report UID GID for other user",
             "Show enabled services in previous boot","Show failed services since yesterday",
             "Report CPU architecture 4","Report file metadata /fixture/data/report.txt",
             "Propose restarting demo.service and inspect active services"):
    obj=invoke(compose,text.encode())
    assert obj["view"]["decision"]!="allow-proposal",(text,obj["view"])
print("F1_COMPOSITION_BOUNDARY 574 old B0 outputs identical;",len(positive),"positive frames;",
      novel,"previously unsupported; 42 B2 guard transitions;",
      len(positive)*6+12,"contrast inputs rejected from proposal; research only")
