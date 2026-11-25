#include "renderer.h"
#include <string.h>
#include "renderer_unicode.inc"

static bool eq(const struct ir_document *d,size_t i,const char *s)
{
    if (i==0) return false;
    const struct ir_node *n=&d->nodes[i];
    return n->kind==IR_STRING && n->length==strlen(s) &&
        memcmp(d->strings+n->offset,s,n->length)==0;
}
static size_t get(const struct ir_document *d,size_t i,const char *s)
{
    if (i==0 || d->nodes[i].kind!=IR_OBJECT) return 0;
    for (size_t k=d->nodes[i].first;k!=0;k=d->nodes[k].next)
        if (eq(d,k,s)) return d->nodes[k].first;
    return 0;
}
bool renderer_structured_plan(const struct ir_document *plan)
{
    if ((ir_validate(plan,IR_PLAN)!=IR_OK && ir_validate(plan,IR_PLAN_V2)!=IR_OK) ||
        !ir_plan_digest_matches(plan)) return false;
    const size_t action=get(plan,1,"action");
    return eq(plan,get(plan,action,"kind"),"structured-proposal") &&
        eq(plan,get(plan,get(plan,action,"operation"),"kind"),"native");
}
static bool forbidden(uint32_t cp)
{
    size_t lo=0,hi=sizeof(forbidden_ranges)/sizeof(forbidden_ranges[0]);
    while (lo<hi) {
        const size_t mid=lo+(hi-lo)/2;
        if (cp<forbidden_ranges[mid][0]) hi=mid;
        else if (cp>forbidden_ranges[mid][1]) lo=mid+1;
        else return true;
    }
    return false;
}
enum renderer_status renderer_check_token(struct renderer_token token)
{
    if (token.size>RENDER_TOKEN_MAX) return RENDER_TOKEN;
    if (token.size==0) return RENDER_OK;
    if (token.data==NULL) return RENDER_UTF8;
    const enum ir_status st=ir_check_input(token.data,token.size);
    if (st==IR_NUL) return RENDER_UNSAFE;
    if (st==IR_NONCHARACTER) return RENDER_NONCHAR;
    if (st!=IR_OK) return RENDER_UTF8;
    /* ir_check_input already verified every scalar and length; this pass
     * only maps those bytes to scalar values for the pinned category test. */
    for (size_t i=0;i<token.size;) {
        const unsigned char c=token.data[i++];
        uint32_t cp=c;
        size_t tail=0;
        if (c>=0xf0u) { cp=c&7u; tail=3; }
        else if (c>=0xe0u) { cp=c&15u; tail=2; }
        else if (c>=0xc0u) { cp=c&31u; tail=1; }
        if (tail>token.size-i) return RENDER_UTF8;
        for (size_t j=0;j<tail;++j) cp=(cp<<6)|(token.data[i++]&63u);
        if (forbidden(cp)) return RENDER_UNSAFE;
    }
    return RENDER_OK;
}
enum renderer_status renderer_quote_tokens(enum renderer_shell shell,
    const struct renderer_token *tokens,size_t count,char out[RENDER_MAX+1u])
{
    if (out==NULL) return RENDER_SIZE;
    out[0]='\0';
    if (shell!=RENDER_BASH_CLEAN && shell!=RENDER_DASH_CLEAN) return RENDER_SHELL;
    if (tokens==NULL || count==0 || count>RENDER_ARG_MAX) return RENDER_COUNT;
    /* Preflight all tokens and exact output length before emitting any bytes. */
    size_t total=0;
    for (size_t i=0;i<count;++i) {
        const enum renderer_status st=renderer_check_token(tokens[i]);
        if (st!=RENDER_OK) return st;
        size_t len=2u+(i!=0?1u:0u);
        for (size_t j=0;j<tokens[i].size;++j) len+=tokens[i].data[j]=='\''?4u:1u;
        if (len>RENDER_MAX-total) return RENDER_SIZE;
        total+=len;
    }
    size_t pos=0;
    for (size_t i=0;i<count;++i) {
        if (i!=0) out[pos++]=' ';
        out[pos++]='\'';
        for (size_t j=0;j<tokens[i].size;++j) {
            const unsigned char c=tokens[i].data[j];
            if (c=='\'') { memcpy(out+pos,"'\\''",4); pos+=4; }
            else out[pos++]=(char)c;
        }
        out[pos++]='\'';
    }
    out[pos]='\0';
    return pos==total ? RENDER_OK : RENDER_SIZE;
}
const char *renderer_status_name(enum renderer_status st)
{
    switch (st) {
    case RENDER_OK: return "ok";
    case RENDER_SHELL: return "unsupported-shell";
    case RENDER_TOKEN: return "token-size";
    case RENDER_UTF8: return "utf8";
    case RENDER_NONCHAR: return "noncharacter";
    case RENDER_UNSAFE: return "unsafe-character";
    case RENDER_COUNT: return "argv-count";
    case RENDER_SIZE: return "preview-size";
    }
    return "invalid";
}
