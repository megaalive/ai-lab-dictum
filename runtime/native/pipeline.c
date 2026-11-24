#include "pipeline.h"
#include "ir_digest.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
#define TOKENS 64u
#define SLOTS 16u
#define NO_INTENT SIZE_MAX
enum slot_name { S_PORT, S_PROTOCOL, S_UNIT, S_WINDOW, S_LIMIT, S_ROOT, S_DEPTH, S_EXTENSION, S_FILENAME };
enum slot_kind { K_INTEGER, K_PROTOCOL, K_LITERAL, K_TIME };
static const char *const slot_names[]={"port","protocol","unit","window","limit","root","depth","extension","filename"};

struct slot_rule {
    enum slot_name name;
    enum slot_kind kind;
    const char *type;
    bool required, has_default;
    int64_t min, max, number;
    const char *literal;
};
struct intent_rule {
    const char *id,*handler,*effect_class,*effect_json,*description_id,*description_en;
    struct slot_rule slots[SLOTS];
    size_t count;
};
struct grammar { size_t intent; const char *pattern; };
struct reference { size_t intent; const char *text; };
#include "pipeline_generated.inc"

struct token { size_t start,end; bool quoted; };
struct tokens { struct token item[TOKENS]; size_t count; };
struct candidate { enum slot_name name; struct token token; };
struct nlu_proposal {
    size_t intents[2], count;
    struct candidate candidates[SLOTS];
    size_t used;
};
struct request {
    const unsigned char *data;
    size_t size;
    int64_t reference;
    struct tokens tokens;
    bool invalid, time_valid;
    struct token time_token;
    int64_t time_start;
    char context_id[65], request_id[33], resolution_id[33], decision_id[33],
        action_id[33], scope_id[33], time_id[33];
};
enum resolution_state { RES_RESOLVED, RES_INCOMPLETE, RES_AMBIGUOUS, RES_UNSUPPORTED, RES_INVALID };
enum problem { PROBLEM_MISSING, PROBLEM_AMBIGUOUS };
struct value {
    const struct slot_rule *rule;
    int64_t number, end;
    char literal[1025];
    bool by_default, context_ref;
    struct token token;
};
struct pending { enum slot_name name; enum problem problem; };
struct resolved_ir {
    enum resolution_state state;
    size_t intent, alternatives[2], alternative_count;
    struct value slots[SLOTS];
    size_t count;
    struct pending pending[SLOTS];
    size_t pending_count;
};
struct policy_decision { enum pipeline_outcome outcome; const char *reason; };

struct writer { char *data; size_t size,used; bool ok; };
static struct writer writer(char *data,size_t size)
{
    data[0]='\0';
    return (struct writer){data,size,0,true};
}
static void bytes(struct writer *w,const char *s,size_t n)
{
    if (!w->ok || n>=w->size-w->used) { w->ok=false; return; }
    memcpy(w->data+w->used,s,n); w->used+=n; w->data[w->used]='\0';
}
static void add(struct writer *w,const char *s) { bytes(w,s,strlen(s)); }
static void number(struct writer *w,int64_t n)
{
    char b[32];
    const int len=snprintf(b,sizeof(b),"%" PRId64,n);
    if (len<=0 || (size_t)len>=sizeof(b)) { w->ok=false; return; }
    bytes(w,b,(size_t)len);
}
static void quote(struct writer *w,const char *s)
{
    add(w,"\"");
    while (*s!='\0') {
        const unsigned char c=(unsigned char)*s;
        if (c=='"' || c=='\\') add(w,"\\");
        if (c<0x20u) { w->ok=false; return; }
        bytes(w,s++,1);
    }
    add(w,"\"");
}
static void field(struct writer *w,const char *key,const char *v)
{
    quote(w,key); add(w,":"); quote(w,v);
}
static bool validate_frame(const struct writer *w,enum ir_stage stage)
{
    struct ir_document doc={0};
    const bool ok=w->ok && ir_parse(&doc,(const unsigned char *)w->data,w->used)==IR_OK
        && ir_validate(&doc,stage)==IR_OK;
    ir_destroy(&doc);
    return ok;
}
static unsigned char fold(unsigned char c)
{
    return c>='A' && c<='Z' ? (unsigned char)(c+('a'-'A')) : c;
}
static bool token_eq(const unsigned char *d,struct token t,const char *s,size_t len)
{
    if (t.quoted || t.end-t.start!=len) return false;
    for (size_t i=0;i<len;++i) if (fold(d[t.start+i])!=fold((unsigned char)s[i])) return false;
    return true;
}
static bool word(const struct request *q,size_t i,const char *s)
{
    return i<q->tokens.count && token_eq(q->data,q->tokens.item[i],s,strlen(s));
}
static bool tokenize(const unsigned char *d,size_t size,struct tokens *out)
{
    out->count=0;
    for (size_t p=0;p<size;) {
        while (p<size && d[p]==' ') ++p;
        if (p==size) break;
        if (out->count==TOKENS) return false;
        struct token t={p,0,false};
        if (d[p]=='"') {
            t.quoted=true; t.start=++p;
            while (p<size && d[p]!='"') ++p;
            if (p==size || p==t.start) return false;
            t.end=p++;
            if (p<size && d[p]!=' ') return false;
        } else {
            while (p<size && d[p]!=' ') {
                if (d[p]=='"') return false;
                ++p;
            }
            t.end=p;
            /* Optional question mark on a final grammar word/number only.
             * Never trim literal paths, names with punctuation, or quotes. */
            if (p==size && d[p-1]=='?') {
                bool plain=true;
                for (size_t j=t.start;j+1<p;++j) {
                    const unsigned char c=fold(d[j]);
                    if (!((c>='a'&&c<='z')||(c>='0'&&c<='9'))) plain=false;
                }
                if (plain) --t.end;
            }
        }
        if (t.start<t.end) out->item[out->count++]=t;
    }
    return out->count!=0;
}
static bool ascii_integer(const struct request *q,struct token t,int64_t lo,int64_t hi,int64_t *out)
{
    if (t.quoted || !ir_check_span(q->data,q->size,t.start,t.end) || t.end-t.start>16u) return false;
    int64_t v=0;
    for (size_t i=t.start;i<t.end;++i) {
        const unsigned char c=q->data[i];
        if (c<'0'||c>'9') return false;
        const int digit=c-'0';
        if (v>hi/10 || (v==hi/10 && digit>hi%10)) return false;
        v=v*10+digit;
    }
    if (v<lo || v>hi) return false;
    *out=v; return true;
}
static bool id_from(const struct request *q,const char *label,char out[33])
{
    char input[128],hash[65];
    const int n=snprintf(input,sizeof(input),"%s/%s",q->context_id,label);
    if (n<=0 || (size_t)n>=sizeof(input) || !ir_sha256_hex((const unsigned char *)input,(size_t)n,hash)) return false;
    memcpy(out,hash,32); out[32]='\0'; return true;
}
static bool unsafe(const struct request *q)
{
    /* Only a narrow authored grammar is accepted. These are additional
     * fail-closed exclusions, not a general secret-detection claim. */
    for (size_t i=0;i<q->size;++i) {
        const unsigned char c=q->data[i];
        if (c<0x20u || c==0x7fu || c==';' || c=='|' || c=='&' ||
            c=='$' || c=='\x60' || c=='<' || c=='>' || c=='\\' || c=='*') return true;
    }
    for (size_t i=0;i<q->tokens.count;++i)
        for (size_t j=0;j<COUNT(deny_tokens);++j)
            if (word(q,i,deny_tokens[j])) return true;
    return false;
}
static bool context(struct request *q,uint64_t sequence,char out[2048])
{
    if (sequence==0 || sequence>(uint64_t)DICTUM_INTEGER_MAX ||
        q->reference<1 || q->reference>INT64_C(253402300799)) return false;
    if (!tokenize(q->data,q->size,&q->tokens) || unsafe(q)) q->invalid=true;
    /* Time candidate is derived by context, before NLU, never by a model. */
    size_t time_hits=0;
    if (!q->invalid) for (size_t i=1;i<q->tokens.count;++i) {
        if (!word(q,i,"minutes") && !word(q,i,"menit")) continue;
        ++time_hits;
        int64_t mins=0;
        if (ascii_integer(q,q->tokens.item[i-1],1,1440,&mins) && q->reference>=mins*60) {
            q->time_token=q->tokens.item[i-1]; q->time_start=q->reference-mins*60; q->time_valid=true;
        }
    }
    q->time_valid=q->time_valid && time_hits==1;
    char input_hash[65];
    if (!ir_sha256_hex(q->data,q->size,input_hash)) return false;
    struct writer w=writer(out,2048);
    add(&w,"{"); field(&w,"mode","synthetic-request-v1"); add(&w,",");
    field(&w,"input_sha256",input_hash); add(&w,","); field(&w,"catalog_sha256",FIXTURE_CATALOG_SHA);
    add(&w,","); field(&w,"profile_sha256",FIXTURE_PROFILE_SHA); add(&w,",");
    field(&w,"policy_sha256",FIXTURE_POLICY_SHA); add(&w,",\"sequence\":"); number(&w,(int64_t)sequence);
    add(&w,",\"reference_unix_s\":"); number(&w,q->reference);
    add(&w,",\"time_candidate\":");
    if (q->time_valid) {
        add(&w,"{\"start\":"); number(&w,(int64_t)q->time_token.start);
        add(&w,",\"end\":"); number(&w,(int64_t)q->time_token.end);
        add(&w,",\"start_unix_s\":"); number(&w,q->time_start);
        add(&w,",\"end_unix_s\":"); number(&w,q->reference); add(&w,"}");
    } else add(&w,"null");
    add(&w,"}");
    return w.ok && ir_sha256_hex((const unsigned char *)out,w.used,q->context_id) &&
        id_from(q,"request",q->request_id) && id_from(q,"resolution",q->resolution_id) &&
        id_from(q,"decision",q->decision_id) && id_from(q,"action",q->action_id) &&
        id_from(q,"scope",q->scope_id) && id_from(q,"window",q->time_id);
}
static const struct slot_rule *find_slot(size_t intent,enum slot_name name)
{
    const struct intent_rule *r=&rules[intent];
    for (size_t i=0;i<r->count;++i) if (r->slots[i].name==name) return &r->slots[i];
    return NULL;
}
static bool placeholder(const char *s,size_t len,enum slot_name *name)
{
    if (len<3 || s[0]!='{' || s[len-1]!='}') return false;
    if (len==9 && memcmp(s,"{minutes}",9)==0) { *name=S_WINDOW; return true; }
    for (size_t i=0;i<COUNT(slot_names);++i)
        if (strlen(slot_names[i])==len-2 && memcmp(s+1,slot_names[i],len-2)==0) {
            *name=(enum slot_name)i; return true;
        }
    return false;
}
static bool candidate_add(struct nlu_proposal *n,enum slot_name name,struct token t)
{
    if (n->used==SLOTS) return false;
    n->candidates[n->used++]=(struct candidate){name,t};
    return true;
}
static bool match_grammar(const struct request *q,const struct grammar *g,
                          size_t first,size_t end,struct nlu_proposal *n)
{
    *n=(struct nlu_proposal){0};
    size_t i=first;
    const char *p=g->pattern;
    while (*p!='\0') {
        size_t len=0;
        while (p[len]!='\0' && p[len]!=' ') ++len;
        if (i==end) return false;
        enum slot_name name;
        const struct token t=q->tokens.item[i++];
        if (placeholder(p,len,&name)) {
            if (!candidate_add(n,name,t)) return false;
        } else if (!token_eq(q->data,t,p,len)) return false;
        p+=len;
        if (*p==' ') ++p;
    }
    while (i<end) {
        enum slot_name name;
        if (word(q,i,"limit")) name=S_LIMIT;
        else if (word(q,i,"depth")) name=S_DEPTH;
        else return false;
        if (end-i<2 || find_slot(g->intent,name)==NULL ||
            !candidate_add(n,name,q->tokens.item[i+1])) return false;
        i+=2;
    }
    n->intents[0]=g->intent; n->count=1; return true;
}
static bool match(const struct request *q,size_t first,size_t end,struct nlu_proposal *n)
{
    *n=(struct nlu_proposal){0};
    if (first<end && (word(q,first,"tolong")||word(q,first,"please"))) ++first;
    bool found=false;
    for (size_t i=0;i<COUNT(grammar);++i) {
        struct nlu_proposal candidate;
        if (!match_grammar(q,&grammar[i],first,end,&candidate)) continue;
        /* Prefer an exact longer grammar over an interpretation of its
         * trailing tokens as optional fields; conflicting interpretations
         * fail closed, rather than rely on table ordering. */
        if (found) {
            if (candidate.intents[0]!=n->intents[0] || candidate.used!=n->used) return false;
            for (size_t j=0;j<n->used;++j)
                if (candidate.candidates[j].name!=n->candidates[j].name ||
                    candidate.candidates[j].token.start!=n->candidates[j].token.start ||
                    candidate.candidates[j].token.end!=n->candidates[j].token.end) return false;
        } else { *n=candidate; found=true; }
    }
    return found;
}
static size_t retrieve(const struct request *q,const struct nlu_proposal *n)
{
    /* Deterministic word-overlap retrieval over the 32 pinned S2 refs.
     * Slots are masked before ranking. A tie or zero score abstains.
     * Retrieval cannot bypass complete grammar or introduce authority. */
    size_t scores[COUNT(rules)]={0};
    for (size_t r=0;r<COUNT(references);++r) {
        const char *p=references[r].text;
        size_t hits=0;
        while (*p!='\0') {
            size_t len=0;
            while (p[len]!='\0'&&p[len]!=' ') ++len;
            for (size_t i=0;i<q->tokens.count;++i) {
                const struct token t=q->tokens.item[i];
                bool masked=false;
                for (size_t j=0;j<n->used;++j)
                    if (n->candidates[j].token.start==t.start) masked=true;
                if (!masked && token_eq(q->data,t,p,len)) { ++hits; break; }
            }
            p+=len; if (*p==' ') ++p;
        }
        const size_t intent=references[r].intent;
        if (hits>scores[intent]) scores[intent]=hits;
    }
    size_t best=NO_INTENT,score=0; bool tie=false;
    for (size_t i=0;i<COUNT(rules);++i) {
        if (scores[i]>score) { best=i; score=scores[i]; tie=false; }
        else if (scores[i]==score && score!=0) tie=true;
    }
    return tie ? NO_INTENT : best;
}
static struct nlu_proposal propose(const struct request *q,enum pipeline_model model)
{
    struct nlu_proposal n={0};
    if (q->invalid) return n;
    if (match(q,0,q->tokens.count,&n)) {
        if (model==PIPE_B1 && retrieve(q,&n)!=n.intents[0]) return (struct nlu_proposal){0};
        return n;
    }
    /* Only recognize explicit alternatives when both sides are supported
     * complete grammar fragments; otherwise abstain (never guess). */
    for (size_t i=1;i+1<q->tokens.count;++i) {
        if (!word(q,i,"or")&&!word(q,i,"atau")) continue;
        struct nlu_proposal a,b;
        if (match(q,0,i,&a) && match(q,i+1,q->tokens.count,&b) && a.intents[0]!=b.intents[0]) {
            n=(struct nlu_proposal){0}; n.count=2;
            n.intents[0]=a.intents[0]; n.intents[1]=b.intents[0]; return n;
        }
    }
    return (struct nlu_proposal){0};
}
static bool time_candidate(const struct request *q,const struct candidate *c)
{
    return c->name==S_WINDOW && q->time_valid && c->token.start==q->time_token.start &&
        c->token.end==q->time_token.end && !c->token.quoted;
}
static void span(struct writer *w,struct token t)
{
    add(w,"{\"start\":"); number(w,(int64_t)t.start); add(w,",\"end\":"); number(w,(int64_t)t.end); add(w,"}");
}
static bool serialize_nlu(const struct request *q,const struct nlu_proposal *n,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    add(&w,"{\"schema_version\":1,\"intent_candidates\":[");
    for (size_t i=0;i<n->count;++i) {
        if (i!=0) add(&w,",");
        add(&w,"{"); field(&w,"intent",rules[n->intents[i]].id); add(&w,",\"slot_candidate_ids\":[");
        if (n->count==1) for (size_t j=0;j<n->used;++j) { if (j!=0) add(&w,","); number(&w,(int64_t)j); }
        add(&w,"]}");
    }
    add(&w,"],\"slot_candidates\":[");
    for (size_t i=0;i<n->used;++i) {
        const struct candidate *c=&n->candidates[i];
        if (i!=0) add(&w,",");
        add(&w,"{\"id\":"); number(&w,(int64_t)i); add(&w,","); field(&w,"slot",slot_names[c->name]);
        add(&w,",\"source\":{");
        if (time_candidate(q,c)) {
            field(&w,"kind","context-ref"); add(&w,","); field(&w,"candidate_id",q->time_id);
            add(&w,","); field(&w,"expected_kind","time-window");
        } else {
            field(&w,"kind","input-span"); add(&w,",\"span\":"); span(&w,c->token);
        }
        add(&w,"}}");
    }
    add(&w,"],"); field(&w,"abstain_hint",n->count==2 ? "ambiguous" : n->count==0 ? "out-of-domain" : "none"); add(&w,"}");
    return validate_frame(&w,IR_NLU);
}
static bool listed(const char *s,const char *const *list,size_t count)
{
    for (size_t i=0;i<count;++i) if (strcmp(s,list[i])==0) return true;
    return false;
}
static bool value_from(const struct request *q,const struct candidate *c,const struct slot_rule *r,struct value *v)
{
    const struct token t=c->token;
    if (!ir_check_span(q->data,q->size,t.start,t.end)) return false;
    *v=(struct value){.rule=r,.token=t};
    if (r->kind==K_INTEGER) return ascii_integer(q,t,r->min,r->max,&v->number);
    if (r->kind==K_TIME) {
        if (!time_candidate(q,c)) return false;
        v->context_ref=true; v->number=q->time_start; v->end=q->reference; return true;
    }
    const size_t len=t.end-t.start;
    if (len>=sizeof(v->literal)) return false;
    memcpy(v->literal,q->data+t.start,len); v->literal[len]='\0';
    switch (r->name) {
    case S_PROTOCOL: return !t.quoted && (strcmp(v->literal,"tcp")==0 || strcmp(v->literal,"udp")==0 || strcmp(v->literal,"all")==0);
    case S_UNIT: return !t.quoted && listed(v->literal,units,COUNT(units));
    case S_ROOT: return listed(v->literal,roots,COUNT(roots));
    case S_EXTENSION: return listed(v->literal,extensions,COUNT(extensions));
    case S_FILENAME: return listed(v->literal,filenames,COUNT(filenames));
    case S_PORT: case S_WINDOW: case S_LIMIT: case S_DEPTH: return false;
    }
    return false;
}
static bool has_slot(const struct resolved_ir *r,enum slot_name name)
{
    for (size_t i=0;i<r->count;++i) if (r->slots[i].rule->name==name) return true;
    return false;
}
static bool has_pending(const struct resolved_ir *r,enum slot_name name)
{
    for (size_t i=0;i<r->pending_count;++i) if (r->pending[i].name==name) return true;
    return false;
}
static struct resolved_ir resolve(const struct request *q,const struct nlu_proposal *n)
{
    struct resolved_ir r={.state=RES_UNSUPPORTED,.intent=NO_INTENT};
    const struct resolved_ir invalid={.state=RES_INVALID,.intent=NO_INTENT};
    if (q->invalid) return invalid;
    if (n->count==0) return r;
    if (n->count==2) {
        r.state=RES_AMBIGUOUS; r.alternative_count=2;
        r.alternatives[0]=n->intents[0]; r.alternatives[1]=n->intents[1]; return r;
    }
    if (n->count!=1 || n->intents[0]>=COUNT(rules)) return invalid;
    r.intent=n->intents[0]; r.state=RES_RESOLVED;
    const struct intent_rule *rule=&rules[r.intent];
    bool ambiguous=false;
    for (size_t i=0;i<n->used;++i)
        if (find_slot(r.intent,n->candidates[i].name)==NULL) return invalid;
    for (size_t i=0;i<rule->count;++i) {
        const struct slot_rule *s=&rule->slots[i];
        struct value v={.rule=s};
        size_t hits=0;
        for (size_t j=0;j<n->used;++j) {
            if (n->candidates[j].name!=s->name) continue;
            if (!value_from(q,&n->candidates[j],s,&v)) return invalid;
            ++hits;
        }
        if (hits>1) {
            r.pending[r.pending_count++]=(struct pending){s->name,PROBLEM_AMBIGUOUS};
            ambiguous=true;
        } else if (hits==1) r.slots[r.count++]=v;
        else if (s->has_default) {
            v.by_default=true; v.number=s->number;
            if (s->literal!=NULL) {
                const size_t len=strlen(s->literal);
                if (len>=sizeof(v.literal)) return invalid;
                memcpy(v.literal,s->literal,len+1);
            }
            r.slots[r.count++]=v;
        } else if (s->required) r.pending[r.pending_count++]=(struct pending){s->name,PROBLEM_MISSING};
    }
    /* F0-C is stricter than the wider listener contract: explicit port.
     * File search must have at least one literal or time filter. */
    if (strcmp(rule->id,"network.listener.lookup")==0 && !has_slot(&r,S_PORT) && !has_pending(&r,S_PORT)) {
        r.pending[r.pending_count++]=(struct pending){S_PORT,PROBLEM_AMBIGUOUS}; ambiguous=true;
    }
    if (strcmp(rule->id,"file.search")==0 && !has_slot(&r,S_EXTENSION)&&!has_slot(&r,S_FILENAME)&&!has_slot(&r,S_WINDOW)) {
        if (!has_pending(&r,S_FILENAME)) r.pending[r.pending_count++]=(struct pending){S_FILENAME,PROBLEM_AMBIGUOUS};
        ambiguous=true;
    }
    if (ambiguous) r.state=RES_AMBIGUOUS;
    else if (r.pending_count!=0) r.state=RES_INCOMPLETE;
    return r;
}
static void identity(struct writer *w,const char *hash)
{
    add(w,"{\"version\":1,"); field(w,"sha256",hash); add(w,"}");
}
static void common(struct writer *w,const struct request *q)
{
    add(w,"{\"schema_version\":1,"); field(w,"request_id",q->request_id); add(w,",");
    field(w,"resolution_id",q->resolution_id); add(w,","); field(w,"context_id",q->context_id);
    add(w,",\"catalog\":"); identity(w,FIXTURE_CATALOG_SHA);
}
static void typed_value(struct writer *w,const struct value *v)
{
    add(w,"{"); field(w,"kind",v->rule->type);
    if (v->rule->kind==K_TIME) {
        add(w,",\"start_unix_s\":"); number(w,v->number); add(w,",\"end_unix_s\":"); number(w,v->end);
    } else {
        add(w,",\"value\":");
        if (v->rule->kind==K_INTEGER) number(w,v->number); else quote(w,v->literal);
    }
    add(w,"}");
}
static const char *state_name(enum resolution_state s)
{
    switch (s) {
    case RES_RESOLVED: return "resolved";
    case RES_INCOMPLETE: return "incomplete";
    case RES_AMBIGUOUS: return "ambiguous";
    case RES_UNSUPPORTED: return "unsupported";
    case RES_INVALID: return "invalid";
    }
    return "invalid";
}
static void pending_json(struct writer *w,const struct resolved_ir *r)
{
    add(w,"[");
    for (size_t i=0;i<r->pending_count;++i) {
        if (i!=0) add(w,",");
        add(w,"{"); field(w,"slot",slot_names[r->pending[i].name]); add(w,",");
        field(w,"problem",r->pending[i].problem==PROBLEM_MISSING?"missing":"ambiguous"); add(w,"}");
    }
    add(w,"]");
}
static bool serialize_ir(const struct request *q,const struct resolved_ir *r,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    common(&w,q);
    if (r->intent!=NO_INTENT) { add(&w,","); field(&w,"intent",rules[r->intent].id); }
    add(&w,",\"slots\":[");
    for (size_t i=0;i<r->count;++i) {
        const struct value *v=&r->slots[i];
        if (i!=0) add(&w,",");
        add(&w,"{"); field(&w,"name",slot_names[v->rule->name]); add(&w,",\"value\":"); typed_value(&w,v);
        add(&w,",\"provenance\":{");
        if (v->by_default) field(&w,"kind","catalog-default");
        else if (v->context_ref) { field(&w,"kind","context-ref"); add(&w,","); field(&w,"candidate_id",q->time_id); }
        else { field(&w,"kind","input-span"); add(&w,",\"span\":"); span(&w,v->token); }
        add(&w,"}}");
    }
    add(&w,"],\"resolution\":{"); field(&w,"state",state_name(r->state)); add(&w,",\"unresolved\":"); pending_json(&w,r);
    add(&w,",\"alternatives\":[");
    for (size_t i=0;i<r->alternative_count;++i) { if (i!=0) add(&w,","); quote(&w,rules[r->alternatives[i]].id); }
    add(&w,"]}}");
    return validate_frame(&w,IR_RESOLVED);
}
static struct policy_decision policy(const struct resolved_ir *r)
{
    switch (r->state) {
    case RES_RESOLVED: return (struct policy_decision){PIPE_PROPOSAL,"proposal-eligible"};
    case RES_INCOMPLETE: return (struct policy_decision){PIPE_CLARIFY,"missing-slot"};
    case RES_AMBIGUOUS: return (struct policy_decision){PIPE_CLARIFY,"ambiguous"};
    case RES_UNSUPPORTED: return (struct policy_decision){PIPE_UNSUPPORTED,"unsupported-intent"};
    case RES_INVALID: return (struct policy_decision){PIPE_DENY,"invalid-candidate"};
    }
    return (struct policy_decision){PIPE_DENY,"policy-restriction"};
}
static const char *decision_name(enum pipeline_outcome p)
{
    switch (p) {
    case PIPE_PROPOSAL: return "allow-proposal";
    case PIPE_CLARIFY: return "clarify";
    case PIPE_UNSUPPORTED: return "unsupported";
    case PIPE_DENY: case PIPE_INTERNAL: return "deny";
    }
    return "deny";
}
static void effect_scope(struct writer *w,const struct request *q,const struct resolved_ir *r,bool allowed)
{
    add(w,",\"effect\":");
    add(w,allowed?rules[r->intent].effect_json:"{\"class\":\"UNKNOWN\",\"axes\":[]}");
    add(w,",\"scope\":{"); field(w,"kind",allowed?"local":"none");
    if (allowed) { add(w,","); field(w,"scope_id",q->scope_id); }
    add(w,"}");
}
static void decision_identity(struct writer *w,const struct request *q)
{
    add(w,","); field(w,"decision_id",q->decision_id); add(w,",\"policy\":"); identity(w,FIXTURE_POLICY_SHA);
}
static bool serialize_policy(const struct request *q,const struct resolved_ir *r,
                             struct policy_decision p,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    common(&w,q); decision_identity(&w,q);
    add(&w,","); field(&w,"decision",decision_name(p.outcome)); effect_scope(&w,q,r,p.outcome==PIPE_PROPOSAL);
    add(&w,","); field(&w,"reason",p.reason); add(&w,"}");
    return validate_frame(&w,IR_POLICY);
}
static bool serialize_plan(const struct request *q,const struct resolved_ir *r,
                           const char *digest,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    common(&w,q); decision_identity(&w,q);
    add(&w,","); field(&w,"action_id",q->action_id); effect_scope(&w,q,r,true);
    add(&w,",\"target_bindings\":[");
    bool comma=false;
    for (size_t i=0;i<r->count;++i) {
        const enum slot_name name=r->slots[i].rule->name;
        if (name!=S_UNIT && name!=S_ROOT) continue;
        char id[33];
        if (!id_from(q,slot_names[name],id)) return false;
        if (comma) add(&w,",");
        comma=true; add(&w,"{"); field(&w,"slot",slot_names[name]); add(&w,","); field(&w,"binding_id",id); add(&w,"}");
    }
    add(&w,"],\"action\":{\"kind\":\"structured-proposal\",\"operation\":{\"kind\":\"native\",");
    field(&w,"handler",rules[r->intent].handler); add(&w,",\"input_slots\":[");
    for (size_t i=0;i<r->count;++i) { if (i!=0) add(&w,","); quote(&w,slot_names[r->slots[i].rule->name]); }
    add(&w,"]}},"); field(&w,"digest",digest); add(&w,"}");
    return validate_frame(&w,IR_PLAN);
}
static bool compile(const struct request *q,const struct resolved_ir *r,struct policy_decision p,char out[PIPE_FRAME])
{
    if (p.outcome!=PIPE_PROPOSAL || r->state!=RES_RESOLVED || r->intent>=COUNT(rules) ||
        r->pending_count!=0 || r->alternative_count!=0) return false;
    char digest[65];
    struct ir_document doc={0};
    const char placeholder_digest[]="0000000000000000000000000000000000000000000000000000000000000000";
    bool ok=serialize_plan(q,r,placeholder_digest,out) &&
        ir_parse(&doc,(const unsigned char *)out,strlen(out))==IR_OK && ir_plan_digest(&doc,digest);
    ir_destroy(&doc);
    ok=ok && serialize_plan(q,r,digest,out) &&
        ir_parse(&doc,(const unsigned char *)out,strlen(out))==IR_OK && ir_plan_digest_matches(&doc);
    ir_destroy(&doc);
    return ok;
}
static bool render(const struct resolved_ir *r,struct policy_decision p,const char *plan,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    if ((p.outcome==PIPE_PROPOSAL)!=(plan[0]!='\0')) return false;
    add(&w,"{\"copyability\":\"NON_COPYABLE\",");
    field(&w,"decision",decision_name(p.outcome)); add(&w,","); field(&w,"reason",p.reason);
    add(&w,",\"execution_allowed\":false,\"observed_os_data\":false,");
    field(&w,"source","F0-C synthetic catalog; actual Debian binding NOT VERIFIED");
    if (r->intent!=NO_INTENT) {
        add(&w,","); field(&w,"intent",rules[r->intent].id);
        add(&w,","); field(&w,"description",rules[r->intent].description_id);
    }
    if (p.outcome==PIPE_PROPOSAL) {
        add(&w,","); field(&w,"effect",rules[r->intent].effect_class);
        add(&w,","); field(&w,"scope","synthetic fixture; no filesystem or service access");
        if (strcmp(rules[r->intent].effect_class,"CHANGE")==0) {
            add(&w,","); field(&w,"warning","CHANGE; may require privilege; no sudo and no execution");
        }
        add(&w,",\"slots\":{");
        for (size_t i=0;i<r->count;++i) {
            if (i!=0) add(&w,",");
            quote(&w,slot_names[r->slots[i].rule->name]); add(&w,":"); typed_value(&w,&r->slots[i]);
        }
        add(&w,"}");
    } else if (p.outcome==PIPE_CLARIFY) {
        add(&w,",\"unresolved\":"); pending_json(&w,r);
        add(&w,",\"alternatives\":[");
        for (size_t i=0;i<r->alternative_count;++i) { if (i!=0) add(&w,","); quote(&w,rules[r->alternatives[i]].id); }
        add(&w,"]");
    }
    add(&w,"}");
    return w.ok;
}

bool pipeline_run(const unsigned char *input,size_t size,int64_t reference_unix_s,
                  uint64_t request_sequence,enum pipeline_model model,struct pipeline_result *out)
{
    if (out==NULL) return false;
    *out=(struct pipeline_result){.outcome=PIPE_INTERNAL};
    if (model!=PIPE_B0 && model!=PIPE_B1) return false;
    if (ir_check_input(input,size)!=IR_OK) {
        out->outcome=PIPE_DENY;
        const struct resolved_ir r={.state=RES_INVALID,.intent=NO_INTENT};
        return render(&r,policy(&r),out->plan,out->view);
    }
    struct request q={.data=input,.size=size,.reference=reference_unix_s};
    if (!context(&q,request_sequence,out->context)) return false;
    const struct nlu_proposal n=propose(&q,model);
    if (!serialize_nlu(&q,&n,out->nlu)) return false;
    const struct resolved_ir r=resolve(&q,&n);
    if (!serialize_ir(&q,&r,out->ir)) return false;
    const struct policy_decision p=policy(&r);
    if (!serialize_policy(&q,&r,p,out->policy)) return false;
    if (p.outcome==PIPE_PROPOSAL && !compile(&q,&r,p,out->plan)) return false;
    if (!render(&r,p,out->plan,out->view)) return false;
    out->outcome=p.outcome;
    return true;
}
bool pipeline_search(const char *id,char out[PIPE_FRAME])
{
    if (id==NULL || out==NULL) return false;
    struct writer w=writer(out,PIPE_FRAME);
    for (size_t i=0;i<COUNT(rules);++i) if (strcmp(id,rules[i].id)==0) {
        add(&w,"{"); field(&w,"intent",rules[i].id); add(&w,","); field(&w,"id",rules[i].description_id);
        add(&w,","); field(&w,"en",rules[i].description_en);
        add(&w,",\"copyable\":false,\"execution_allowed\":false}"); return w.ok;
    }
    return false;
}
bool pipeline_inspect(char out[PIPE_FRAME])
{
    if (out==NULL) return false;
    struct writer w=writer(out,PIPE_FRAME);
    add(&w,"{\"mode\":\"F0-C synthetic proposal-only\",\"primary\":\"B0-rules\",\"alternative\":\"B1-guarded-word-retrieval\","
        "\"neural_parameters\":0,\"intent_count\":8,\"profile\":\"debian-13 NOT VERIFIED\",");
    field(&w,"catalog_sha256",FIXTURE_CATALOG_SHA); add(&w,","); field(&w,"profile_sha256",FIXTURE_PROFILE_SHA);
    add(&w,","); field(&w,"policy_sha256",FIXTURE_POLICY_SHA);
    add(&w,",\"execution_allowed\":false,\"latency\":\"not measured by inspect\"}");
    return w.ok;
}
