#include "ir_wire.h"

#include <stdlib.h>
#include <string.h>

struct parser {
    struct ir_document *doc;
    const unsigned char *data;
    size_t size, pos;
};

static bool continuation(unsigned char c)
{
    return (c & 0xc0u) == 0x80u;
}

static bool noncharacter(uint32_t cp)
{
    return (cp >= 0xfdd0u && cp <= 0xfdefu) || (cp & 0xffffu) >= 0xfffeu;
}

/* No reads beyond size, including a truncated scalar. */
static enum ir_status scalar(const unsigned char *data, size_t size,
                             size_t *pos, uint32_t *out)
{
    if (*pos >= size) {
        return IR_UTF8;
    }
    const unsigned char c = data[(*pos)++];
    uint32_t cp;
    unsigned int extra;
    uint32_t minimum;
    if (c < 0x80u) {
        *out = c;
        return IR_OK;
    }
    if (c >= 0xc2u && c <= 0xdfu) {
        cp = c & 0x1fu; extra = 1; minimum = 0x80u;
    } else if (c >= 0xe0u && c <= 0xefu) {
        cp = c & 0x0fu; extra = 2; minimum = 0x800u;
    } else if (c >= 0xf0u && c <= 0xf4u) {
        cp = c & 7u; extra = 3; minimum = 0x10000u;
    } else {
        return IR_UTF8;
    }
    if ((size_t)extra > size - *pos) {
        return IR_UTF8;
    }
    for (unsigned int i = 0; i < extra; ++i) {
        const unsigned char tail = data[(*pos)++];
        if (!continuation(tail)) {
            return IR_UTF8;
        }
        cp = (cp << 6) | (tail & 0x3fu);
    }
    if (cp < minimum || cp > 0x10ffffu || (cp >= 0xd800u && cp <= 0xdfffu)) {
        return IR_UTF8;
    }
    *out = cp;
    return IR_OK;
}

static enum ir_status utf8(const unsigned char *data, size_t size, bool input)
{
    if (size != 0 && memchr(data, 0, size) != NULL) {
        return IR_NUL;
    }
    size_t pos = 0;
    bool forbidden = false;
    while (pos < size) {
        uint32_t cp = 0;
        const enum ir_status st = scalar(data, size, &pos, &cp);
        if (st != IR_OK) {
            return st;
        }
        forbidden = forbidden || noncharacter(cp);
    }
    return input && forbidden ? IR_NONCHARACTER : IR_OK;
}

enum ir_status ir_check_input(const unsigned char *data, size_t size)
{
    if (size == 0 || size > DICTUM_INPUT_MAX) {
        return IR_INPUT_SIZE;
    }
    return data == NULL ? IR_ARGUMENT : utf8(data, size, true);
}

bool ir_check_span(const unsigned char *data, size_t size, size_t start, size_t end)
{
    return ir_check_input(data, size) == IR_OK && start < end && end <= size
        && !continuation(data[start]) && (end == size || !continuation(data[end]));
}

static int peek(const struct parser *p)
{
    return p->pos == p->size ? -1 : p->data[p->pos];
}

static bool take(struct parser *p, int c)
{
    if (peek(p) != c) {
        return false;
    }
    ++p->pos;
    return true;
}

static void space(struct parser *p)
{
    while (peek(p) == ' ' || peek(p) == '\t' || peek(p) == '\r' || peek(p) == '\n') {
        ++p->pos;
    }
}

static bool word(struct parser *p, const char *s)
{
    const size_t len = strlen(s);
    if (len > p->size - p->pos || memcmp(p->data + p->pos, s, len) != 0) {
        return false;
    }
    p->pos += len;
    return true;
}

static enum ir_status depth_preflight(const unsigned char *data, size_t size)
{
    size_t depth = 0;
    bool quoted = false, escaped = false;
    for (size_t i = 0; i < size; ++i) {
        const unsigned char c = data[i];
        if (quoted) {
            if (escaped) {
                escaped = false;
            } else if (c == '\\') {
                escaped = true;
            } else if (c == '"') {
                quoted = false;
            }
        } else if (c == '"') {
            quoted = true;
        } else if (c == '{' || c == '[') {
            if (++depth > DICTUM_DEPTH_MAX) {
                return IR_DEPTH;
            }
        } else if (c == '}' || c == ']') {
            if (depth == 0) {
                return IR_SYNTAX;
            }
            --depth;
        }
    }
    return IR_OK;
}

static bool hex4(struct parser *p, uint32_t *out)
{
    uint32_t cp = 0;
    for (unsigned int i = 0; i < 4; ++i) {
        const int c = peek(p);
        unsigned int digit;
        if (c >= '0' && c <= '9') {
            digit = (unsigned int)(c - '0');
        } else if (c >= 'a' && c <= 'f') {
            digit = (unsigned int)(c - 'a' + 10);
        } else if (c >= 'A' && c <= 'F') {
            digit = (unsigned int)(c - 'A' + 10);
        } else {
            return false;
        }
        ++p->pos;
        cp = (cp << 4) | digit;
    }
    *out = cp;
    return true;
}

static enum ir_status escape(struct parser *p, uint32_t *cp)
{
    const int c = peek(p);
    if (c < 0) {
        return IR_SYNTAX;
    }
    ++p->pos;
    switch (c) {
    case '"': case '\\': case '/': *cp = (uint32_t)c; break;
    case 'b': *cp = 8; break;
    case 'f': *cp = 12; break;
    case 'n': *cp = 10; break;
    case 'r': *cp = 13; break;
    case 't': *cp = 9; break;
    case 'u':
        if (!hex4(p, cp)) {
            return IR_SYNTAX;
        }
        if (*cp >= 0xd800u && *cp <= 0xdbffu) {
            uint32_t low = 0;
            if (!take(p, '\\') || !take(p, 'u')) {
                return IR_SURROGATE;
            }
            if (!hex4(p, &low)) {
                return IR_SYNTAX;
            }
            if (low < 0xdc00u || low > 0xdfffu) {
                return IR_SURROGATE;
            }
            *cp = 0x10000u + ((*cp - 0xd800u) << 10) + low - 0xdc00u;
        } else if (*cp >= 0xdc00u && *cp <= 0xdfffu) {
            return IR_SURROGATE;
        }
        break;
    default: return IR_SYNTAX;
    }
    return IR_OK;
}

static enum ir_status append_scalar(struct parser *p, struct ir_node *n, uint32_t cp)
{
    if (cp == 0) {
        return IR_NUL;
    }
    if (noncharacter(cp)) {
        return IR_NONCHARACTER;
    }
    const size_t len = cp < 0x80u ? 1u : cp < 0x800u ? 2u : cp < 0x10000u ? 3u : 4u;
    if (len > DICTUM_STRING_MAX - n->length) {
        return IR_STRING_SIZE;
    }
    /* Decoding never expands a token, and the arena holds at most size bytes. */
    if (len > p->size - p->doc->string_used) {
        return IR_RESOURCE;
    }
    unsigned char *dst = p->doc->strings + p->doc->string_used;
    if (len == 1) {
        dst[0] = (unsigned char)cp;
    } else {
        for (size_t i = len - 1; i > 0; --i) {
            dst[i] = (unsigned char)(0x80u | (cp & 0x3fu));
            cp >>= 6;
        }
        const unsigned int lead = len == 2 ? 0xc0u : len == 3 ? 0xe0u : 0xf0u;
        dst[0] = (unsigned char)(lead | cp);
    }
    p->doc->string_used += len;
    n->length += len;
    ++n->scalars;
    return IR_OK;
}

static enum ir_status string(struct parser *p, struct ir_node *n)
{
    n->kind = IR_STRING;
    n->offset = p->doc->string_used;
    if (!take(p, '"')) {
        return IR_SYNTAX;
    }
    while (!take(p, '"')) {
        uint32_t cp = 0;
        enum ir_status st;
        if (take(p, '\\')) {
            st = escape(p, &cp);
        } else {
            if (peek(p) < 0x20) {
                return IR_SYNTAX;
            }
            st = scalar(p->data, p->size, &p->pos, &cp);
        }
        if (st != IR_OK) {
            return st;
        }
        st = append_scalar(p, n, cp);
        if (st != IR_OK) {
            return st;
        }
    }
    n->end = p->pos;
    return IR_OK;
}

static bool digit(int c)
{
    return c >= '0' && c <= '9';
}

static enum ir_status number(struct parser *p, struct ir_node *n)
{
    const bool negative = take(p, '-');
    if (!digit(peek(p))) {
        return IR_SYNTAX;
    }
    int64_t value = 0;
    bool overflow = false;
    if (!take(p, '0')) {
        while (digit(peek(p))) {
            const int d = peek(p) - '0';
            ++p->pos;
            if (value > (DICTUM_INTEGER_MAX - d) / 10) {
                overflow = true;
            }
            if (!overflow) {
                value = value * 10 + d;
            }
        }
    }
    if (peek(p) == '.' || peek(p) == 'e' || peek(p) == 'E') {
        /* Match the oracle's distinction between invalid grammar and a
         * syntactically complete non-integer token. An incomplete suffix
         * remains trailing data or container syntax. */
        const size_t save = p->pos;
        bool fraction = false, exponent = false;
        if (take(p, '.')) {
            if (!digit(peek(p))) {
                p->pos = save;
            } else {
                fraction = true;
                while (digit(peek(p))) { ++p->pos; }
            }
        }
        if (peek(p) == 'e' || peek(p) == 'E') {
            ++p->pos;
            if (!take(p, '+')) { (void)take(p, '-'); }
            exponent = digit(peek(p));
        }
        if (fraction || exponent) {
            return IR_NUMBER_SYNTAX;
        }
        p->pos = save;
    }
    if (overflow) {
        return IR_INTEGER_RANGE;
    }
    if (negative && value == 0) {
        return IR_NUMBER_SYNTAX;
    }
    n->kind = IR_INTEGER;
    n->integer = negative ? -value : value;
    n->end = p->pos;
    return IR_OK;
}

static size_t new_node(struct parser *p)
{
    /* Each node consumes at least one unique input byte. */
    if (p->doc->used >= p->size) {
        return 0;
    }
    const size_t id = ++p->doc->used;
    p->doc->nodes[id].start = p->pos;
    return id;
}

static enum ir_status value(struct parser *p, size_t depth, size_t *id);

static bool same_key(const struct ir_document *doc, size_t a, size_t b)
{
    const struct ir_node *x = &doc->nodes[a], *y = &doc->nodes[b];
    return x->length == y->length &&
        memcmp(doc->strings + x->offset, doc->strings + y->offset, x->length) == 0;
}

static enum ir_status container(struct parser *p, struct ir_node *n, size_t depth, bool object)
{
    if (depth >= DICTUM_DEPTH_MAX) {
        return IR_DEPTH;
    }
    n->kind = object ? IR_OBJECT : IR_ARRAY;
    const int close = object ? '}' : ']';
    const size_t limit = object ? DICTUM_OBJECT_MAX : DICTUM_ARRAY_MAX;
    ++p->pos;
    space(p);
    size_t *link = &n->first;
    if (!take(p, close)) {
        for (;;) {
            if (n->count == limit) {
                return object ? IR_OBJECT_SIZE : IR_ARRAY_SIZE;
            }
            size_t member = 0;
            enum ir_status st;
            if (object) {
                if (peek(p) != '"') {
                    return IR_SYNTAX;
                }
                member = new_node(p);
                if (member == 0) {
                    return IR_RESOURCE;
                }
                struct ir_node *key = &p->doc->nodes[member];
                st = string(p, key);
                if (st != IR_OK) {
                    return st;
                }
                for (size_t prev = n->first; prev != 0; prev = p->doc->nodes[prev].next) {
                    if (same_key(p->doc, prev, member)) {
                        return IR_DUPLICATE;
                    }
                }
                space(p);
                if (!take(p, ':')) {
                    return IR_SYNTAX;
                }
                space(p);
                st = value(p, depth + 1, &key->first);
            } else {
                st = value(p, depth + 1, &member);
            }
            if (st != IR_OK) {
                return st;
            }
            *link = member;
            link = &p->doc->nodes[member].next;
            ++n->count;
            space(p);
            if (take(p, close)) {
                break;
            }
            if (!take(p, ',')) {
                return IR_SYNTAX;
            }
            space(p);
        }
    }
    n->end = p->pos;
    return IR_OK;
}

static enum ir_status value(struct parser *p, size_t depth, size_t *id)
{
    if (peek(p) < 0) {
        return IR_SYNTAX;
    }
    *id = new_node(p);
    if (*id == 0) {
        return IR_RESOURCE;
    }
    struct ir_node *n = &p->doc->nodes[*id];
    switch (peek(p)) {
    case '{': return container(p, n, depth, true);
    case '[': return container(p, n, depth, false);
    case '"': return string(p, n);
    default: break;
    }
    if (word(p, "true")) {
        n->kind = IR_TRUE;
    } else if (word(p, "false")) {
        n->kind = IR_FALSE;
    } else if (word(p, "null")) {
        n->kind = IR_NULL;
    } else if (word(p, "NaN") || word(p, "Infinity") || word(p, "-Infinity")) {
        return IR_NONFINITE;
    } else if (peek(p) == '-' || digit(peek(p))) {
        return number(p, n);
    } else {
        return IR_SYNTAX;
    }
    n->end = p->pos;
    return IR_OK;
}

void ir_destroy(struct ir_document *doc)
{
    if (doc != NULL) {
        free(doc->nodes);
        free(doc->strings);
        *doc = (struct ir_document){0};
    }
}

enum ir_status ir_parse(struct ir_document *doc, const unsigned char *data, size_t size)
{
    if (doc == NULL) {
        return IR_ARGUMENT;
    }
    ir_destroy(doc);
    if (size > DICTUM_FRAME_MAX) {
        return IR_FRAME_SIZE;
    }
    if (size == 0) {
        return IR_SYNTAX;
    }
    if (data == NULL) {
        return IR_ARGUMENT;
    }
    if (size >= 3 && data[0] == 0xefu && data[1] == 0xbbu && data[2] == 0xbfu) {
        return IR_BOM;
    }
    enum ir_status st = utf8(data, size, false);
    if (st == IR_OK) {
        st = depth_preflight(data, size);
    }
    if (st != IR_OK) {
        return st;
    }
    doc->nodes = calloc(size + 1, sizeof(*doc->nodes));
    doc->strings = malloc(size);
    if (doc->nodes == NULL || doc->strings == NULL) {
        ir_destroy(doc);
        return IR_RESOURCE;
    }
    struct parser p = {doc, data, size, 0};
    size_t root = 0;
    space(&p);
    st = value(&p, 0, &root);
    if (st == IR_OK) {
        space(&p);
        if (p.pos != size) {
            st = IR_TRAILING;
        }
    }
    if (st != IR_OK) {
        ir_destroy(doc);
    }
    return st;
}

const char *ir_status_name(enum ir_status status)
{
    switch (status) {
    case IR_OK: return "ok";
    case IR_INPUT_SIZE: return "byte/input-size";
    case IR_FRAME_SIZE: return "byte/frame-size";
    case IR_BOM: return "byte/bom";
    case IR_NUL: return "byte/nul";
    case IR_UTF8: return "byte/utf8";
    case IR_DEPTH: return "byte/depth";
    case IR_SYNTAX: return "byte/json-syntax";
    case IR_TRAILING: return "byte/trailing-data";
    case IR_DUPLICATE: return "byte/duplicate-key";
    case IR_SURROGATE: return "byte/surrogate";
    case IR_NONCHARACTER: return "byte/noncharacter";
    case IR_STRING_SIZE: return "byte/string-size";
    case IR_ARRAY_SIZE: return "byte/array-size";
    case IR_OBJECT_SIZE: return "byte/object-size";
    case IR_NUMBER_SYNTAX: return "byte/number-syntax";
    case IR_INTEGER_RANGE: return "byte/integer-range";
    case IR_NONFINITE: return "byte/nonfinite";
    case IR_SCHEMA: return "schema/structure";
    case IR_RESOURCE: return "internal/resource";
    case IR_ARGUMENT: return "internal/argument";
    }
    return "internal/argument";
}
