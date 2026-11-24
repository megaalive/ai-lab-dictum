#ifndef DICTUM_IR_WIRE_H
#define DICTUM_IR_WIRE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DICTUM_INPUT_MAX 4096u
#define DICTUM_FRAME_MAX 32768u
#define DICTUM_STRING_MAX 4096u
#define DICTUM_DEPTH_MAX 12u
#define DICTUM_ARRAY_MAX 64u
#define DICTUM_OBJECT_MAX 32u
#define DICTUM_INTEGER_MAX INT64_C(9007199254740991)

enum ir_status {
    IR_OK, IR_INPUT_SIZE, IR_FRAME_SIZE, IR_BOM, IR_NUL, IR_UTF8,
    IR_DEPTH, IR_SYNTAX, IR_TRAILING, IR_DUPLICATE, IR_SURROGATE,
    IR_NONCHARACTER, IR_STRING_SIZE, IR_ARRAY_SIZE, IR_OBJECT_SIZE,
    IR_NUMBER_SYNTAX, IR_INTEGER_RANGE, IR_NONFINITE, IR_SCHEMA,
    IR_RESOURCE, IR_ARGUMENT
};

enum ir_kind { IR_OBJECT, IR_ARRAY, IR_STRING, IR_INTEGER, IR_TRUE, IR_FALSE, IR_NULL };

struct ir_node {
    enum ir_kind kind;
    size_t start, end; /* raw byte span, exclusive end */
    size_t first, next, count; /* object children are key nodes; key.first is value */
    size_t offset, length, scalars; /* decoded string in document arena */
    int64_t integer;
};

/* An owned document. Index 0 is reserved, root is 1. Zero-init before
 * first parse; destroy once finished. Parse replaces any previous document
 * and leaves an empty document on error. No pointer into input is retained. Input must not alias the
 * document's owned storage.
 * Do not mutate nodes or pass fabricated documents to the validator. */
struct ir_document {
    struct ir_node *nodes;
    unsigned char *strings;
    size_t used, string_used;
};

enum ir_status ir_check_input(const unsigned char *data, size_t size);
/* Checks input validity, range and UTF-8 scalar boundaries only; does not
 * establish provenance or compare the slice against a trusted request. */
bool ir_check_span(const unsigned char *data, size_t size, size_t start, size_t end);
enum ir_status ir_parse(struct ir_document *doc, const unsigned char *data, size_t size);
void ir_destroy(struct ir_document *doc);
const char *ir_status_name(enum ir_status status);

#endif
