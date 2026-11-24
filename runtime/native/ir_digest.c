#include "ir_digest.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

static const uint32_t constants[64] = {
    0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
    0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
    0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
    0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
    0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
    0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
    0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
    0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
};
static const char hex[] = "0123456789abcdef";

static uint32_t rotr(uint32_t x, unsigned int n)
{
    return (x >> n) | (x << (32u - n));
}

static void compress(uint32_t h[8], const unsigned char block[64])
{
    uint32_t w[64];
    for (size_t i = 0; i < 16; ++i) {
        const unsigned char *p = block + i * 4;
        w[i] = ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16)
            | ((uint32_t)p[2] << 8) | p[3];
    }
    for (size_t i = 16; i < 64; ++i) {
        const uint32_t x = w[i-15], y = w[i-2];
        w[i] = w[i-16] + (rotr(x,7) ^ rotr(x,18) ^ (x >> 3))
            + w[i-7] + (rotr(y,17) ^ rotr(y,19) ^ (y >> 10));
    }
    uint32_t a=h[0], b=h[1], c=h[2], d=h[3], e=h[4], f=h[5], g=h[6], v=h[7];
    for (size_t i=0; i<64; ++i) {
        const uint32_t t1 = v + (rotr(e,6) ^ rotr(e,11) ^ rotr(e,25))
            + ((e & f) ^ (~e & g)) + constants[i] + w[i];
        const uint32_t t2 = (rotr(a,2) ^ rotr(a,13) ^ rotr(a,22))
            + ((a & b) ^ (a & c) ^ (b & c));
        v=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    h[0]+=a; h[1]+=b; h[2]+=c; h[3]+=d; h[4]+=e; h[5]+=f; h[6]+=g; h[7]+=v;
}

bool ir_sha256_hex(const unsigned char *data, size_t size, char out[65])
{
    if (out == NULL) return false;
    out[0] = '\0';
    if (size > 65536u || (size != 0 && data == NULL)) return false;
    uint32_t h[8] = {0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
                     0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u};
    size_t pos = 0;
    while (size-pos >= 64u) { compress(h,data+pos); pos+=64u; }
    unsigned char last[128] = {0};
    const size_t tail=size-pos;
    if (tail != 0) memcpy(last,data+pos,tail);
    last[tail]=0x80u;
    const size_t blocks=tail<56u ? 64u : 128u;
    const uint64_t bits=(uint64_t)size*8u;
    for (size_t i=0; i<8; ++i) last[blocks-1-i]=(unsigned char)(bits >> (i*8u));
    compress(h,last);
    if (blocks==128u) compress(h,last+64);
    for (size_t i=0;i<8;++i)
        for (size_t j=0;j<8;++j) out[i*8+j]=hex[(h[i] >> (28u-4u*j)) & 15u];
    out[64]='\0';
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
