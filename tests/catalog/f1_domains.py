"""Independent authored data vectors. No actual utility or target executed."""
import hashlib
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
from f1_slot_domains import CONTRACT,SCHEMA,Reject,load,validate_value,validate_slots,validate_window

c,s=load()
counts={"positive":0,"negative":0}


def check(fn,accepted):
    try:
        fn()
    except Reject:
        assert not accepted
        counts["negative"]+=1
    else:
        assert accepted
        counts["positive"]+=1


def v(k,x):
    return {"kind":k,"value":x}


positive=[
    ("utility-id","ss"),("option-id","--failed"),("dns-name","example.test"),
    ("network-target","192.0.2.10"),("network-target","2001:db8::10"),
    ("network-target","example.test"),("local-service","demo.service"),
    ("literal-text","café"),("literal-text","a+b[1]"),
    ("head-tail-direction","first"),("head-tail-direction","last"),
    ("process-name","fixture worker"),("package-id","demo-package:amd64"),
    ("package-query","demo+tools"),("dns-record-type","A"),
]
negative=[
    ("utility-id","/usr/bin/ss"),("utility-id","SS"),("utility-id","curl"),
    ("option-id","--"),("option-id","--version"),("option-id","--failed\n"),
    ("dns-name","-example.test"),("dns-name","example-.test"),("dns-name","example..test"),
    ("dns-name","example.test."),("dns-name","@example.test"),("dns-name","+example.test"),
    ("dns-name","127.0.0.1"),("dns-name","a"*64+".test"),("dns-name","example.com"),
    ("dns-name","EXAMPLE.test"),("dns-name","example.test\n"),
    ("network-target","127.0.0.1"),("network-target","192.0.2.010"),
    ("network-target","2001:0db8::10"),("network-target","fe80::1%eth0"),
    ("network-target","-c"),("network-target","https://example.test"),
    ("local-service","unknown.service"),("local-service","demo.service/../../"),
    ("literal-text","CANARY_SECRET"),("literal-text","a"*257),
    ("literal-text","é"*129),("literal-text","a\u202eb"),("literal-text","a\u0000b"),
    ("literal-text","a\ud800b"),("literal-text","a\ufdd0b"),("literal-text"," x"),
    ("head-tail-direction","head"),("head-tail-direction","tail"),
    ("head-tail-direction","FIRST"),("head-tail-direction","both"),
    ("process-name","-demo-worker"),("process-name",".*"),("process-name","unknown"),
    ("package-id","demo-package:*"),("package-id","Demo-Package"),
    ("package-id","demo-package:amd64:amd64"),("package-id","--help"),
    ("package-query","-demo"),("package-query","@demo"),("package-query",".*"),
    ("package-query","demo\\tools"),("dns-record-type","AAAA"),("dns-record-type","ANY"),
    ("unknown-kind","x"),("literal-text",1),("literal-text",None)
]
for k,x in positive:
    check(lambda:validate_value(v(k,x),c,s),True)
for k,x in negative:
    check(lambda:validate_value(v(k,x),c,s),False)
for obj in ({},{"kind":"literal-text"},{"kind":"literal-text","value":"café","authority":True},
            {"kind":"filename","value":"café"},[],None):
    check(lambda:validate_value(obj,c,s),False)

valid=[
    ("help.command.explain",{"utility":v("utility-id","ss"),"option":v("option-id","--numeric")}),
    ("network.dns.lookup",{"domain":v("dns-name","example.test")}),
    ("network.dns.lookup",{"domain":v("dns-name","example.test"),"record_type":v("dns-record-type","A")}),
    ("network.connectivity.ping",{"target":v("network-target","192.0.2.10")}),
    ("diagnosis.connectivity",{}),
    ("diagnosis.connectivity",{"target":v("local-service","demo.service")}),
    ("file.text.search",{"text":v("literal-text","a+b[1]")}),
    ("file.head_tail.view",{"direction":v("head-tail-direction","last")}),
    ("process.lookup.name",{"name":v("process-name","demo-worker")}),
    ("package.installed.check",{"package":v("package-id","demo-package")}),
    ("package.search.local",{"query":v("package-query","demo")}),
]
for intent,slots in valid:
    check(lambda:validate_slots(intent,slots,c,s),True)
for intent,slots in [
    ("help.command.explain",{"option":v("option-id","--failed")}),
    ("help.command.explain",{"utility":v("utility-id","ss"),"option":v("option-id","--failed")}),
    ("network.dns.lookup",{}),
    ("network.dns.lookup",{"domain":v("dns-name","example.test"),"record_type":v("dns-record-type","AAAA")}),
    ("network.dns.lookup",{"domain":v("dns-name","example.test"),"resolver":v("network-target","192.0.2.10")}),
    ("network.connectivity.ping",{"target":v("dns-name","example.test")}),
    ("file.text.search",{"text":v("filename","a+b[1]")}),
    ("file.head_tail.view",{}),
    ("memory.summary",{}),
]:
    check(lambda:validate_slots(intent,slots,c,s),False)
assert validate_slots("network.dns.lookup",{"domain":v("dns-name","example.test")},c,s)["record_type"] == {
    "value":v("dns-record-type","A"),"provenance":"catalog-default"}
assert validate_slots("network.dns.lookup",{"domain":v("dns-name","example.test"),"record_type":v("dns-record-type","A")},c,s)["record_type"]["provenance"]=="explicit-candidate"

for intent in ("log.service.query","log.system.errors","file.search"):
    for start,end,ref,ok in [
        (100,101,101,True),(100,86500,86500,True),(100,86501,86501,False),
        (100,100,100,False),(101,100,101,False),(100,101,100,False),
        (-1,100,100,False),(True,100,100,False),(100.0,101,101,False),
        (100,101,253402300800,False)
    ]:
        check(lambda:validate_window(intent,start,end,ref,c),ok)
check(lambda:validate_window("memory.summary",0,1,1,c),False)
print("F1_DEFERRED_CONTRACT",counts,"total",sum(counts.values()),
      "10 deferred occurrences/9 intents + DNS A; 3 finite windows;",
      "contract",hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
      "schema",hashlib.sha256(SCHEMA.read_bytes()).hexdigest(),
      "data-only, native IR integration NOT RUN")
