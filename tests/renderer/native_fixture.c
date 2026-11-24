/* Inert fixture adapter only: this target is never linked into dictum. */
#include "renderer.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static const char dumper[]="/fixture/bin/argv-dumper";
static const char hash[]="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static bool kind(const struct ir_document *d,size_t i,enum ir_kind k)
{
    return i!=0 && d->nodes[i].kind==k;
}
static bool eq(const struct ir_document *d,size_t i,const char *s)
{
    if (!kind(d,i,IR_STRING)) return false;
    const struct ir_node *n=&d->nodes[i];
    return n->length==strlen(s) && memcmp(d->strings+n->offset,s,n->length)==0;
}
static size_t get(const struct ir_document *d,size_t i,const char *s)
{
    if (!kind(d,i,IR_OBJECT)) return 0;
    for (size_t k=d->nodes[i].first;k!=0;k=d->nodes[k].next)
        if (eq(d,k,s)) return d->nodes[k].first;
    return 0;
}
static bool shape(const struct ir_document *d,size_t i,size_t count)
{
    return kind(d,i,IR_OBJECT) && d->nodes[i].count==count;
}
static struct renderer_token token(const struct ir_document *d,size_t i)
{
    const struct ir_node *n=&d->nodes[i];
    return (struct renderer_token){d->strings+n->offset,n->length};
}
static struct renderer_token text(const char *s)
{
    return (struct renderer_token){(const unsigned char *)s,strlen(s)};
}
static bool token_eq(struct renderer_token t,const char *s)
{
    return t.size==strlen(s) && (t.size==0 || memcmp(t.data,s,t.size)==0);
}
static bool alnum(unsigned char c)
{
    return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9');
}
static bool flag(struct renderer_token t)
{
    if (t.size<2||t.size>64||t.data[0]!='-') return false;
    size_t i=t.data[1]=='-'?2u:1u;
    if (i==t.size||!alnum(t.data[i])) return false;
    for (++i;i<t.size;++i) if (!alnum(t.data[i])&&t.data[i]!='-') return false;
    return true;
}
enum atom_kind { A_END,A_LITERAL,A_FLAG,A_INTEGER };
struct atom {
    enum atom_kind kind;
    struct renderer_token token;
    int64_t integer;
    char number[32];
};
static const char *read_atom(const struct ir_document *d,size_t i,struct atom *a)
{
    if (!kind(d,i,IR_OBJECT)) return "atom-type";
    const size_t k=get(d,i,"kind"),v=get(d,i,"value");
    if (eq(d,k,"option-end")) {
        if (!shape(d,i,1)) return "atom-shape";
        a->kind=A_END; a->token=text("--"); return NULL;
    }
    if (!shape(d,i,2)||v==0||k==0) return "atom-shape";
    if (eq(d,k,"integer")) {
        if (!kind(d,v,IR_INTEGER)) return "integer";
        a->kind=A_INTEGER; a->integer=d->nodes[v].integer;
        const int n=snprintf(a->number,sizeof(a->number),"%" PRId64,a->integer);
        if (n<=0||(size_t)n>=sizeof(a->number)) return "integer";
        a->token=text(a->number); return NULL;
    }
    if (eq(d,k,"flag")) {
        if (!kind(d,v,IR_STRING)) return "flag-syntax";
        a->kind=A_FLAG; a->token=token(d,v);
        if (!flag(a->token)) return "flag-syntax";
    } else {
        if (!eq(d,k,"literal")||!kind(d,v,IR_STRING)) return "atom-type";
        a->kind=A_LITERAL; a->token=token(d,v);
    }
    const enum renderer_status st=renderer_check_token(a->token);
    return st==RENDER_OK?NULL:renderer_status_name(st);
}
static const char *render_fixture(const struct ir_document *d,char out[RENDER_MAX+1u])
{
    const size_t shell=get(d,1,"shell"),gate=get(d,1,"gate"),recipe=get(d,1,"recipe"),
        action=get(d,1,"action");
    if (!shape(d,1,6)||get(d,1,"id")==0||get(d,1,"expected")==0||shell==0||gate==0||recipe==0||action==0)
        return "case-shape";
    enum renderer_shell profile=RENDER_UNKNOWN;
    if (eq(d,shell,"bash-posix-clean-v1")) profile=RENDER_BASH_CLEAN;
    else if (eq(d,shell,"dash-clean-v1")) profile=RENDER_DASH_CLEAN;
    else return "unsupported-shell";
    if (!eq(d,gate,"verified-fixture")) return "unverified-binding";
    const size_t ak=get(d,action,"kind");
    if (!kind(d,action,IR_OBJECT)||!kind(d,ak,IR_STRING)) return "action-shape";
    if (!eq(d,ak,"proposal-only")) return "non-executable-action";
    const size_t op=get(d,action,"operation");
    if (!shape(d,action,2)||op==0) return "action-shape";
    const size_t identity=get(d,op,"identity"),args=get(d,op,"argv");
    if (!shape(d,op,3)||!eq(d,get(d,op,"kind"),"executable")||identity==0||args==0)
        return "operation-shape";
    if (!shape(d,identity,3)||!eq(d,get(d,identity,"path"),dumper)||
        !eq(d,get(d,identity,"version"),"fixture-v1")||!eq(d,get(d,identity,"sha256"),hash))
        return "identity";
    if (!kind(d,args,IR_ARRAY)||d->nodes[args].count>32) return "argv-count";
    struct atom atoms[32]={0};
    struct renderer_token tokens[33]={text(dumper)};
    size_t n=0;
    for (size_t k=d->nodes[args].first;k!=0;k=d->nodes[k].next) {
        const char *reason=read_atom(d,k,&atoms[n]);
        if (reason!=NULL) return reason;
        tokens[n+1]=atoms[n].token; ++n;
    }
    if (eq(d,recipe,"fixture-end")) {
        if (n<2||atoms[0].kind!=A_END) return "operand-binding";
        for (size_t i=1;i<n;++i) if (atoms[i].kind!=A_LITERAL) return "operand-binding";
        for (size_t i=1;i<n;++i) if (token_eq(atoms[i].token,"-")) return "stdin-operand";
    } else if (eq(d,recipe,"fixture-no-end")) {
        if (n!=1||atoms[0].kind!=A_LITERAL||atoms[0].token.size==0||atoms[0].token.data[0]=='-')
            return "operand-binding";
    } else if (eq(d,recipe,"fixture-limit")) {
        if (n!=4||atoms[0].kind!=A_FLAG||!token_eq(atoms[0].token,"--limit")||
            atoms[1].kind!=A_INTEGER||atoms[2].kind!=A_END||atoms[3].kind!=A_LITERAL)
            return "operand-binding";
        if (atoms[1].integer<1||atoms[1].integer>4) return "limit";
        if (atoms[3].token.size==0||token_eq(atoms[3].token,"-")) return "stdin-operand";
    } else return "unknown-recipe";
    const enum renderer_status st=renderer_quote_tokens(profile,tokens,n+1,out);
    return st==RENDER_OK?NULL:renderer_status_name(st);
}
int main(void)
{
    unsigned char input[DICTUM_FRAME_MAX+1u];
    const size_t n=fread(input,1,sizeof(input),stdin);
    if (ferror(stdin)) return 2;
    char preview[RENDER_MAX+1u]={0};
    struct ir_document d={0};
    const enum ir_status st=ir_parse(&d,input,n);
    const char *reason;
    if (st==IR_OK) reason=render_fixture(&d,preview);
    else if (st==IR_NUL) reason="unsafe-character";
    else if (st==IR_SURROGATE||st==IR_UTF8) reason="utf8";
    else if (st==IR_NONCHARACTER) reason="noncharacter";
    else if (st==IR_STRING_SIZE) reason="token-size";
    else reason="wire-reject";
    /* Never emit a rejected token, preview fragment or diagnostic input. */
    if (reason==NULL) printf("COPYABLE\n%s",preview);
    else printf("NON_COPYABLE\n%s",reason);
    ir_destroy(&d);
    return ferror(stdout)||fflush(stdout)==EOF?2:0;
}
