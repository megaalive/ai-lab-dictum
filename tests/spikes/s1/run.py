"""S1 inert lab. Only the fixture dumper may be invoked by the clean shells."""
import hashlib
import json
import os
import random
import re
import resource
import selectors
import signal
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/"tests/renderer"))
from run import render, IDENTITY  # development fixture, never product trust

SEED = 20261124
SHELL = {"bash-posix-clean-v1": ("/usr/bin/bash", "--noprofile", "--norc", "--posix"),
         "dash-clean-v1": ("/usr/bin/dash",)}
DUMPER = "/fixture/bin/argv-dumper"
STRACE = "/usr/bin/strace"
CAP = 65536
DEADLINE = 5.0
# Literal fragments only. No real commands. Construct acceptance independently of render.
FRAGMENTS = ["alpha", "a b", "O'Brien", "'", '"', r"back\slash", "café",
             "cafe\u0301", "日本語", "Bahasa", "*?[x]", "$HOME", "$()",
             "\x60INERT_MARKER\x60", "; INERT_MARKER", "|&<>", "-literal",
             "  ", "a'b'c", "é"*100]
INVALID = [b"\xc0\x80", b"\xff", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xe2\x82"]
BAD = ["\0", "\n", "\r", "\t", "\x1b", "\x7f", "\x85", "\u202e",
       "\u2066", "\u200b", "\u2028", "\u2029", "\ufdd0", "\ufe0f", "\u034f"]


class Blocked(RuntimeError):
    pass


def need(ok, code):
    if not ok:
        raise AssertionError(code)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preflight():
    status = Path("/proc/self/status").read_text()
    if (os.getuid() == 0 or not re.search(r"^CapEff:\s+0+$",status,re.M)
            or not re.search(r"^NoNewPrivs:\s+1$",status,re.M)
            or sorted(os.listdir("/sys/class/net")) != ["lo"]
            or not os.statvfs("/").f_flag & os.ST_RDONLY):
        raise Blocked("inert-container-boundary")
    for path in (DUMPER, STRACE, *(v[0] for v in SHELL.values())):
        if not Path(path).is_file() or not os.access(path, os.X_OK):
            raise Blocked("missing-pinned-fixture-tool")
        print(f"fixture-tool {path} sha256={sha(path)}")
    # Keep trace logs bounded even if a fixture unexpectedly misbehaves.
    resource.setrlimit(resource.RLIMIT_FSIZE, (CAP, CAP))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    print("preflight: nonroot, caps=0, no-new-privileges, lo-only, root read-only")


def case(cid, shell, args, recipe="fixture-end", gate="verified-fixture"):
    return {"id":cid,"shell":shell,"gate":gate,"recipe":recipe,"expected":{},
            "action":{"kind":"proposal-only","operation":{
                "kind":"executable","identity":dict(IDENTITY),"argv":args}}}


def lit(s):
    return {"kind":"literal","value":s}


def generated(profile):
    rng = random.Random(SEED)
    for n in range(7000):
        cid = f"{profile}-a-{n:04d}"
        if n % 25 == 0:
            values = ["x"*1024, "", "'"*30]
        else:
            values = ["".join(rng.choices(FRAGMENTS,k=rng.randint(1,4)))
                      for _ in range(rng.randint(1,4))]
            if n % 11 == 0:
                values.append("")
        # Known grammar: -- followed by literals; "-" alone has special meaning.
        yield case(cid,profile,[{"kind":"option-end"},*[lit(x) for x in values]]), \
            [DUMPER,"--",*values], None
    for n in range(3000):
        cid = f"{profile}-r-{n:04d}"
        kind = n % 10
        marker = f"CANARY_SECRET_{n}"
        if kind == 0:
            yield case(cid,profile,[]), None, INVALID[n % len(INVALID)]
            continue
        args = [{"kind":"option-end"},lit(marker)]
        c = case(cid,profile,args)
        if kind == 1:
            args[1] = lit(marker+BAD[n//10 % len(BAD)])
        elif kind == 2:
            args[1] = lit("é"*513+marker)
        elif kind == 3:
            c["shell"] = "unknown"
        elif kind == 4:
            args[1] = lit("-")
        elif kind == 5:
            c["gate"] = "blocked"
        elif kind == 6:
            c["recipe"] = "fixture-no-end"
            c["action"]["operation"]["argv"] = [lit("-"+marker)]
        elif kind == 7:
            c["action"]["kind"] = "execution-candidate"
        elif kind == 8:
            c["action"]["operation"]["argv"] = [lit("x")]*33
        elif kind == 9:
            c["action"]["operation"]["argv"] = [
                {"kind":"option-end"}, *[lit("'"*1024) for _ in range(10)]]
        yield c, None, None


def safe_decode_preview(preview):
    """Independent byte lexer for exactly one sequence of quoted literals.
    No shell parsing, no shlex fallback. The only outside-quote escape is
    the exact quote-escape sequence; no other unquoted byte is accepted.
    """
    b = preview.encode("utf-8",errors="strict")
    need(0 < len(b) <= 32768, "preview-size")
    i = 0
    tokens = []
    while i < len(b):
        need(b[i:i+1] == b"'", "opening-quote")
        i += 1
        token = bytearray()
        while True:
            j = b.find(b"'",i)
            need(j >= i, "unclosed-quote")
            token.extend(b[i:j])
            i = j+1
            if b[i:i+3] == b"\\''":
                token.append(39)
                i += 3
            else:
                break
        need(len(token) <= 1024,"token-bound")
        tokens.append(bytes(token))
        if i == len(b):
            break
        need(b[i:i+1] == b" " and i+1 < len(b),"separator")
        i += 1
    need(1 <= len(tokens) <= 33 and tokens[0] == DUMPER.encode(), "fixed-dumper")
    return tokens


def decode_record(data):
    need(len(data)>=4,"record-header")
    count, = struct.unpack_from("<I",data)
    need(1<=count<=33,"record-count")
    pos = 4
    result = []
    for _ in range(count):
        need(pos+4<=len(data),"record-length")
        n, = struct.unpack_from("<I",data,pos)
        pos += 4
        need(n<=1024 and n<=len(data)-pos,"record-token")
        result.append(data[pos:pos+n])
        pos += n
    need(pos==len(data),"record-trailing")
    return result


def bounded_process(argv,cwd,env):
    # Only called after exact argv lexing and trusted fixture selection.
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    buffers = [bytearray(),bytearray()]
    deadline = time.monotonic()+DEADLINE
    try:
        with selectors.DefaultSelector() as sel:
            for i,p in enumerate((proc.stdout,proc.stderr)):
                sel.register(p,selectors.EVENT_READ,i)
            while sel.get_map():
                left = deadline-time.monotonic()
                need(left>0,"timeout")
                ready = sel.select(left)
                need(bool(ready),"timeout")
                for key,_ in ready:
                    block = os.read(key.fileobj.fileno(),8192)
                    if not block:
                        sel.unregister(key.fileobj)
                    else:
                        buffers[key.data].extend(block)
                        need(sum(map(len,buffers))<=CAP,"output-cap")
        rc = proc.wait(timeout=max(.01,deadline-time.monotonic()))
        return rc,bytes(buffers[0]),bytes(buffers[1])
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGKILL)
            proc.wait(timeout=2)
        proc.stdout.close()
        proc.stderr.close()


# Trace classification is fail-closed: unknown file/process/network calls fail.
READ_ONLY = {"access","faccessat","faccessat2","stat","lstat","fstat",
             "newfstatat","statx","readlink","readlinkat","getcwd","statfs",
             "fstatfs","getdents","getdents64"}
PROCESS = {"wait4","waitid","exit","exit_group","clone","clone3","fork","vfork"}
OPENS = {"open","openat","openat2"}


def check_trace(raw, shell):
    need(0<len(raw)<CAP,"trace-size")
    lines = raw.decode("utf-8",errors="backslashreplace").splitlines()
    execs = []
    for line in lines:
        # strace -f output prefixes PID; unfinished/resumed process calls allowed.
        m = re.match(r"^\s*\d+\s+([a-zA-Z0-9_]+)\(",line)
        if not m:
            if re.match(r"^\s*\d+\s+(<\.\.\. (?:wait4|waitid|clone|clone3|fork|vfork|execve) resumed>|--- SIGCHLD )",line):
                continue
            raise AssertionError("trace-unparsed")
        name = m.group(1)
        if name == "execve":
            p = re.search(r'execve\("([^"]+)"',line)
            need(p is not None,"trace-exec-path")
            execs.append(p.group(1))
        elif name in OPENS:
            need("O_RDONLY" in line and not re.search(
                r"\bO_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND|TMPFILE)\b",line),"trace-write")
        else:
            need(name in READ_ONLY or name in PROCESS,"trace-forbidden-"+name)
    need(execs==[shell,DUMPER],"unexpected-exec")


def roundtrip(preview, expected, profile, trace, cwd):
    want = [s.encode("utf-8") for s in expected]
    need(safe_decode_preview(preview)==want,"literal-lexer-mismatch")
    env = {"LC_ALL":"C.UTF-8","TZ":"UTC","TERM":"dumb",
           "HOME":str(cwd),"PATH":"/usr/bin:/bin"}
    need(not list(cwd.iterdir()),"dirty-fixture-before")
    trace.unlink(missing_ok=True)
    command = [STRACE,"-f","-qq","-s","80","-e","trace=%process,%network,%file",
               "-o",str(trace),*SHELL[profile],"-c",preview]
    rc,out,err = bounded_process(command,cwd,env)
    need(rc==0 and not err,"shell-or-dumper-error")
    need(decode_record(out)==want,"argv-mismatch")
    check_trace(trace.read_bytes(),SHELL[profile][0])
    need(not list(cwd.iterdir()),"fixture-mutation")
    trace.unlink()


def run_profile(profile):
    preflight()
    shell,dump = SHELL[profile][0],DUMPER
    initial = (sha(shell),sha(dump))
    accepted = rejected = 0
    corpus = hashlib.sha256()
    ids = set()
    with tempfile.TemporaryDirectory(prefix="s1-") as temp:
        root = Path(temp)
        cwd = root/"empty"
        cwd.mkdir()
        trace = root/"trace"
        # Verify tracer functionality on one inert fixed probe before generated cases.
        probe = case("preflight",profile,[{"kind":"option-end"},lit("probe")])
        try:
            result = render(probe)
            roundtrip(result["preview"],[DUMPER,"--","probe"],profile,trace,cwd)
        except (AssertionError,KeyError,OSError,subprocess.TimeoutExpired) as exc:
            raise Blocked("tracer-or-inert-preflight:"+str(exc)) from exc
        print(f"S1 preflight round-trip verified profile={profile}",flush=True)
        for c,expected,invalid in generated(profile):
            cid = c["id"]
            need(cid not in ids,"duplicate-id")
            ids.add(cid)
            corpus.update(json.dumps([c,expected,invalid.hex() if invalid else None],
                          ensure_ascii=True,sort_keys=True,separators=(",",":")).encode()+b"\n")
            try:
                if invalid is not None:
                    try:
                        invalid.decode("utf-8",errors="strict")
                    except UnicodeError:
                        rejected += 1
                    else:
                        raise AssertionError("invalid-byte-accepted")
                else:
                    result = render(c)
                    if expected is None:
                        need(set(result)=={"kind","reason"} and result["kind"]=="NON_COPYABLE"
                             and "CANARY_SECRET" not in json.dumps(result),"reject-copyable")
                        rejected += 1
                    else:
                        need(result["kind"]=="COPYABLE","expected-copyable")
                        roundtrip(result["preview"],expected,profile,trace,cwd)
                        accepted += 1
            except (AssertionError, OSError, KeyError, subprocess.TimeoutExpired) as exc:
                print(f"S1 FAIL profile={profile} id={cid} reason={exc}",flush=True)
                raise
            if len(ids)%1000==0:
                print(f"S1 progress {profile} {len(ids)}/10000",flush=True)
        # A4 fixed copyable golden vectors independently decode the literal bytes.
        # Golden expected preview is checked by original A4 oracle; actual shell argv
        # uses the explicit typed input, not lexer output as expected oracle.
        gold = json.loads((ROOT/"tests/renderer/fixtures/preview-v1.json").read_text())
        edge = 0
        for c in gold["cases"]:
            if c["shell"] != profile or c["expected"]["kind"] != "COPYABLE":
                continue
            result = render(c)
            need(result==c["expected"],"golden-preview")
            args = c["action"]["operation"]["argv"]
            want = [DUMPER]+["--" if a["kind"]=="option-end" else
                             str(a["value"]) for a in args]
            roundtrip(result["preview"],want,profile,trace,cwd)
            edge += 1
    need((accepted,rejected,len(ids))==(7000,3000,10000),"denominator")
    need((sha(shell),sha(dump))==initial,"tool-identity-change")
    print(f"S1 PASS {profile} generated=10000 accepted={accepted} rejected={rejected} "
          f"edge={edge} mismatch=0 unintended_exec=0 seed={SEED} corpus_sha256={corpus.hexdigest()}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in SHELL:
        raise SystemExit(2)
    print(f"Python {sys.version.split()[0]} Unicode {unicodedata.unidata_version}",flush=True)
    try:
        run_profile(sys.argv[1])
    except Blocked as exc:
        print(f"S1 BLOCKED: {exc}; no generated shell invocation",flush=True)
        raise SystemExit(2)
