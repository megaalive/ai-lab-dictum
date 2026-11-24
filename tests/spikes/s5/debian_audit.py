"""Read-only provenance of selected Debian package documents (no target executable)."""
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

TARGETS = {
    "procps":["free.1.gz"],"iproute2":["ss.8.gz"],
    "systemd":["systemctl.1.gz","journalctl.1.gz"],
    "coreutils":["df.1.gz","du.1.gz"],"findutils":["find.1.gz"],
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read_file(root,path):
    actual=path.resolve(strict=True)
    assert actual.is_relative_to(root.resolve()) and actual.is_file()
    assert actual.stat().st_size<=8*1024*1024
    return actual.read_bytes()


def main():
    assert len(sys.argv)==2
    directory=Path(sys.argv[1]).resolve(strict=True)
    count=0
    for package,names in TARGETS.items():
        debs=list(directory.glob(package+"_*.deb"))
        assert len(debs)==1
        deb=debs[0]
        assert deb.stat().st_size<=64*1024*1024
        metadata=subprocess.check_output(["dpkg-deb","-f",str(deb),"Package","Version","Architecture"],
                                         timeout=5,text=True).splitlines()
        assert metadata[0]=="Package: "+package
        root=directory/(package+".extracted")
        root.mkdir()
        subprocess.run(["dpkg-deb","-x",str(deb),str(root)],check=True,timeout=20)
        copyright=read_file(root,root/"usr/share/doc"/package/"copyright")
        cptext=copyright.decode("utf-8",errors="replace")
        # Identifiers only, not wholesale upstream text; exact document hash for review.
        licenses=sorted(set(line[9:].strip() for line in cptext.splitlines()
                            if line.startswith("License: ")))[:40]
        for name in names:
            paths=list((root/"usr/share/man").glob("man*/"+name))
            assert len(paths)==1,(package,name)
            raw=read_file(root,paths[0])
            text=gzip.decompress(raw)
            assert len(text)<=2*1024*1024
            header=text[:16000].decode("utf-8",errors="replace")
            # Evidence hints; no assumption package-wide terms cover manpage.
            keywords=sorted(set(re.findall(r"(?i)\b(?:GPL(?:v[23])?|LGPL(?:v[23])?|GFDL|MIT|BSD|CC-BY|copyright|public domain|license)\b",header)))
            print("S5_DOC "+json.dumps({"package":package,"metadata":metadata,
                "deb_sha256":sha(deb.read_bytes()),"copyright_sha256":sha(copyright),
                "license_identifiers":licenses,"path":str(paths[0].relative_to(root)),
                "gzip_sha256":sha(raw),"text_sha256":sha(text),"header_hints":keywords,
                "decision":"HOLD-PER-FILE-RIGHTS"},sort_keys=True))
            count+=1
    print(f"S5 Debian documents: {count}/7 pinned; no target execution, no import; per-file rights HOLD")


if __name__=="__main__":
    main()
