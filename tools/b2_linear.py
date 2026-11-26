"""Development-only B2 numeric mechanics; no corpus reader or model loader.

Eligible corpus/feature manifest must be bound to actual owner scope.
Nothing here reads repository gold or authorizes product use.
"""
from dataclasses import dataclass
import random

CLASSES = 48
DIM = 1024
MAX_MASKS = 32
MAX_INPUT = 4096


def _valid_input(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT or b"\x00" in raw:
        raise ValueError("input")
    text = raw.decode("utf-8", "strict")
    if any(0xFDD0 <= ord(c) <= 0xFDEF or ord(c) & 0xFFFF in (0xFFFE, 0xFFFF) for c in text):
        raise ValueError("noncharacter")


def extract(raw, masks=()):
    _valid_input(raw)
    if len(masks) > MAX_MASKS:
        raise ValueError("mask-count")
    end = 0
    for a, b in masks:
        if type(a) is not int or type(b) is not int or not end <= a < b <= len(raw):
            raise ValueError("mask-order")
        raw[a:b].decode("utf-8", "strict")
        end = b
    def word(c):
        return 65 <= c <= 90 or 97 <= c <= 122 or 48 <= c <= 57 or c >= 128
    seen = set()
    p = m = 0
    while p < len(raw):
        if not word(raw[p]):
            p += 1
            continue
        start = p
        h = 2166136261
        while p < len(raw) and word(raw[p]):
            c = raw[p]
            p += 1
            if 65 <= c <= 90:
                c += 32
            h = ((h ^ c) * 16777619) & 0xFFFFFFFF
        while m < len(masks) and masks[m][1] <= start:
            m += 1
        if m < len(masks) and masks[m][0] < p:
            continue
        seen.add(h % DIM)
    return tuple(sorted(seen))


def validate_features(features):
    if (len(features) > DIM or any(type(x) is not int or not 0 <= x < DIM for x in features)
            or any(a >= b for a, b in zip(features, features[1:]))):
        raise ValueError("features")


@dataclass
class Linear:
    weights: list
    bias: list

    @classmethod
    def zero(cls):
        return cls([[0] * DIM for _ in range(CLASSES)], [0] * CLASSES)

    def scores(self, features):
        validate_features(features)
        return tuple(self.bias[c] + sum(self.weights[c][i] for i in features)
                     for c in range(CLASSES))


def rank(features, scores, margin=1):
    validate_features(features)
    bound = 32768 * (DIM + 1)
    if (len(scores) != CLASSES or type(margin) is not int or not 1 <= margin <= 0xFFFFFFFF
            or any(type(s) is not int or not -bound <= s <= bound for s in scores)):
        raise ValueError("scores")
    if not features:
        return -1
    order = sorted(range(CLASSES), key=lambda c: (-scores[c], c))
    return order[0] if scores[order[0]] - scores[order[1]] >= margin else -1


def fit_numeric(rows, *, epochs, seed):
    """Bounded multiclass perceptron on *already authorized* numeric rows.

    No text ingestion, split construction, evaluation or serialization.
    Caller owns the rights/label gate: private human evidence or DEC-011
    original synthetic development. Never use visible regression/holdout labels.
    """
    if type(epochs) is not int or not 1 <= epochs <= 32 or not 1 <= len(rows) <= 10000:
        raise ValueError("budget")
    for f, c in rows:
        validate_features(f)
        if not f or type(c) is not int or not 0 <= c < CLASSES:
            raise ValueError("row")
    model = Linear.zero()
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    for _ in range(epochs):
        rng.shuffle(indices)
        for j in indices:
            f, expected = rows[j]
            scores = model.scores(f)
            predicted = max(range(CLASSES), key=lambda c: scores[c])
            if expected == predicted:
                continue
            for c, delta in ((expected, 1), (predicted, -1)):
                model.bias[c] = max(-32767, min(32767, model.bias[c] + delta))
                for i in f:
                    model.weights[c][i] = max(-32767, min(32767, model.weights[c][i] + delta))
    return model


def fit_averaged_numeric(rows, *, epochs, seed, scale=8):
    """Averaged multiclass perceptron on authorized numeric train rows only.

    Exact integer timestamp accumulation of post-update weights, with a
    fixed signed round-to-nearest (ties away from zero) int16 quantization.
    No features or labels outside the supplied training rows.
    """
    if (type(epochs) is not int or not 1 <= epochs <= 32 or
            not 1 <= len(rows) <= 10000 or type(scale) is not int or not 1 <= scale <= 16):
        raise ValueError("budget")
    for f, c in rows:
        validate_features(f)
        if not f or type(c) is not int or not 0 <= c < CLASSES:
            raise ValueError("row")
    model = Linear.zero()
    totals = {}
    last = {}
    rng = random.Random(seed)
    indices = list(range(len(rows)))
    step = 0
    for _ in range(epochs):
        rng.shuffle(indices)
        for j in indices:
            f, expected = rows[j]
            scores = model.scores(f)
            predicted = max(range(CLASSES), key=lambda c: scores[c])
            if expected != predicted:
                for c, delta in ((expected, 1), (predicted, -1)):
                    # DIM is a separate bias coordinate, not a feature ID.
                    for i in (*f, DIM):
                        key = (c, i)
                        old = model.bias[c] if i == DIM else model.weights[c][i]
                        totals[key] = totals.get(key, 0) + (step-last.get(key, 0))*old
                        last[key] = step
                        new = max(-32767, min(32767, old+delta))
                        if i == DIM:
                            model.bias[c] = new
                        else:
                            model.weights[c][i] = new
            step += 1
    result = Linear.zero()
    for (c, i), total in totals.items():
        old = model.bias[c] if i == DIM else model.weights[c][i]
        summed = total+(step-last[(c,i)])*old
        magnitude = (2*abs(summed)*scale+step)//(2*step)
        quantized = max(-32767,min(32767,-magnitude if summed < 0 else magnitude))
        if i == DIM:
            result.bias[c] = quantized
        else:
            result.weights[c][i] = quantized
    return result
