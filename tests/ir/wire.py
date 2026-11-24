"""Pemeriksaan byte dan JSON sebelum validasi schema."""

import json


MAX_INPUT = 4096
MAX_FRAME = 32768
MAX_DEPTH = 12
MAX_STRING = 4096
MAX_ITEMS = 64
MAX_MEMBERS = 32
MAX_INTEGER = (1 << 53) - 1
WHITESPACE = " \t\r\n"


class Reject(Exception):
    def __init__(self, layer, code):
        super().__init__(f"{layer}/{code}")


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise Reject("byte", "duplicate-key")
        result[name] = value
    return result


def integer(token):
    if token == "-0":
        raise Reject("byte", "number-syntax")
    if len(token.removeprefix("-")) > 16:
        raise Reject("byte", "integer-range")
    value = int(token)
    if not -MAX_INTEGER <= value <= MAX_INTEGER:
        raise Reject("byte", "integer-range")
    return value


def reject_number(_token):
    raise Reject("byte", "number-syntax")


def reject_nonfinite(_token):
    raise Reject("byte", "nonfinite")


def check_noncharacters(text):
    for character in text:
        codepoint = ord(character)
        if 0xFDD0 <= codepoint <= 0xFDEF or (codepoint & 0xFFFF) >= 0xFFFE:
            raise Reject("byte", "noncharacter")


def scalar_bytes(text):
    if "\x00" in text:
        raise Reject("byte", "nul")
    try:
        data = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise Reject("byte", "surrogate") from exc
    check_noncharacters(text)
    return data


def decode_utf8(data):
    if b"\x00" in data:
        raise Reject("byte", "nul")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise Reject("byte", "utf8") from exc


def check_input(data):
    if not 1 <= len(data) <= MAX_INPUT:
        raise Reject("byte", "input-size")
    check_noncharacters(decode_utf8(data))
    return data


def check_depth(text):
    # Batasi nesting sebelum memanggil decoder rekursif. Decoder memeriksa grammar.
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise Reject("byte", "depth")
        elif character in "]}":
            depth -= 1
            if depth < 0:
                raise Reject("byte", "json-syntax")


def check_decoded(value):
    if isinstance(value, str):
        if len(scalar_bytes(value)) > MAX_STRING:
            raise Reject("byte", "string-size")
    elif isinstance(value, list):
        if len(value) > MAX_ITEMS:
            raise Reject("byte", "array-size")
        for item in value:
            check_decoded(item)
    elif isinstance(value, dict):
        if len(value) > MAX_MEMBERS:
            raise Reject("byte", "object-size")
        for key, item in value.items():
            check_decoded(key)
            check_decoded(item)


def decode_frame(data):
    if len(data) > MAX_FRAME:
        raise Reject("byte", "frame-size")
    if data.startswith(b"\xef\xbb\xbf"):
        raise Reject("byte", "bom")
    text = decode_utf8(data)
    check_depth(text)
    decoder = json.JSONDecoder(
        object_pairs_hook=unique_object,
        parse_int=integer,
        parse_float=reject_number,
        parse_constant=reject_nonfinite,
    )
    try:
        value, end = decoder.raw_decode(text, len(text) - len(text.lstrip(WHITESPACE)))
    except json.JSONDecodeError as exc:
        raise Reject("byte", "json-syntax") from exc
    if text[end:].strip(WHITESPACE):
        raise Reject("byte", "trailing-data")
    check_decoded(value)
    return value


def read_source(path):
    # File spesifikasi dan fixture adalah artefak repo, bukan frame objek IR.
    with path.open(encoding="utf-8") as source:
        return json.load(source, object_pairs_hook=unique_object, parse_constant=reject_nonfinite)
