"""Check that every tracked file in a clean CI checkout equals its index blob.

No source normalization or hash exception. Run from an isolated checkout,
including on Windows with core.autocrlf=true.
"""
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def git(*args, data=None):
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(ROOT), *args],
        input=data, timeout=30,
    )


def main():
    if git("rev-parse", "--show-object-format").strip() != b"sha1":
        raise SystemExit("unexpected object format")
    if git("config", "--get", "core.autocrlf").strip() != b"true":
        raise SystemExit("autocrlf=true required for checkout regression")
    git("diff", "--cached", "--quiet", "HEAD", "--")
    entries = []
    for record in git("ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        meta, path = record.split(b"\t", 1)
        mode, oid, stage = meta.split(b" ")
        if mode not in (b"100644", b"100755") or stage != b"0":
            raise SystemExit("unexpected index entry type/stage")
        entries.append((path, oid))
    if not entries:
        raise SystemExit("empty checkout")
    attributes = git("check-attr", "-z", "--stdin", "text",
                     data=b"".join(path + b"\0" for path, _ in entries)).split(b"\0")
    expected = [part for path, _ in entries for part in (path, b"text", b"unset")] + [b""]
    if attributes != expected:
        raise SystemExit("tracked path lacks byte-preserving text attribute")
    failures = []
    for path, oid in entries:
        p = ROOT / path.decode("utf-8", "strict")
        if p.is_symlink() or not p.is_file():
            failures.append(path.decode())
            continue
        data = p.read_bytes()
        actual = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest().encode()
        if actual != oid:
            failures.append(path.decode())
    if failures:
        raise SystemExit("working-tree byte drift: " + ", ".join(failures))
    print("CHECKOUT_BYTES", len(entries), "tracked files match exact index blobs;",
          "core.autocrlf=true; all text attributes unset; no hash normalization")


if __name__ == "__main__":
    main()
