#include "ir_digest.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include <openssl/evp.h>

static const char hex[] = "0123456789abcdef";

bool ir_sha256_hex(const unsigned char *data, size_t size, char out[65])
{
    if (out == NULL) return false;
    out[0] = '\0';
    if (size > 65536u || (size != 0 && data == NULL)) return false;
    unsigned char digest[32];
    unsigned int length = 0;
    /* Maintained library, not a home-grown crypto primitive. SHA-256 is
     * content identity only, not signature, authentication or approval. */
    if (EVP_Digest(data == NULL ? (const unsigned char *)"" : data, size,
                   digest, &length, EVP_sha256(), NULL) != 1 || length != sizeof(digest)) return false;
    for (size_t i = 0; i < sizeof(digest); ++i) {
        out[i*2] = hex[digest[i] >> 4];
        out[i*2+1] = hex[digest[i] & 15u];
    }
    out[64] = '\0';
    return true;
}

struct buffer { unsigned char bytes[DICTUM_FRAME_MAX+64u]; size_t used; };
static bool append(struct buffer *b, const void *data, size_t len)
{
    if (len > sizeof(b->bytes)-b->used) return false;
    if (len != 0) memcpy(b->bytes+b->used,data,len);
    b->used+=len;
    return true;
}
static bool put(struct buffer *b, unsigned char c) { return append(b,&c,1); }

static bool quote(struct buffer *b, const unsigned char *s, size_t len)
{
    if (!put(b,'"')) return false;
    for (size_t i=0;i<len;++i) {
        const unsigned char c=s[i];
        switch (c) {
        case '"': if (!append(b,"\\\"",2)) return false; break;
        case '\\': if (!append(b,"\\\\",2)) return false; break;
        case '\b': if (!append(b,"\\b",2)) return false; break;
        case '\t': if (!append(b,"\\t",2)) return false; break;
        case '\n': if (!append(b,"\\n",2)) return false; break;
        case '\f': if (!append(b,"\\f",2)) return false; break;
        case '\r': if (!append(b,"\\r",2)) return false; break;
        default:
            if (c<0x20u) {
                const char esc[]={'\\','u','0','0',hex[c>>4],hex[c&15u]};
                if (!append(b,esc,sizeof(esc))) return false;
            } else if (!put(b,c)) return false;
        }
    }
    return put(b,'"');
}

/* The closed IR schemas require ASCII property names. For that subset,
 * lexicographic UTF-8 bytes and RFC 8785 UTF-16 code-unit order coincide. */
static int compare(const struct ir_document *d, size_t x, size_t y)
{
    const struct ir_node *a=&d->nodes[x],*b=&d->nodes[y];
    const size_t len=a->length<b->length ? a->length : b->length;
    const int cmp=memcmp(d->strings+a->offset,d->strings+b->offset,len);
    if (cmp!=0) return cmp;
    return a->length>b->length ? 1 : a->length<b->length ? -1 : 0;
}

static bool key_digest(const struct ir_document *d,size_t i)
{
    const struct ir_node *n=&d->nodes[i];
    return n->length==6 && memcmp(d->strings+n->offset,"digest",6)==0;
}

static bool canonical(struct buffer *b,const struct ir_document *d,size_t i,bool root)
{
    const struct ir_node *n=&d->nodes[i];
    switch (n->kind) {
    case IR_OBJECT: {
        size_t order[DICTUM_OBJECT_MAX], count=0;
        for (size_t k=n->first;k!=0;k=d->nodes[k].next) {
            if (root && key_digest(d,k)) continue;
            if (count>=DICTUM_OBJECT_MAX) return false;
            size_t j=count++;
            while (j>0 && compare(d,order[j-1],k)>0) { order[j]=order[j-1]; --j; }
            order[j]=k;
        }
        if (!put(b,'{')) return false;
        for (size_t j=0;j<count;++j) {
            const struct ir_node *k=&d->nodes[order[j]];
            if ((j!=0 && !put(b,',')) || !quote(b,d->strings+k->offset,k->length)
                || !put(b,':') || !canonical(b,d,k->first,false)) return false;
        }
        return put(b,'}');
    }
    case IR_ARRAY:
        if (!put(b,'[')) return false;
        for (size_t k=n->first;k!=0;k=d->nodes[k].next)
            if ((k!=n->first && !put(b,',')) || !canonical(b,d,k,false)) return false;
        return put(b,']');
    case IR_STRING: return quote(b,d->strings+n->offset,n->length);
    case IR_INTEGER: {
        char token[32];
        const int len=snprintf(token,sizeof(token),"%" PRId64,n->integer);
        return len>0 && (size_t)len<sizeof(token) && append(b,token,(size_t)len);
    }
    /* These types are excluded by the current plan schema. */
    case IR_TRUE: case IR_FALSE: case IR_NULL: return false;
    }
    return false;
}

bool ir_plan_digest(const struct ir_document *doc,char out[65])
{
    if (out==NULL) return false;
    out[0]='\0';
    if (ir_validate(doc,IR_PLAN)!=IR_OK) return false;
    struct buffer b={0};
    const char prefix[]="dictum:execution-plan:v1\n";
    return append(&b,prefix,sizeof(prefix)-1) && canonical(&b,doc,1,true)
        && ir_sha256_hex(b.bytes,b.used,out);
}

bool ir_plan_digest_matches(const struct ir_document *doc)
{
    char digest[65];
    if (!ir_plan_digest(doc,digest)) return false;
    for (size_t k=doc->nodes[1].first;k!=0;k=doc->nodes[k].next)
        if (key_digest(doc,k)) {
            const struct ir_node *n=&doc->nodes[doc->nodes[k].first];
            return n->length==64 && memcmp(doc->strings+n->offset,digest,64)==0;
        }
    return false;
}
