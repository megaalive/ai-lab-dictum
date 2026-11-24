/* Direct in-process fuzz of byte parser, schema validator and lifetime. */
#include "ir_schema.h"
#include <stdlib.h>
#include <string.h>

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

static void need(bool condition)
{
    if (!condition) abort();
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    struct ir_document d = {0};
    const enum ir_status first = ir_parse(&d, data, size);
    enum ir_status results[4] = {IR_ARGUMENT, IR_ARGUMENT, IR_ARGUMENT, IR_ARGUMENT};
    if (first == IR_OK) {
        need(d.used > 0 && d.used <= size && d.string_used <= size);
        for (size_t j = 1; j <= d.used; ++j) {
            const struct ir_node *n = &d.nodes[j];
            need(n->start < n->end && n->end <= size);
            need(n->first <= d.used && n->next <= d.used);
            if (n->kind == IR_STRING)
                need(n->offset <= d.string_used && n->length <= d.string_used - n->offset);
        }
        for (size_t j = 0; j < 4; ++j) results[j] = ir_validate(&d, (enum ir_stage)j);
    } else {
        need(d.nodes == NULL && d.strings == NULL && d.used == 0 && d.string_used == 0);
    }
    need(ir_parse(&d, data, size) == first);
    if (first == IR_OK)
        for (size_t j = 0; j < 4; ++j) need(ir_validate(&d, (enum ir_stage)j) == results[j]);
    (void)ir_check_input(data, size);
    ir_destroy(&d);
    ir_destroy(&d);
    return 0;
}
