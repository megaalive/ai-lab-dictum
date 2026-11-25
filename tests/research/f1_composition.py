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
             "Report CPU architecture 4","Report file metadata /outside/report.txt",
             "Propose restarting demo.service and inspect active services"):
    obj=invoke(compose,text.encode())
    assert obj["view"]["decision"]!="allow-proposal",(text,obj["view"])
print("F1_COMPOSITION_BOUNDARY 574 old B0 outputs identical;",len(positive),"positive frames;",
      novel,"previously unsupported; 42 B2 guard transitions;",
      len(positive)*6+12,"contrast inputs rejected from proposal; research only")


# Original project-authored train/dev-inspired hypotheses, not observed
# test rows. Check typed values, explicit spans, defaults and B2 veto.
typed=[
 # Intentional migration of a slotless-only contrast: valid explicit path now supported.
 ("Report file metadata /fixture/data/report.txt","file.metadata.stat",{"path":"/fixture/data/report.txt"}),
 ("Rinci keadaan unit layanan demo.service sekarang","service.status.get",{"unit":"demo.service"}),
 ("Describe runtime status of service worker.service","service.status.get",{"unit":"worker.service"}),
 ("Temukan subdirektori terbesar di /fixture/projects","storage.directory.usage",{"root":"/fixture/projects"}),
 ('Rank largest child folders within "/fixture/data set"',"storage.directory.usage",{"root":"/fixture/data set"}),
 ("Rinci atribut berkas /fixture/data/report.txt","file.metadata.stat",{"path":"/fixture/data/report.txt"}),
 ("Describe owner and metadata of file /fixture/data/notes.md","file.metadata.stat",{"path":"/fixture/data/notes.md"}),
 ("Rinci izin akses efektif berkas /fixture/logs/events.log","file.permission.check",{"path":"/fixture/logs/events.log"}),
 ("Determine allowed access modes of file /fixture/data/notes.md","file.permission.check",{"path":"/fixture/data/notes.md"}),
 ("Rinci nama anggota arsip /fixture/data/demo.tar","archive.contents.list",{"path":"/fixture/data/demo.tar"}),
 ("Enumerate member names inside archive /fixture/data/demo.zip","archive.contents.list",{"path":"/fixture/data/demo.zip"}),
 ('Identifikasi PID proses bernama "fixture worker"',"process.lookup.name",{"name":"fixture worker"}),
 ("Locate process identifiers associated with name demo-worker","process.lookup.name",{"name":"demo-worker"}),
 ("Rinci status instalasi paket demo-package","package.installed.check",{"package":"demo-package"}),
 ("Determine installed version of package libdemo1","package.installed.check",{"package":"libdemo1"}),
 ('Telusuri indeks paket offline dengan kata "demo+tools"',"package.search.local",{"query":"demo+tools"}),
 ('Find packages matching "fixture package" in local cache',"package.search.local",{"query":"fixture package"}),
 ('Temukan kemunculan teks persis "teks uji" pada berkas di /fixture/logs',"file.text.search",{"root":"/fixture/logs","text":"teks uji"}),
 ('Locate exact literal "café" in text files under /fixture/data',"file.text.search",{"root":"/fixture/data","text":"café"}),
 ("Ambil 4 baris last berkas /fixture/logs/events.log","file.head_tail.view",{"path":"/fixture/logs/events.log","direction":"last","limit":4}),
 ("Report first 3 lines from file /fixture/data/notes.md","file.head_tail.view",{"path":"/fixture/data/notes.md","direction":"first","limit":3}),
 ("Temukan berkas berekstensi log dalam folder /fixture/logs","file.search",{"root":"/fixture/logs","extension":"log"}),
 ("Locate files of extension md beneath /fixture/data","file.search",{"root":"/fixture/data","extension":"md"}),
 ("Cari layanan yang menunggu koneksi udp di port 8443","network.listener.lookup",{"port":8443,"protocol":"udp"}),
 ("Identify listening socket associated with port 5432","network.listener.lookup",{"port":5432}),
 ("Rincikan koneksi aktif udp dengan batas 7","network.connection.active",{"protocol":"udp","limit":7}),
 ("Display active tcp connections with a maximum of 15 entries","network.connection.active",{"protocol":"tcp","limit":15}),
 ("Rangkum catatan jurnal unit demo.service dalam 17 menit terakhir","log.service.query",{"unit":"demo.service","window":17}),
 ("Find service journal entries of worker.service within the past 25 minutes","log.service.query",{"unit":"worker.service","window":25}),
 ("Rinci pesan galat jurnal sistem dari 31 menit terakhir","log.system.errors",{"window":31}),
 ("Report system error journal records over the last 42 minutes","log.system.errors",{"window":42}),
]
typed_novel=0
typed_neg=0
for sentence,intent,expected in typed:
    raw=sentence.encode("utf-8")
    before=invoke(original,raw)
    after=invoke(compose,raw)
    assert after["view"]["decision"]=="allow-proposal" and after["view"]["intent"]==intent,(sentence,after["view"])
    assert after["view"]["execution_allowed"] is False
    got={}
    for slot in after["nlu"]["slot_candidates"]:
        source=slot["source"]
        if slot["slot"]=="window":
            assert source["kind"]=="context-ref" and source["expected_kind"]=="time-window"
            span=after["context"]["time_candidate"]
        else:
            assert source["kind"]=="input-span"
            span=source["span"]
        assert raw[span["start"]:span["end"]]==str(expected[slot["slot"]]).encode("utf-8"),(sentence,slot)
        assert slot["slot"] not in got
        got[slot["slot"]]=expected[slot["slot"]]
    assert got==expected,(sentence,got)
    values=after["view"]["slots"]
    assert set(values)==set(expected)|{k for k,v in o.catalog[intent]["slots"].items() if v["required"]}
    for key,value in values.items():
        if key=="window":
            assert value=={"kind":"time-window","start_unix_s":o.reference-expected[key]*60,
                           "end_unix_s":o.reference},(sentence,key,value)
        elif key in expected:
            assert value["value"]==expected[key],(sentence,key,value)
        else:
            assert value==o.catalog[intent]["slots"][key]["default"],(sentence,key,value)
    typed_novel+=before["view"]["decision"]!="allow-proposal"
    model=Linear.zero()
    model.bias[registry[intent]]=100
    for weights,decision in ((model,"allow-proposal"),(zero,"unsupported")):
        obj,stdout=call(b2,model_frame(weights,1),raw)
        trace=obj.pop("trace")
        o.check_invariants(obj,raw,stdout)
        assert obj["view"]["decision"]==decision and trace["grammar_class"]==registry[intent],(sentence,trace)
        if decision=="allow-proposal":
            assert obj==after
    # Duplicate any existing explicit slot token, unknown target, negation,
    # alternatives and mixed intent. No malformed typed fallback proposal.
    source=after["nlu"]["slot_candidates"][0]["source"]
    first=source["span"] if source["kind"]=="input-span" else after["context"]["time_candidate"]
    a,b=first["start"],first["end"]
    duplicate=raw[a:b]
    if a and raw[a-1:a]==b'"':
        duplicate=b'"'+duplicate+b'"'
    for neg in (raw+b" "+duplicate,raw+b" not",b"jangan "+raw,
                raw+b" arbitrarytoken",raw+b";",raw+b" or inspect service status demo.service",
                raw[:a]+b"outside_unlisted_value"+raw[b:]):
        obj=invoke(compose,neg)
        assert obj["view"]["decision"]!="allow-proposal",(neg,obj["view"])
        typed_neg+=1
assert typed_novel>=10
# Cross-scope, wrong role, omitted/duplicate slots and out-of-range count.
for sentence in (
    "Report first 101 lines from file /fixture/data/report.txt",
    "Report first lines from file /fixture/data/report.txt",
    "Report first 4 lines from file /fixture/data/demo.tar",
    "Rinci nama anggota arsip /fixture/data/report.txt",
    "Describe runtime status of service other.service",
    'Find packages matching demo in local cache',
    'Locate exact literal "sample marker" in text files under /outside',
    'Locate exact literal "sample marker" in text files under /fixture/data /fixture/logs',
    'Locate exact literal "sample marker" in text files',
    "Rinci keadaan unit layanan demo.service serta status worker.service",
    "Find process name demo-worker",
    "Describe file metadata and permissions of /fixture/data/report.txt",
    "Locate files extension txt under /fixture/data log",
    "Locate files txt of extension under /fixture/data",
    "Identify listening socket associated with 5432 port",
    "Identify listening socket associated with port 65536",
    "Rincikan koneksi aktif udp dengan batas 0",
    "Display active udp connections with 15 entries",
    "Display active all connections with a maximum of 15 entries",
    "Report system error journal records over the next 42 minutes",
    "Report system error journal records over 42 minutes",
    "Report system error journal records over the last 1441 minutes",
    "Report system error journal records over the last 42 minutes and 12 minutes",
    "Find service journal entries of worker.service within the past 25 minutes and system errors",
    "Report system journal records over the last 42 minutes",
):
    assert invoke(compose,sentence.encode())["view"]["decision"]!="allow-proposal",sentence
    typed_neg+=1
print("F1_TYPED_COMPOSITION",len(typed),"positive frames;",typed_novel,"previously unsupported;",
      len(typed)*2,"B2 guard transitions;",typed_neg,"contrast inputs rejected from proposal; research only")
