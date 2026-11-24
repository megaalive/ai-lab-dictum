#include "f1_candidate.h"
#include <string.h>

struct pair { const char *kind,*value; };
#include "f1_candidate_generated.inc"

static bool eq(const struct ir_document *d,size_t i,const char *s)
{
    if (i==0) return false;
    const struct ir_node *n=&d->nodes[i];
    return n->kind==IR_STRING && n->length==strlen(s) &&
        memcmp(d->strings+n->offset,s,n->length)==0;
}

enum ir_status f1_candidate_validate(const struct ir_document *doc)
{
    if (doc==NULL || doc->nodes==NULL || doc->used==0) return IR_ARGUMENT;
    if (doc->nodes[1].kind!=IR_OBJECT || doc->nodes[1].count!=2) return IR_SCHEMA;
    size_t kind=0,value=0;
    for (size_t k=doc->nodes[1].first;k!=0;k=doc->nodes[k].next) {
        if (eq(doc,k,"kind")) kind=doc->nodes[k].first;
        else if (eq(doc,k,"value")) value=doc->nodes[k].first;
        else return IR_SCHEMA;
    }
    if (kind==0 || value==0) return IR_SCHEMA;
    for (size_t i=0;i<sizeof(pairs)/sizeof(pairs[0]);++i)
        if (eq(doc,kind,pairs[i].kind) && eq(doc,value,pairs[i].value)) return IR_OK;
    return IR_SCHEMA;
}
