"""Synthetic numeric and feature/scoring differential; never reads a corpus."""
import random
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from b2_linear import CLASSES, DIM, Linear, extract, fit_numeric, rank

probe = sys.argv[1]
rng = random.Random(20261124)
regular = Linear(
    [[((c+3)*(i+7)+i//17)%23-11 for i in range(DIM)] for c in range(CLASSES)],
    [c%11-5 for c in range(CLASSES)],
)
zero = Linear.zero()
checks = 0
def check(raw, masks=(), mode="regular"):
    global checks
    frame = bytes([len(masks)]) + b"".join(struct.pack("<HH", a,b) for a,b in masks) + raw
    p = subprocess.run([probe, mode], input=frame, capture_output=True, check=True, timeout=5)
    assert not p.stderr
    try:
        features = extract(raw,masks)
    except (ValueError, UnicodeError):
        assert p.stdout == b"reject\n"
    else:
        model = zero if mode == "tie" else regular
        scores = model.scores(features)
        expected = rank(features, scores, 1000 if mode == "margin" else 1)
        lines = p.stdout.decode("ascii").splitlines()
        assert len(lines) == 3
        assert int(lines[0]) == expected
        assert tuple(map(int, lines[1].split())) == features
        assert tuple(map(int, lines[2].split())) == scores
    checks += 1

for raw,masks in [
    (b"one TWO one",()), (b"one TWO one",((4,7),)),
    (b"before abc.def after",((7,14),)),
    (b"before abc.def after",((8,9),)), ("café word".encode(),((0,5),)),
    ("café word".encode(),((4,5),)), (b"abc",((0,3),)),
    (b"abc",((2,1),)), (b"abc",((0,2),(1,3))), (b"abc",((1,4),)),
    (b"abc",((0,0),)), (b"x\x00y",()), (b"\xff",()), (b"",()),
    ("x\ufdd0".encode(),()), (b"x"*4097,()), (b"x"*4096,()), (b"---",()),
]:
    for mode in ("regular","tie","margin"):
        check(raw,masks,mode)

alphabet = b"abcXYZ0123-_. "
for _ in range(180):
    raw = bytes(rng.choice(alphabet) for _ in range(rng.randint(1,180)))
    a = rng.randrange(len(raw))
    b = rng.randrange(a+1,len(raw)+1)
    check(raw, ((a,b),), rng.choice(("regular","tie","margin")))
# Masked lexical words do not affect features, even across punctuation.
assert extract(b"before alpha.beta after",((7,17),)) == extract(b"before gamma/zeta after",((7,17),))
# Abstract features only. No text labels, project intent corpus, or actual model.
rows = [((1,2),0),((3,4),1),((5,6),2),((1,7),0),((3,8),1),((5,9),2)]
a = fit_numeric(rows, epochs=12, seed=7)
b = fit_numeric(rows, epochs=12, seed=7)
assert a == b
assert all(rank(f,a.scores(f)) == c for f,c in rows)
assert rank((1,),zero.scores((1,))) == -1
assert rank((),regular.scores(())) == -1
for invalid in [[], [((2,1),0)], [((1,1),0)], [((DIM,),0)], [((1,),CLASSES)]]:
    try:
        fit_numeric(invalid,epochs=1,seed=1)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid training row")
print(f"F1_B2_MECHANICS {checks} native/Python feature+score+rank checks; 6 abstract training rows, deterministic numeric fit; actual B2 NOT RUN")
