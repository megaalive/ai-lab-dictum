#include "ir_schema.h"
#include <string.h>

static bool eq(const struct ir_document *d, size_t i, const char *s)
{
    const struct ir_node *n = &d->nodes[i];
    return n->kind == IR_STRING && n->length == strlen(s)
        && memcmp(d->strings + n->offset, s, n->length) == 0;
}

static bool bounds(size_t n, size_t lo, size_t hi)
{
    return n >= lo && n <= hi;
}

enum pattern_kind { P_INTENT, P_NAME, P_HEX32, P_HEX64, P_UNIT, P_PATH, P_FLAG };

static bool lower(unsigned char c) { return c >= 'a' && c <= 'z'; }
static bool digit(unsigned char c) { return c >= '0' && c <= '9'; }
static bool alnum(unsigned char c)
{
    return lower(c) || (c >= 'A' && c <= 'Z') || digit(c);
}

static bool pattern(const struct ir_document *d, size_t i, enum pattern_kind kind)
{
    const struct ir_node *n = &d->nodes[i];
    const unsigned char *s = d->strings + n->offset;
    const size_t len = n->length;
    if (len == 0) return false;
    switch (kind) {
    case P_PATH: return s[0] == '/';
    case P_HEX32: case P_HEX64:
        if (len != (kind == P_HEX32 ? 32u : 64u)) return false;
        for (size_t j = 0; j < len; ++j)
            if (!digit(s[j]) && !(s[j] >= 'a' && s[j] <= 'f')) return false;
        return true;
    case P_INTENT: case P_NAME: {
        bool beginning = true, dot = false;
        for (size_t j = 0; j < len; ++j) {
            if (beginning) {
                if (!lower(s[j])) return false;
                beginning = false;
            } else if (kind == P_INTENT && s[j] == '.') {
                dot = true;
                beginning = true;
            } else if (!lower(s[j]) && !digit(s[j]) && s[j] != '_') return false;
        }
        return !beginning && (kind == P_NAME || dot);
    }
    case P_UNIT:
        if (!alnum(s[0]) && s[0] != '_') return false;
        for (size_t j = 1; j < len; ++j)
            if (!alnum(s[j]) && s[j] != '_' && s[j] != '.' && s[j] != ':'
                && s[j] != '@' && s[j] != '-') return false;
        return true;
    case P_FLAG: {
        if (s[0] != '-' || len < 2) return false;
        size_t j = s[1] == '-' ? 2u : 1u;
        if (j == len || !alnum(s[j])) return false;
        for (++j; j < len; ++j)
            if (!alnum(s[j]) && s[j] != '-') return false;
        return true;
    }
    }
    return false;
}

#include "ir_generated.inc"

enum ir_status ir_validate(const struct ir_document *doc, enum ir_stage stage)
{
    if (doc == NULL || doc->nodes == NULL || doc->used == 0 ||
        stage < IR_NLU || stage > IR_PLAN_V2) return IR_ARGUMENT;
    return root_valid(doc, stage) ? IR_OK : IR_SCHEMA;
}
