"""Actual product CLI; no target operation execution. Isolated synthetic lab only."""
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from catalog_lookup import rows as catalog_rows, check as check_catalog, check_inspect

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location("s1_harness",ROOT/"tests/spikes/s1/run.py")
s1=importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1)
CLI=str(Path(sys.argv[1]).resolve())
CASES=json.loads((HERE/"functional-v1.json").read_text())["cases"] + json.loads((HERE/"f1-functional-v1.json").read_text())["cases"] + json.loads((HERE/"f1-v2-functional.json").read_text())["cases"]
CANARIES=(b"CANARY_SECRET",b"DCT008_CANARY",b"CANARY_SECRET_CONTENT_FIXTURE_V1",b"CANARY_SECRET_CONTENT_FIXTURE_V2")

# The trace must contain exactly one initial execve of the product and no
# later process creation or networking attempt. No target path may be read.
# Fixed paths are loader/process metadata only, not target data access.
LOADER_PATHS={"","/etc/ld.so.preload","/etc/ld.so.cache","/proc/self/exe",
              "/lib/x86_64-linux-gnu/libcrypto.so.3","/usr/lib/x86_64-linux-gnu/libcrypto.so.3",
              "/lib/x86_64-linux-gnu/libc.so.6","/usr/lib/x86_64-linux-gnu/libc.so.6",
              # Exact transitive dependencies observed in native CI ldd (run 45367398117).
              "/lib/x86_64-linux-gnu/libz.so.1","/usr/lib/x86_64-linux-gnu/libz.so.1",
              "/lib/x86_64-linux-gnu/libzstd.so.1","/usr/lib/x86_64-linux-gnu/libzstd.so.1"}
READ_ONLY={"access","faccessat","faccessat2","stat","lstat","fstat","newfstatat","statx",
           "readlink","readlinkat","getcwd"}
OPENS={"open","openat","openat2"}


def need(condition,code):
    if not condition:
        raise AssertionError(code)


def check_trace(raw,diagnose=False):
    need(0<len(raw)<s1.CAP,"trace-size")
    need(not any(c in raw for c in CANARIES),"trace-canary")
    count=0
    for line in raw.decode("utf-8",errors="strict").splitlines():
        m=re.match(r"^\s*\d+\s+([a-zA-Z0-9_]+)\(",line)
        need(m is not None,"trace-unparsed")
        name=m.group(1)
        if name=="execve":
            count+=1
            need(count==1 and re.search(r'execve\("'+re.escape(CLI)+r'",',line) and
                 re.search(r"=\s*0$",line),"unexpected-exec")
            continue
        if name in {"exit","exit_group"}:
            continue
        need(name in OPENS or name in READ_ONLY,"forbidden-syscall-"+name)
        if name in OPENS:
            need("O_RDONLY" in line and not re.search(r"\bO_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND|TMPFILE)\b",line),
                 "file-mutation")
        # For fstat there is no path; for stat/readlink the first string is
        # the path, subsequent strings are result buffers, not access targets.
        quoted=re.search(r'"((?:\\.|[^"\\])*)"',line)
        if quoted is not None:
            path=quoted.group(1)
            if diagnose and path not in LOADER_PATHS:
                # Fixed --version input in disposable synthetic image only; never log raw argv.
                print("PREFLIGHT unexpected path",repr(path),flush=True)
            need(path in LOADER_PATHS,"non-loader-file")
        else:
            need(name in {"fstat","getcwd"},"missing-file-path")
    need(count==1,"missing-initial-exec")


def guard_regression():
    initial=f'1 execve("{CLI}", [], []) = 0\n'
    tail="1 exit_group(0) = ?\n"
    good='1 openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3\n'
    check_trace((initial+good+tail).encode())
    bad=[
        '1 execve("/fixture/bin/argv-dumper", [], []) = 0\n',
        '1 execveat(3, "", [], [], AT_EMPTY_PATH) = 0\n',
        '1 clone(NULL, 0) = 2\n',
        '1 socket(AF_INET, SOCK_STREAM, 0) = -1 EPERM (Operation not permitted)\n',
        '1 connect(3, NULL, 0) = -1 EPERM (Operation not permitted)\n',
        '1 io_uring_setup(1, NULL) = -1 EPERM (Operation not permitted)\n',
        '1 openat(AT_FDCWD, "/fixture/data/.env", O_RDONLY) = 3\n',
        '1 openat(AT_FDCWD, "/etc/ld.so.cache", O_RDWR) = 3\n',
        '1 stat("/fixture/data/escape", NULL) = 0\n',
        '1 unlink("/fixture/data/.env") = 0\n',
        '1 openat(AT_FDCWD, "/tmp/CANARY_SECRET", O_RDONLY) = -1 ENOENT (No such file or directory)\n',
    ]
    for line in bad:
        try:
            check_trace((initial+line+tail).encode())
        except AssertionError:
            pass
        else:
            raise AssertionError("trace-guard-negative")
    print("C06 trace guard",len(bad)+1,"synthetic cases")


def traced(args,trace,cwd):
    trace.unlink(missing_ok=True)
    env={"LC_ALL":"C.UTF-8","TZ":"UTC","TERM":"dumb","PATH":"/usr/bin:/bin",
         "HOME":str(cwd),"OPENSSL_CONF":"/tmp/CANARY_SECRET_CONFIG",
         "OPENSSL_MODULES":"/tmp/CANARY_SECRET_MODULES"}
    command=[s1.STRACE,"-f","-qq","-s","0","-e",
             "trace=%process,%network,%file,io_uring_setup,io_uring_enter,io_uring_register",
             "-o",str(trace),CLI,*args]
    rc,out,err=s1.bounded_process(command,cwd,env)
    check_trace(trace.read_bytes(),diagnose=(args==["--version"]))
    trace.unlink()
    need(not any(c in out+err for c in CANARIES),"output-canary")
    need(not list(cwd.iterdir()),"cwd-mutation")
    return rc,out,err


def main():
    s1.preflight()
    guard_regression()
    need(Path("/fixture/data/.env").is_file() and Path("/fixture/data/escape").is_symlink(),"fixture-not-seeded")
    hashes={str(p):s1.sha(p) for p in (CLI,"/fixture/data/.env","/fixture/private/hidden")}
    print("actual-product sha256="+hashes[CLI]+"; synthetic canary fixture present")
    checks=0
    with tempfile.TemporaryDirectory(prefix="dictum-c06-") as tmp:
        cwd=Path(tmp)/"empty"
        cwd.mkdir()
        trace=Path(tmp)/"trace"
        # Preflight must launch actual CLI once and classify its trace.
        rc,out,err=traced(["--version"],trace,cwd)
        need(rc==0 and out.startswith(b"dictum ") and not err,"actual-preflight")
        checks+=1
        for row in CASES:
            if "text" in row:
                raw=row["text"]
            elif "hex" in row:
                raw=bytes.fromhex(row["hex"])
                if b"\0" in raw or not raw:  # OS argv cannot carry NUL; empty handled separately.
                    continue
            else:
                raw=row["repeat"][0]*row["repeat"][1]
            expected=row["expected"]["decision"]
            try:
                rc,out,err=traced(["ask",raw],trace,cwd)
                need(rc=={"allow-proposal":0,"unsupported":3,"deny":4,"clarify":5}[expected],"exit")
                need(not err,"stderr")
                view=json.loads(out)
                need(view["decision"]==expected and view["copyability"]=="NON_COPYABLE" and
                     "command" not in view and "preview" not in view and
                     not view["execution_allowed"] and not view["observed_os_data"],"view")
            except (AssertionError,ValueError,OSError,KeyError) as exc:
                print("C06/C07 FAIL",row["id"],type(exc).__name__,
                      str(exc) if isinstance(exc,AssertionError) else "redacted",flush=True)
                raise SystemExit(1)
            checks+=1
        for args,expected in [(["ask",""],2),(["inspect"],0),(["search","memory.summary"],0),
            (["search","CANARY_SECRET"],3),(["explain","show available memory"],0),
            (["show available memory"],0),(["run"],4),(["run","CANARY_SECRET"],4),
            (["run","restart demo.service","--force"],4),
            (["ask","ukuran folder /fixture/data/escape"],4),
            (["ask","find files named CANARY_SECRET under /fixture/data"],4)]:
            rc,out,err=traced(args,trace,cwd)
            need(rc==expected,"extra-cli-exit")
            checks+=1
        # Additional F1 catalog-only paths: execute actual CLI, no product target access.
        for row,binding in catalog_rows():
            rc,out,err=traced(["search",row["id"]],trace,cwd)
            need(rc==0 and not err,"catalog-trace-exit")
            check_catalog(json.loads(out),row,binding)
            checks+=1
        rc,out,err=traced(["inspect"],trace,cwd)
        need(rc==0 and not err,"inspect-trace-exit")
        check_inspect(json.loads(out))
        checks+=1
    need(all(s1.sha(p)==h for p,h in hashes.items()),"fixture-mutation")
    print("C06_C07_ACTUAL_CLI",checks,"initial launches",checks,
          "post-launch execs 0; process spawn 0; network attempts 0; target file access 0; canary leaks 0")
    print("Scope: actual synthetic CLI Release artifact, no utility execution; descriptor/host/VM/FES NOT RUN")

if __name__=="__main__":
    main()
