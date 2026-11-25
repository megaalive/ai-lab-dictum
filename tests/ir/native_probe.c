/* Test-only byte transport. No product command or target invocation. */
#include "ir_digest.h"
#include <stdio.h>
#include <string.h>
#include <inttypes.h>

static void hex(const unsigned char *s, size_t n)
{
    for (size_t i = 0; i < n; ++i) printf("%02x", (unsigned int)s[i]);
}

/* Prefix traversal, including raw byte spans and decoded values. */
static void dump(const struct ir_document *d, size_t i)
{
    const struct ir_node *n = &d->nodes[i];
    printf("%d %zu %zu", (int)n->kind, n->start, n->end);
    if (n->kind == IR_STRING) {
        printf(" %zu ", n->scalars);
        hex(d->strings + n->offset, n->length);
    } else if (n->kind == IR_INTEGER) {
        printf(" %" PRId64, n->integer);
    } else if (n->kind == IR_OBJECT || n->kind == IR_ARRAY) {
        printf(" %zu", n->count);
    }
    putchar('\n');
    if (n->kind == IR_OBJECT || n->kind == IR_ARRAY) {
        for (size_t k = n->first; k != 0; k = d->nodes[k].next) {
            dump(d, k);
            if (n->kind == IR_OBJECT) dump(d, d->nodes[k].first);
        }
    }
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    unsigned char data[DICTUM_FRAME_MAX + 1u];
    const size_t size = fread(data, 1, sizeof(data), stdin);
    if (ferror(stdin)) return 2;
    if (strcmp(argv[1], "hash") == 0) {
        char digest[65];
        if (!ir_sha256_hex(data,size,digest)) return 2;
        puts(digest);
        return ferror(stdout) || fflush(stdout) == EOF ? 2 : 0;
    }
    struct ir_document d = {0};
    if (strcmp(argv[1], "digest") == 0) {
        char digest[65];
        const bool valid=ir_parse(&d,data,size)==IR_OK && ir_plan_digest(&d,digest);
        if (valid) printf("%s %s\n",digest,ir_plan_digest_matches(&d) ? "match" : "mismatch");
        ir_destroy(&d);
        if (!valid) puts("invalid");
        return ferror(stdout) || fflush(stdout) == EOF ? 2 : 0;
    }
    enum ir_status st;
    if (strcmp(argv[1], "input") == 0) {
        st = ir_check_input(data, size);
    } else {
        st = ir_parse(&d, data, size);
        const char *names[] = {"nlu", "ir", "policy", "plan", "nlu-v2", "ir-v2", "policy-v2", "plan-v2"};
        if (strcmp(argv[1], "raw") != 0) {
            size_t i = 0;
            while (i < 8 && strcmp(argv[1], names[i]) != 0) ++i;
            if (i == 8) { ir_destroy(&d); return 2; }
            if (st == IR_OK) st = ir_validate(&d, (enum ir_stage)i);
        }
    }
    puts(ir_status_name(st));
    if (st == IR_OK && d.used != 0) dump(&d, 1);
    ir_destroy(&d);
    return ferror(stdout) || fflush(stdout) == EOF ? 2 : 0;
}
