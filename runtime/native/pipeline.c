#include "pipeline.h"
#ifdef DICTUM_DEV_B2
#include "pipeline_b2_dev.h"
#endif
#include "ir_digest.h"
#include "renderer.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
#define TOKENS 64u
#define SLOTS 16u
#define NO_INTENT SIZE_MAX
enum slot_name { S_PORT, S_PROTOCOL, S_UNIT, S_WINDOW, S_LIMIT, S_ROOT, S_DEPTH, S_EXTENSION, S_FILENAME, S_PATH,
    S_UTILITY, S_OPTION, S_DOMAIN, S_TARGET, S_TEXT, S_DIRECTION, S_NAME, S_PACKAGE, S_QUERY,
    S_RECORD_TYPE, S_COUNT, S_ARCHIVE, S_SOURCE, S_DESTINATION };
enum slot_kind { K_INTEGER, K_PROTOCOL, K_LITERAL, K_TIME, K_DOMAIN };
static const char *const slot_names[]={"port","protocol","unit","window","limit","root","depth","extension","filename","path",
    "utility","option","domain","target","text","direction","name","package","query",
    "record_type","count","archive","source","destination"};

struct slot_rule {
    enum slot_name name;
    enum slot_kind kind;
    const char *type;
    bool required, has_default;
    int64_t min, max, number;
    const char *literal;
};
struct intent_rule {
    const char *id,*handler,*effect_class,*effect_json,*description_id,*description_en,*guidance;
    struct slot_rule slots[SLOTS];
    size_t count;
};
struct grammar { size_t intent; const char *pattern; };
struct lexical_term { const char *word; uint64_t intents; unsigned int weight; };
struct domain_pair { const char *kind,*value; };
struct help_entry { const char *utility,*option,*text; };
struct catalog_entry { const char *id; const char *metadata_json; };
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
static size_t polite_start(const struct request *q,size_t first,size_t end)
{
    if (first<end && (word(q,first,"tolong")||word(q,first,"please")||word(q,first,"mohon"))) return first+1;
    if (end-first>=2u && (word(q,first,"could")||word(q,first,"can")) && word(q,first+1,"you")) return first+2;
    return first;
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
            if (word(q,i,deny_tokens[j])) {
                const size_t start=polite_start(q,0,q->tokens.count);
                if (strcmp(deny_tokens[j],"ping")==0 && i==start+1u &&
                    (word(q,start,"propose")||word(q,start,"usulkan"))) continue;
                return true;
            }
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
        if (ascii_integer(q,q->tokens.item[i-1],1,FIXTURE_MAX_WINDOW_SECONDS/60,&mins) && q->reference>=mins*60) {
            q->time_token=q->tokens.item[i-1]; q->time_start=q->reference-mins*60; q->time_valid=true;
        }
    }
    q->time_valid=q->time_valid && time_hits==1;
    char input_hash[65];
    if (!ir_sha256_hex(q->data,q->size,input_hash)) return false;
    struct writer w=writer(out,2048);
    add(&w,"{"); field(&w,"mode","synthetic-request-v2"); add(&w,",");
    field(&w,"input_sha256",input_hash); add(&w,","); field(&w,"catalog_sha256",FIXTURE_CATALOG_SHA);
    add(&w,","); field(&w,"profile_sha256",FIXTURE_PROFILE_SHA); add(&w,",");
    field(&w,"registry_sha256",FIXTURE_REGISTRY_SHA); add(&w,",");
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
        if (word(q,i,"limit")||word(q,i,"batas")) name=S_LIMIT;
        else if (word(q,i,"depth")||word(q,i,"kedalaman")) name=S_DEPTH;
        else if (word(q,i,"count")||word(q,i,"jumlah")) name=S_COUNT;
        else if (word(q,i,"protocol")||word(q,i,"protokol")) name=S_PROTOCOL;
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
    first=polite_start(q,first,end);
    if (first<end && (word(q,end-1,"please")||word(q,end-1,"tolong"))) --end;
    bool found=false;
    size_t best_specificity=0;
    for (size_t i=0;i<COUNT(grammar);++i) {
        struct nlu_proposal candidate;
        if (!match_grammar(q,&grammar[i],first,end,&candidate)) continue;
        size_t specificity=0;
        for (const char *p=grammar[i].pattern;*p!='\0';++p) {
            if (*p=='{') { while (*p!='}' && *p!='\0') ++p; if (*p=='\0') break; }
            else ++specificity;
        }
        if (found && specificity<best_specificity) continue;
        if (found && specificity==best_specificity) {
            if (candidate.intents[0]!=n->intents[0] || candidate.used!=n->used) return false;
            for (size_t j=0;j<n->used;++j)
                if (candidate.candidates[j].name!=n->candidates[j].name ||
                    candidate.candidates[j].token.start!=n->candidates[j].token.start ||
                    candidate.candidates[j].token.end!=n->candidates[j].token.end) return false;
        } else { *n=candidate; found=true; best_specificity=specificity; }
    }
    return found;
}
static size_t retrieve(const struct request *q,const struct nlu_proposal *n)
{
    /* Weighted distinct lexical matches over pinned reference descriptions.
     * All explicit slot tokens masked, common words excluded at build time.
     * No grammar bypass, no fitting against development labels. */
    unsigned int scores[COUNT(rules)]={0};
    for (size_t j=0;j<COUNT(lexical_terms);++j) {
        const struct lexical_term *term=&lexical_terms[j];
        bool present=false;
        for (size_t i=0;i<q->tokens.count;++i) {
            const struct token t=q->tokens.item[i];
            bool masked=false;
            for (size_t k=0;k<n->used;++k)
                if (n->candidates[k].token.start==t.start) masked=true;
            if (!masked && token_eq(q->data,t,term->word,strlen(term->word))) {
                present=true; break;
            }
        }
        if (present) for (size_t i=0;i<COUNT(rules);++i)
            if ((term->intents & (UINT64_C(1)<<i))!=0) scores[i]+=term->weight;
    }
    size_t best=NO_INTENT; unsigned int score=0; bool tie=false;
    for (size_t i=0;i<COUNT(rules);++i) {
        if (scores[i]>score) { best=i; score=scores[i]; tie=false; }
        else if (scores[i]==score && score!=0) tie=true;
    }
    return tie ? NO_INTENT : best;
}
#ifdef DICTUM_DEV_COMPOSE
/* Research-only closed lexical composition for default-only/slotless
 * INFO/READ. Unlike a similarity threshold, every token is consumed by
 * a finite vocabulary and two intent-specific cue groups are mandatory.
 * No slot extraction, command strings, NET/CHANGE, authority or fallback
 * in the product. This is a limited semantic hypothesis, not gold. */
struct compose_frame { const char *id,*first,*second,*extra; };
static const struct compose_frame compose_frames[]={
    {"system.os.info","os operating distro distribution linux operasi","kernel release version architecture rilis versi arsitektur","machine platform host identity identity information info identitas informasi tipe jenis serta and dan with beserta"},
    {"system.uptime.summary","uptime startup boot menyala berjalan hidup","load beban average rerata rata-rata","duration elapsed running time since lama durasi sejak mesin host system sistem together with beserta serta averages rata durasi saat"},
    {"network.connection.active","connection connections sambungan koneksi","active current currently aktif sedang sekarang","network jaringan local lokal visible terlihat entries daftar status state existing currently machine mesin session sessions sesi"},
    {"network.interface.list","interface interfaces adapter adapters nic antarmuka kartu","address addresses link alamat status keadaan","network jaringan assigned visible local lokal available tersedia states state kondisi sambungan fisik beserta serta per setiap tiap detected terdeteksi"},
    {"network.route.table","route routes routing rute jalur","gateway table next gerbang tabel default utama","ip traffic lalu lintas lokal local host machine mesin hop entries entry konfigurasi configuration yang dikenal berlaku"},
    {"network.dns.config","dns resolver resolvers resolusi","configuration settings configured konfigurasi pengaturan dikonfigurasi","name nama server local lokal active aktif host mesin currently used digunakan"},
    {"service.list.active","service services layanan unit units","active running aktif berjalan","state keadaan currently current presently sedang sekarang kondisi masih operational operasional"},
    {"service.failed.list","service services layanan unit units","failed gagal","state keadaan current currently marked presently berstatus status sekarang masih dalam terakhirnya"},
    {"service.enabled.list","service services layanan unit units","enabled enablement diaktifkan","boot startup start mulai next process proses configured konfigurasi saat ketika untuk ditetapkan"},
    {"log.boot.messages","kernel boot startup","messages message records log catatan pesan","accessible visible available last latest recent terakhir terkini terlihat lokal locally sesi ketika setelah"},
    {"storage.filesystem.usage","filesystem filesystems berkas","capacity usage used free space available kapasitas penggunaan pemakaian terpakai bebas sisa ruang storage penyimpanan","byte bytes accounting mounted terpasang disk per each tiap setiap file systems system sistem local lokal statistics statistik available"},
    {"storage.inode.usage","inode inodes","usage utilization allocation counts count used free availability penggunaan terpakai tersisa bebas jumlah kapasitas persentase","filesystem filesystems file systems sistem berkas local lokal mounted across per each tiap setiap statistik allocation"},
    {"storage.block.list","block blok","device devices disk perangkat partition partitions partisi","storage penyimpanan topology susunan attached visible detected terdeteksi lokal local mount mounts points locations lokasi"},
    {"storage.mount.list","mount mounts mounted pemasangan terpasang","filesystem filesystems locations location table points titik options opsi","file systems sistem berkas permitted allowed boleh aman safe metadata tipe type active aktif current sekarang local lokal"},
    {"process.list.top_cpu","process processes proses","cpu processor prosesor","highest greatest most top intensive usage consumption utilization rank urutkan teratas dominan persentase penggunaan pemakaian membebani running tinggi terbesar paling saat sekarang"},
    {"process.list.top_mem","process processes proses","rss resident","memory ram memori highest largest most top consumption usage occupy rank urutkan teratas dominan pemakaian penggunaan konsumsi tinggi terbesar paling"},
    {"process.tree.view","process processes proses antarproses","parent child ancestry parentage induk anak keturunan","tree hierarchy hierarki pohon relationships hubungan susunan structure struktur pid among between antar"},
    {"memory.summary","memory ram memori","available free cache swap tersedia bebas kapasitas","physical fisik system sistem mesin machine local lokal summary ringkasan summarize total remaining remains usage penggunaan pemakaian kondisi keadaan gambaran tekanan pressure beserta dan and dengan"},
    {"cpu.hardware.info","cpu processor prosesor","architecture topology arsitektur topologi","hardware cores core threads thread frequency frekuensi jumlah logical logical spesifikasi karakteristik perangkat keras details detail configuration konfigurasi tipe jenis berapa present"},
    {"user.session.who","session sessions sesi","login logged-in masuk","user users pengguna visible currently current existing aktif tercatat terlihat present sedang sekarang mempunyai daftar siapa"},
    {"user.identity.info","uid gid","identity credentials identitas","numeric current user group groups supplementary membership memberships nomor pengguna grup keanggotaan saya my sedang digunakan values value nilai"},
    {"diagnosis.disk_full","diagnosis diagnose diagnostic troubleshooting investigate panduan diagnosis telusuri","disk storage filesystem penyimpanan","full exhaustion shortage penuh habis kehabisan ruang space capacity kapasitas cause penyebab langkah guidance guidance mencari sebab investigate"},
    {"diagnosis.high_load","diagnosis diagnose diagnostic troubleshooting investigate panduan analisis","load beban","high elevated excessive pressure tinggi berlebihan melonjak sustained abnormally cause penyebab langkah mencari sebab guidance sistem system mesin machine average"},
    {"diagnosis.dns_failure","diagnosis diagnose diagnostic troubleshooting investigate panduan","dns resolver resolusi","failure failed unsuccessful gagal kegagalan bermasalah lookup resolution name nama hostname diresolusi cause penyebab langkah mencari sebab guidance"},
};
static bool compose_wordlist(const struct request *q,size_t i,const char *list)
{
    const struct token t=q->tokens.item[i];
    for (const char *p=list;*p!='\0';) {
        while (*p==' ') ++p;
        if (*p=='\0') break;
        size_t len=0;
        while (p[len]!='\0' && p[len]!=' ') ++len;
        if (token_eq(q->data,t,p,len)) return true;
        p+=len;
    }
    return false;
}
static bool compose_prefix(const struct request *q,size_t *start)
{
    const size_t n=q->tokens.count;
    *start=polite_start(q,0,n);
    if (*start>=n) return false;
    const size_t i=*start;
    static const char *const two[][2]={
        {"saya","ingin"},{"saya","perlu"},{"saya","butuh"},{"tell","me"},
        {"give","me"},{"i","need"},{"i","want"},{"what","is"},{"what","are"},
        {"how","long"},{"how","much"},{"which","of"}
    };
    for (size_t j=0;j<COUNT(two);++j)
        if (i+1<n && word(q,i,two[j][0]) && word(q,i+1,two[j][1])) {
            *start=i+2; return true;
        }
    if (compose_wordlist(q,i,"show report summarize list enumerate identify inspect describe outline guide give find locate compare check display rank urutkan which what how tampilkan perlihatkan ringkas rangkum rinci rincikan jelaskan beri berikan daftar cari cek periksa apa apakah berapa bagaimana bantu")) {
        *start=i+1; return true;
    }
    return false;
}
static bool compose_match(const struct request *q,struct nlu_proposal *n)
{
    *n=(struct nlu_proposal){0};
    size_t start=0;
    if (q->invalid || q->time_valid || q->tokens.count>32u || !compose_prefix(q,&start) ||
        q->tokens.count-start<2u) return false;
    /* Words carry no authority by themselves. Reject negation, alternatives,
     * unknown syntax, quoted or literal/numeric targets rather than ignore. */
    for (size_t i=0;i<q->tokens.count;++i)
        if (q->tokens.item[i].quoted || compose_wordlist(q,i,
            "not no never dont don't without except or versus vs bukan tidak jangan tanpa kecuali atau abaikan ignore bypass")) return false;
    static const char *const common=
        "a an the of for from to in on at by with and as is are was were be being me my this that it i "
        "want need know information details about see currently now local machine host system "
        "saya ingin perlu butuh mengetahui tahu melihat informasi tentang pada dalam di dari ke "
        "yang dan serta dengan untuk saat kini ini itu tersebut mesin sistem host lokal sekarang tiap setiap per berdasarkan bagaimana apa berapa saja mana";
    size_t selected=NO_INTENT;
    for (size_t f=0;f<COUNT(compose_frames);++f) {
        const struct compose_frame *frame=&compose_frames[f];
        bool first=false,second=false,ok=true;
        for (size_t i=start;i<q->tokens.count;++i) {
            if (compose_wordlist(q,i,frame->first)) first=true;
            else if (compose_wordlist(q,i,frame->second)) second=true;
            else if (!compose_wordlist(q,i,frame->extra) && !compose_wordlist(q,i,common)) {
                ok=false; break;
            }
        }
        if (!ok || !first || !second) continue;
        if (strcmp(frame->id,"process.list.top_cpu")==0 || strcmp(frame->id,"process.list.top_mem")==0) {
            bool ranking=false;
            for (size_t i=0;i<q->tokens.count;++i)
                if (compose_wordlist(q,i,"rank highest greatest most top largest teratas tertinggi terbesar dominan paling urutkan")) ranking=true;
            if (!ranking) continue;
        }
        if (strncmp(frame->id,"diagnosis.",10u)==0) {
            bool topic=false;
            const char *cue=strcmp(frame->id,"diagnosis.disk_full")==0 ? "full exhaustion shortage penuh habis kehabisan" :
                strcmp(frame->id,"diagnosis.high_load")==0 ? "high elevated excessive pressure tinggi berlebihan melonjak" :
                "failure failed unsuccessful gagal kegagalan bermasalah";
            for (size_t i=0;i<q->tokens.count;++i) if (compose_wordlist(q,i,cue)) topic=true;
            if (!topic) continue;
        }
        size_t candidate=NO_INTENT;
        for (size_t i=0;i<COUNT(rules);++i)
            if (strcmp(rules[i].id,frame->id)==0) { candidate=i; break; }
        if (candidate==NO_INTENT) return false;
        const struct intent_rule *rule=&rules[candidate];
        if (strcmp(rule->effect_class,"READ")!=0 && strcmp(rule->effect_class,"INFO")!=0) return false;
        for (size_t j=0;j<rule->count;++j)
            if (!rule->slots[j].required || !rule->slots[j].has_default) return false;
        if (selected!=NO_INTENT && selected!=candidate) return false;
        selected=candidate;
    }
    if (selected==NO_INTENT) return false;
    n->intents[0]=selected;
    n->count=1;
    return true;
}

/* Typed research frames. Each explicitly bound role consumes exactly one
 * original token. Values must already satisfy the existing typed resolver
 * and scope; no new normalizer, inference, target, default or authority.
 * Closed cue vocabulary is separate from the slotless experiment. */
static bool value_from(const struct request *q,const struct candidate *c,const struct slot_rule *r,struct value *v);
static bool slot_scope(const struct intent_rule *rule,const struct value *v);
struct typed_frame {
    const char *id,*first,*second,*extra;
    enum slot_name slots[3];
    size_t count;
    const char *third;
    unsigned int optional_mask;
};
static const struct typed_frame typed_frames[]={
    {"service.status.get","service services unit units layanan",
        "status state keadaan kondisi",
        "runtime current active aktif utama main process proses pid information informasi named bernama",
        {S_UNIT},1,NULL,0u},
    {"storage.directory.usage","directory directories subdirectories folder folders subfolder subfolders direktori subdirektori",
        "largest heaviest size sizes space capacity terbesar ukuran ruang",
        "child anak consume consumption consuming use usage occupied penggunaan pemakaian berdasarkan contained within below under bawah di paling rank",
        {S_ROOT},1,NULL,0u},
    {"file.metadata.stat","file files berkas",
        "metadata attributes attribute atribut timestamps timestamp ukuran size kepemilikan owner pemilik",
        "ownership modification modified changed time waktu perubahan details detail termasuk",
        {S_PATH},1,NULL,0u},
    {"file.permission.check","file files berkas",
        "permission permissions access akses hak izin",
        "effective efektif allowed mode modes read write baca tulis identity identitas terhadap",
        {S_PATH},1,NULL,0u},
    {"archive.contents.list","archive archives arsip",
        "member members entries contents entry anggota isi entri",
        "names name nama stored inside contained paket list daftar hanya only",
        {S_PATH},1,NULL,0u},
    {"process.lookup.name","process processes proses",
        "name named nama bernama pid identifiers identifier",
        "exact tepat persis literal running berjalan associated allowed details detail memiliki",
        {S_NAME},1,"named bernama pid identifiers identifier exact tepat persis literal",0u},
    {"package.installed.check","package packages paket",
        "installed installation install terpasang terinstal instalasi",
        "version versions versi status presence local database basis data informasi apakah berapa versinya",
        {S_PACKAGE},1,NULL,0u},
    {"package.search.local","package packages paket",
        "cache cached index indeks offline repositori repository",
        "literal matching match matches pencarian kecocokan kata nama metadata results hasil search",
        {S_QUERY},1,NULL,0u},
    {"file.text.search","text teks string literal",
        "file files berkas line lines baris occurrences occurrence kemunculan",
        "exact persis matching contained berisi below under within bawah bounded search",
        {S_ROOT,S_TEXT},2,NULL,0u},
    {"file.head_tail.view","line lines baris",
        "file berkas excerpt potongan",
        "text teks end akhir bagian contained sebanyak arah",
        {S_PATH,S_DIRECTION,S_LIMIT},3,NULL,0u},
    {"file.search","file files berkas entries",
        "extension ekstensi berekstensi akhiran suffix",
        "ending beneath below under within inside folder directory directories direktori jenis berada bawah pencarian",
        {S_ROOT,S_EXTENSION},2,NULL,0u},
    {"network.listener.lookup","listener listening socket pendengar menunggu accepting",
        "port",
        "associated accepting accepts connections connection koneksi waiting menunggu opens membuka process processes proses layanan milik siapa mana menggunakan",
        {S_PORT,S_PROTOCOL},2,NULL,2u},
    {"network.connection.active","connection connections sambungan koneksi",
        "active current currently established aktif sedang sekarang",
        "network jaringan entries entry daftar maximum maksimum batas limit protocol protokol",
        {S_PROTOCOL,S_LIMIT},2,NULL,0u},
    {"log.service.query","journal journals log logs jurnal catatan",
        "service services unit units layanan",
        "entries entry records record pesan messages message over within during selama sepanjang interval minutes menit last past previous terakhir belakangan",
        {S_UNIT,S_WINDOW},2,NULL,0u},
    {"log.system.errors","journal journals log logs jurnal catatan",
        "system sistem",
        "error errors severity priority high emergency emerg galat kesalahan prioritas pesan messages entries records over within selama sepanjang interval minutes menit last past previous terakhir belakangan",
        {S_WINDOW},1,"error errors galat kesalahan",0u},
};
static bool typed_prefix(const struct request *q,size_t *start)
{
    if (compose_prefix(q,start)) return true;
    const size_t i=polite_start(q,0,q->tokens.count);
    if (i>=q->tokens.count) return false;
    if (compose_wordlist(q,i,"determine search retrieve temukan identifikasi telusuri ambil")) {
        *start=i+1; return true;
    }
    if ((word(q,i,"look") && word(q,i+1,"for")) ||
        (word(q,i,"saya") && (word(q,i+1,"mencari") || word(q,i+1,"mau")))) {
        *start=i+2; return true;
    }
    return false;
}
/* A value is not evidence for a role by itself. Numeric/time/filter
 * roles require local lexical anchors; a context window must already
 * exist and denote the past, never a new timestamp guessed by NLU. */
static bool typed_role_anchor(const struct request *q,const struct typed_frame *f,size_t i,enum slot_name name)
{
    if (name==S_TEXT)
        return i>0u && compose_wordlist(q,i-1u,"literal text string teks persis exact");
    if (name==S_ROOT)
        return i>0u && compose_wordlist(q,i-1u,"under beneath below within inside in at from folder directory directories root di pada dalam bawah direktori dari");
    if (name==S_QUERY)
        return i>0u && compose_wordlist(q,i-1u,"matching match matches literal keyword query kata nama pencarian for");
    if (name==S_NAME)
        return i>0u && compose_wordlist(q,i-1u,"name named nama bernama exact tepat persis literal");
    if (name==S_UNIT) {
        if (i>0u && compose_wordlist(q,i-1u,"service unit layanan named bernama")) return true;
        return strcmp(f->id,"log.service.query")==0 && i>1u &&
            compose_wordlist(q,i-1u,"of for from") &&
            compose_wordlist(q,i-2u,"journal journals log logs entries entry records record");
    }
    if (name==S_PACKAGE)
        return i>0u && compose_wordlist(q,i-1u,"package paket version versi");
    if (name==S_PATH)
        return i>0u && compose_wordlist(q,i-1u,"file files berkas archive arsip metadata of for from to dari terhadap pada");
    if (name==S_PORT) return i>0u && word(q,i-1u,"port");
    if (name==S_EXTENSION) return i>0u && compose_wordlist(q,i-1u,"extension ekstensi berekstensi akhiran suffix");
    if (name==S_WINDOW) {
        if (!q->time_valid) return false;
        const bool before=i>0u && compose_wordlist(q,i-1u,"last past previous");
        const bool after=i+2u<q->tokens.count && compose_wordlist(q,i+2u,"terakhir belakangan");
        return before || after;
    }
    if (name==S_LIMIT && strcmp(f->id,"network.connection.active")==0) {
        return (i>0u && compose_wordlist(q,i-1u,"limit batas maximum maksimum")) ||
            (i>1u && word(q,i-1u,"of") && word(q,i-2u,"maximum"));
    }
    if (name==S_PROTOCOL && word(q,i,"all"))
        return i>0u && compose_wordlist(q,i-1u,"protocol protokol");
    return true;
}
static bool compose_typed_match(const struct request *q,struct nlu_proposal *out)
{
    size_t start=0;
    if (q->invalid || q->tokens.count>32u ||
        !typed_prefix(q,&start) || q->tokens.count-start<3u) return false;
    for (size_t i=0;i<q->tokens.count;++i)
        if (compose_wordlist(q,i,
            "not no never dont don't without except or versus vs bukan tidak jangan tanpa kecuali atau abaikan ignore bypass")) return false;
    static const char *const common=
        "a an the of for from to in on at by with and as is are me my this "
        "current currently now local information details about "
        "yang dan serta dengan untuk pada dalam di dari ke ini itu tersebut "
        "saat kini sekarang lokal informasi berdasarkan saja apa berapa tahu mengetahui melihat";
    struct nlu_proposal selected={0};
    for (size_t f=0;f<COUNT(typed_frames);++f) {
        const struct typed_frame *frame=&typed_frames[f];
        size_t intent=NO_INTENT;
        for (size_t j=0;j<COUNT(rules);++j)
            if (strcmp(rules[j].id,frame->id)==0) { intent=j; break; }
        if (intent==NO_INTENT) return false;
        const struct intent_rule *rule=&rules[intent];
        if (strcmp(rule->effect_class,"READ")!=0 || rule->guidance!=NULL) return false;
        struct nlu_proposal n={0};
        unsigned int hits[3]={0};
        bool first=false,second=false,third=frame->third==NULL,ok=true;
        for (size_t i=start;i<q->tokens.count;++i) {
            const struct token t=q->tokens.item[i];
            size_t role=SIZE_MAX;
            for (size_t j=0;j<frame->count;++j) {
                const enum slot_name name=frame->slots[j];
                const struct slot_rule *s=find_slot(intent,name);
                if (s==NULL) return false;
                /* Quoting is mandatory for text/query, forbidden for
                 * direction/numeric roles, and preserved in byte spans. */
                if ((name==S_TEXT || name==S_QUERY) && !t.quoted) continue;
                if ((name==S_DIRECTION || name==S_LIMIT) && t.quoted) continue;
                const struct candidate c={name,t};
                struct value v;
                if (value_from(q,&c,s,&v) && slot_scope(rule,&v)) {
                    if (!typed_role_anchor(q,frame,i,name)) { ok=false; break; }
                    if (role!=SIZE_MAX) { ok=false; break; }
                    role=j;
                }
            }
            if (!ok) break;
            if (role!=SIZE_MAX) {
                /* Two separately anchored candidates can be surfaced to the
                 * existing ambiguity resolver; never choose one silently.
                 * Larger multiplicities and duplicate time markers abstain. */
                if (hits[role]>=2u || !candidate_add(&n,frame->slots[role],t)) { ok=false; break; }
                ++hits[role];
            } else {
                const bool a=compose_wordlist(q,i,frame->first);
                const bool b=compose_wordlist(q,i,frame->second);
                const bool c=frame->third!=NULL && compose_wordlist(q,i,frame->third);
                first=first||a; second=second||b; third=third||c;
                if (t.quoted || (!a && !b && !c && !compose_wordlist(q,i,frame->extra) &&
                                  !compose_wordlist(q,i,common))) { ok=false; break; }
            }
        }
        if (!ok || !first || !second || !third) continue;
        bool window=false,missing=false;
        for (size_t j=0;j<frame->count;++j) {
            const struct slot_rule *slot=find_slot(intent,frame->slots[j]);
            if (slot==NULL) return false;
            if (hits[j]==0u && (frame->optional_mask & (1u<<j))==0u) {
                /* Only an existing required, non-defaulted slot may be
                 * missing. Otherwise omission might silently widen scope. */
                if (!slot->required || slot->has_default) ok=false;
                else missing=true;
            }
            if (hits[j]!=0u && frame->slots[j]==S_WINDOW) window=true;
        }
        if (!ok || window!=q->time_valid) continue;
        for (size_t j=0;j<rule->count;++j) {
            bool bound=false;
            for (size_t k=0;k<n.used;++k)
                if (n.candidates[k].name==rule->slots[j].name) bound=true;
            if (rule->slots[j].required && !rule->slots[j].has_default && !bound) missing=true;
        }
        /* Complete, unambiguous cue coverage is still mandatory. The
         * resolver will emit missing/ambiguous, not a plan. In particular,
         * absent explicit numeric/defaulted roles never become a proposal. */
        if (missing) {
            bool ambiguous=false;
            for (size_t j=0;j<frame->count;++j) if (hits[j]>1u) ambiguous=true;
            if (ambiguous) continue;
        }
        if (selected.count!=0) return false;
        n.intents[0]=intent; n.count=1; selected=n;
    }
    if (selected.count!=1) return false;
    *out=selected;
    return true;
}

#endif

static struct nlu_proposal propose(const struct request *q)
{
    struct nlu_proposal n={0};
    if (q->invalid) return n;
    if (match(q,0,q->tokens.count,&n)) {
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
#ifdef DICTUM_DEV_COMPOSE
    if (compose_match(q,&n) || compose_typed_match(q,&n)) return n;
#endif
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
    add(&w,"{\"schema_version\":2,\"intent_candidates\":[");
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
    return validate_frame(&w,IR_NLU_V2);
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
        if (!time_candidate(q,c) || q->time_start>=q->reference ||
            q->reference-q->time_start>FIXTURE_MAX_WINDOW_SECONDS) return false;
        v->context_ref=true; v->number=q->time_start; v->end=q->reference; return true;
    }
    const size_t len=t.end-t.start;
    if (len>=sizeof(v->literal)) return false;
    memcpy(v->literal,q->data+t.start,len); v->literal[len]='\0';
    if (r->kind==K_DOMAIN) {
        for (size_t i=0;i<COUNT(domain_values);++i)
            if (strcmp(r->type,domain_values[i].kind)==0 && strcmp(v->literal,domain_values[i].value)==0) return true;
        return false;
    }
    switch (r->name) {
    case S_PROTOCOL: return !t.quoted && (strcmp(v->literal,"tcp")==0 || strcmp(v->literal,"udp")==0 || strcmp(v->literal,"all")==0);
    case S_UNIT: return !t.quoted && listed(v->literal,units,COUNT(units));
    case S_ROOT: return listed(v->literal,roots,COUNT(roots));
    case S_PATH: return listed(v->literal,files,COUNT(files));
    case S_ARCHIVE: return listed(v->literal,archives,COUNT(archives));
    case S_SOURCE: return listed(v->literal,compress_sources,COUNT(compress_sources));
    case S_DESTINATION: return listed(v->literal,extract_destinations,COUNT(extract_destinations)) ||
        listed(v->literal,compress_destinations,COUNT(compress_destinations));
    case S_EXTENSION: return listed(v->literal,extensions,COUNT(extensions));
    case S_FILENAME: return listed(v->literal,filenames,COUNT(filenames));
    case S_PORT: case S_WINDOW: case S_LIMIT: case S_DEPTH: case S_COUNT:
    case S_UTILITY: case S_OPTION: case S_DOMAIN: case S_TARGET: case S_TEXT: case S_DIRECTION:
    case S_NAME: case S_PACKAGE: case S_QUERY: case S_RECORD_TYPE: return false;
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
static const char *literal_slot(const struct resolved_ir *r,enum slot_name name)
{
    for (size_t i=0;i<r->count;++i) if (r->slots[i].rule->name==name) return r->slots[i].literal;
    return NULL;
}
static const char *help_text(const struct resolved_ir *r)
{
    const char *utility=literal_slot(r,S_UTILITY),*option=literal_slot(r,S_OPTION);
    if (utility==NULL) return NULL;
    for (size_t i=0;i<COUNT(help_entries);++i) {
        const struct help_entry *e=&help_entries[i];
        if (strcmp(utility,e->utility)==0 &&
            ((option==NULL && e->option==NULL) ||
             (option!=NULL && e->option!=NULL && strcmp(option,e->option)==0))) return e->text;
    }
    return NULL;
}
static bool slot_scope(const struct intent_rule *rule,const struct value *v)
{
    if (v->rule->name==S_PATH) {
        if (strcmp(rule->id,"archive.contents.list")==0) return listed(v->literal,archives,COUNT(archives));
        if (strcmp(rule->id,"file.head_tail.view")==0) return !listed(v->literal,archives,COUNT(archives));
    }
    if (v->rule->name==S_DESTINATION) {
        if (strcmp(rule->id,"archive.extract.safe")==0)
            return listed(v->literal,extract_destinations,COUNT(extract_destinations));
        if (strcmp(rule->id,"file.compress.archive")==0)
            return listed(v->literal,compress_destinations,COUNT(compress_destinations));
        return false;
    }
    return true;
}
static bool cross_constraints(const struct resolved_ir *r)
{
    const char *id=rules[r->intent].id;
    if (strcmp(id,"help.command.explain")==0) return help_text(r)!=NULL;
    if (strcmp(id,"archive.extract.safe")==0 || strcmp(id,"file.compress.archive")==0) {
        const char *src=literal_slot(r,strcmp(id,"archive.extract.safe")==0 ? S_ARCHIVE:S_SOURCE);
        const char *dst=literal_slot(r,S_DESTINATION);
        if (src==NULL || dst==NULL || strcmp(src,dst)==0) return false;
        const size_t len=strlen(src);
        if (strncmp(src,dst,len)==0 && dst[len]=='/') return false;
    }
    return true;
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
            if (!slot_scope(rule,&v)) return invalid;
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
    else if (!cross_constraints(&r)) return invalid;
    return r;
}
static void identity(struct writer *w,const char *hash)
{
    add(w,"{\"version\":2,"); field(w,"sha256",hash); add(w,"}");
}
static void common(struct writer *w,const struct request *q)
{
    add(w,"{\"schema_version\":2,"); field(w,"request_id",q->request_id); add(w,",");
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
    return validate_frame(&w,IR_RESOLVED_V2);
}
static bool verified_values(const struct request *q,const struct resolved_ir *r)
{
    if (q==NULL || q->invalid || r->intent>=COUNT(rules) || r->count>SLOTS ||
        r->pending_count!=0 || r->alternative_count!=0) return false;
    const struct intent_rule *rule=&rules[r->intent];
    for (size_t i=0;i<r->count;++i) {
        const struct value *v=&r->slots[i];
        if (v->rule==NULL || find_slot(r->intent,v->rule->name)!=v->rule) return false;
        for (size_t j=0;j<i;++j) if (r->slots[j].rule==v->rule) return false;
        if (v->by_default) {
            if (!v->rule->has_default || v->context_ref || v->number!=v->rule->number ||
                strcmp(v->literal,v->rule->literal==NULL?"":v->rule->literal)!=0) return false;
        } else {
            struct value actual;
            const struct candidate c={v->rule->name,v->token};
            if (!value_from(q,&c,v->rule,&actual) || actual.number!=v->number ||
                actual.end!=v->end || actual.context_ref!=v->context_ref ||
                strcmp(actual.literal,v->literal)!=0) return false;
            if (!slot_scope(rule,&actual)) return false;
        }
    }
    for (size_t i=0;i<rule->count;++i)
        if (rule->slots[i].required && !has_slot(r,rule->slots[i].name)) return false;
    if (strcmp(rule->id,"network.listener.lookup")==0 && !has_slot(r,S_PORT)) return false;
    if (strcmp(rule->id,"file.search")==0 && !has_slot(r,S_EXTENSION)&&!has_slot(r,S_FILENAME)&&!has_slot(r,S_WINDOW)) return false;
    return cross_constraints(r) && (strcmp(rule->effect_class,"INFO")==0 || strcmp(rule->effect_class,"READ")==0 ||
        strcmp(rule->effect_class,"CHANGE")==0);
}
static struct policy_decision policy(const struct request *q,const struct resolved_ir *r)
{
    switch (r->state) {
    case RES_RESOLVED:
        if (!verified_values(q,r)) return (struct policy_decision){PIPE_DENY,"policy-restriction"};
        return (struct policy_decision){PIPE_PROPOSAL,"proposal-eligible"};
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
    add(w,r->state==RES_RESOLVED?rules[r->intent].effect_json:"{\"class\":\"UNKNOWN\",\"axes\":[]}");
    add(w,",\"scope\":{"); field(w,"kind",allowed?"local":"none");
    if (allowed) { add(w,","); field(w,"scope_id",q->scope_id); }
    add(w,"}");
}
static void decision_identity(struct writer *w,const struct request *q)
{
    add(w,","); field(w,"decision_id",q->decision_id); add(w,",\"policy\":"); identity(w,FIXTURE_POLICY_SHA);
}
static const char *representation(const struct resolved_ir *r,struct policy_decision p)
{
    if (p.outcome!=PIPE_PROPOSAL) return "none";
    return rules[r->intent].guidance!=NULL ? "narrative-guidance":"structured-proposal";
}
static bool serialize_policy(const struct request *q,const struct resolved_ir *r,
                             struct policy_decision p,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    common(&w,q); decision_identity(&w,q);
    add(&w,","); field(&w,"decision",decision_name(p.outcome)); effect_scope(&w,q,r,p.outcome==PIPE_PROPOSAL);
    add(&w,","); field(&w,"reason",p.reason); add(&w,",");
    field(&w,"representation",representation(r,p)); add(&w,"}");
    return validate_frame(&w,IR_POLICY_V2);
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
        if (name!=S_UNIT && name!=S_ROOT && name!=S_PATH && name!=S_DOMAIN && name!=S_TARGET &&
            name!=S_ARCHIVE && name!=S_SOURCE && name!=S_DESTINATION && name!=S_PACKAGE && name!=S_NAME) continue;
        char id[33];
        if (!id_from(q,slot_names[name],id)) return false;
        if (comma) add(&w,",");
        comma=true; add(&w,"{"); field(&w,"slot",slot_names[name]); add(&w,","); field(&w,"binding_id",id); add(&w,"}");
    }
    add(&w,"],\"action\":{\"kind\":\"structured-proposal\",\"operation\":{\"kind\":\"native\",");
    field(&w,"handler",rules[r->intent].handler); add(&w,",\"input_slots\":[");
    for (size_t i=0;i<r->count;++i) { if (i!=0) add(&w,","); quote(&w,slot_names[r->slots[i].rule->name]); }
    add(&w,"]}},"); field(&w,"digest",digest); add(&w,"}");
    return validate_frame(&w,IR_PLAN_V2);
}
static bool compile(const struct request *q,const struct resolved_ir *r,struct policy_decision p,char out[PIPE_FRAME])
{
    if (p.outcome!=PIPE_PROPOSAL || r->state!=RES_RESOLVED || r->intent>=COUNT(rules) ||
        r->pending_count!=0 || r->alternative_count!=0 || rules[r->intent].guidance!=NULL) return false;
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
static bool render(const struct request *q,const struct resolved_ir *r,struct policy_decision p,const char *plan,char out[PIPE_FRAME])
{
    struct writer w=writer(out,PIPE_FRAME);
    const bool structured_expected=p.outcome==PIPE_PROPOSAL && rules[r->intent].guidance==NULL;
    if (structured_expected!=(plan[0]!='\0')) return false;
    if (p.outcome==PIPE_PROPOSAL && !verified_values(q,r)) return false;
    if (structured_expected) {
        char expected[PIPE_FRAME];
        if (!verified_values(q,r) || !compile(q,r,p,expected) || strcmp(expected,plan)!=0) return false;
        struct ir_document doc={0};
        const bool structured=ir_parse(&doc,(const unsigned char *)plan,strlen(plan))==IR_OK &&
            renderer_structured_plan(&doc);
        ir_destroy(&doc);
        if (!structured) return false;
    }
    add(&w,"{\"copyability\":\"NON_COPYABLE\",");
    field(&w,"decision",decision_name(p.outcome)); add(&w,","); field(&w,"reason",p.reason);
    add(&w,",\"execution_allowed\":false,\"observed_os_data\":false,");
    field(&w,"source","F1 synthetic catalog; actual Debian binding NOT VERIFIED");
    add(&w,","); field(&w,"representation",representation(r,p));
    if (r->intent!=NO_INTENT) {
        add(&w,","); field(&w,"intent",rules[r->intent].id);
        add(&w,","); field(&w,"description",rules[r->intent].description_id);
    }
    if (p.outcome==PIPE_PROPOSAL) {
        add(&w,","); field(&w,"effect",rules[r->intent].effect_class);
        add(&w,","); field(&w,"scope","synthetic fixture; no target, filesystem or service access");
        add(&w,",\"effect_envelope\":"); add(&w,rules[r->intent].effect_json);
        if (rules[r->intent].guidance!=NULL) {
            add(&w,","); field(&w,"guidance_text",rules[r->intent].guidance);
            add(&w,","); field(&w,"limitations","Narrative only; no host observation, child operation or automatic check");
            add(&w,","); field(&w,"warning","No automatic probe, mutation or execution; NET requires separate proposal");
            add(&w,"}"); return w.ok;
        }
        if (strstr(rules[r->intent].effect_json,"\"network\"")!=NULL) {
            add(&w,","); field(&w,"warning","NET; synthetic proposal only; no traffic, DNS resolution or execution");
        } else if (strcmp(rules[r->intent].effect_class,"CHANGE")==0) {
            add(&w,","); field(&w,"warning","CHANGE; interruption or mutation possible; no safety guarantee, no sudo and no execution");
        }
        if (strcmp(rules[r->intent].id,"archive.extract.safe")==0 || strcmp(rules[r->intent].id,"file.compress.archive")==0) {
            add(&w,","); field(&w,"limitations","Synthetic new destination only; existence, content, traversal and overwrite safety NOT VERIFIED");
        }
        if (strcmp(rules[r->intent].id,"help.command.explain")==0) {
            const char *text=help_text(r);
            if (text==NULL) return false;
            add(&w,","); field(&w,"guidance_text",text);
            add(&w,","); field(&w,"limitations","Original internal metadata summary; actual utility option compatibility NOT VERIFIED");
        }
        if (strcmp(rules[r->intent].id,"help.intent.list")==0) {
            add(&w,",\"catalogued_ids\":[");
            for (size_t i=0;i<COUNT(catalog_entries);++i) {
                if (i!=0) add(&w,",");
                quote(&w,catalog_entries[i].id);
            }
            add(&w,"]");
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

#ifdef DICTUM_DEV_B2
static bool development_rank(const struct request *q,const struct nlu_proposal *n,
                             const struct resolved_ir *r,const struct b2_weights *weights,
                             uint32_t margin,struct b2_dev_trace *trace)
{
    /* Spans come solely from the same deterministic NLU, never gold labels.
     * Sort and union duplicate/overlapping spans before lexical extraction. */
    for (size_t i=0;i<n->used;++i) {
        const struct token t=n->candidates[i].token;
        if (trace->mask_count>=B2_MASK_MAX) return false;
        size_t j=trace->mask_count++;
        while (j>0 && trace->masks[j-1].start>t.start) {
            trace->masks[j]=trace->masks[j-1]; --j;
        }
        trace->masks[j]=(struct b2_span){t.start,t.end};
    }
    size_t used=0;
    for (size_t i=0;i<trace->mask_count;++i) {
        const struct b2_span span0=trace->masks[i];
        if (!ir_check_span(q->data,q->size,span0.start,span0.end)) return false;
        if (used!=0 && trace->masks[used-1].end>span0.start) {
            if (span0.end>trace->masks[used-1].end) trace->masks[used-1].end=span0.end;
        } else trace->masks[used++]=span0;
    }
    trace->mask_count=used;
    if (!b2_extract(q->data,q->size,trace->masks,used,&trace->features) ||
        !b2_scores(weights,&trace->features,trace->scores)) return false;
    trace->features_valid=true;
    trace->rank=b2_rank(&trace->features,trace->scores,margin);
    if (policy(q,r).outcome==PIPE_PROPOSAL) {
        if (r->state!=RES_RESOLVED || r->intent==NO_INTENT) return false;
        /* Registry ordinal and grammar rule array order are not identical. */
        for (size_t i=0;i<COUNT(catalog_entries);++i)
            if (strcmp(catalog_entries[i].id,rules[r->intent].id)==0) {
                trace->grammar_class=(int)i; break;
            }
        if (trace->grammar_class<0) return false;
    }
    return true;
}
#endif

static bool pipeline_run_common(const unsigned char *input,size_t size,int64_t reference_unix_s,
                  uint64_t request_sequence,enum pipeline_model model,
#ifdef DICTUM_DEV_B2
                  const struct b2_weights *weights,uint32_t margin,struct b2_dev_trace *trace,
#endif
                  struct pipeline_result *out)
{
#ifdef DICTUM_DEV_B2
    if (trace!=NULL) {
        *trace=(struct b2_dev_trace){.rank=-1,.grammar_class=-1};
        if (weights==NULL || margin==0 || model!=PIPE_B0) return false;
    }
#endif
    if (out==NULL) return false;
    *out=(struct pipeline_result){.outcome=PIPE_INTERNAL};
    if (model!=PIPE_B0 && model!=PIPE_B1) return false;
    if (ir_check_input(input,size)!=IR_OK) {
        out->outcome=PIPE_DENY;
        const struct resolved_ir r={.state=RES_INVALID,.intent=NO_INTENT};
        return render(NULL,&r,policy(NULL,&r),out->plan,out->view);
    }
    struct request q={.data=input,.size=size,.reference=reference_unix_s};
    if (!context(&q,request_sequence,out->context)) return false;
    struct nlu_proposal n=propose(&q);
    struct resolved_ir r=resolve(&q,&n);
    /* Ranking is an abstention guard for fully resolved proposals only.
     * A failed retrieval may not erase deterministic invalid/missing/conflict
     * diagnoses. This preflight is pure typed validation, not permission. */
    bool abstain=model==PIPE_B1 && r.state==RES_RESOLVED &&
        retrieve(&q,&n)!=n.intents[0];
#ifdef DICTUM_DEV_B2
    if (trace!=NULL) {
        if (!development_rank(&q,&n,&r,weights,margin,trace)) return false;
        abstain=trace->grammar_class>=0 && trace->rank!=trace->grammar_class;
    }
#endif
    if (abstain) {
        n=(struct nlu_proposal){0};
        r=resolve(&q,&n);
    }
    if (!serialize_nlu(&q,&n,out->nlu)) return false;
    if (!serialize_ir(&q,&r,out->ir)) return false;
    const struct policy_decision p=policy(&q,&r);
    if (!serialize_policy(&q,&r,p,out->policy)) return false;
    if (p.outcome==PIPE_PROPOSAL && rules[r.intent].guidance==NULL && !compile(&q,&r,p,out->plan)) return false;
    if (!render(&q,&r,p,out->plan,out->view)) return false;
    out->outcome=p.outcome;
    return true;
}
bool pipeline_run(const unsigned char *input,size_t size,int64_t reference_unix_s,
                  uint64_t request_sequence,enum pipeline_model model,struct pipeline_result *out)
{
    return pipeline_run_common(input,size,reference_unix_s,request_sequence,model,
#ifdef DICTUM_DEV_B2
                               NULL,0,NULL,
#endif
                               out);
}
#ifdef DICTUM_DEV_B2
bool pipeline_run_b2_dev(const unsigned char *input,size_t size,int64_t reference_unix_s,
                  uint64_t request_sequence,const struct b2_weights *weights,uint32_t margin,
                  struct b2_dev_trace *trace,struct pipeline_result *out)
{
    if (trace==NULL) return false;
    return pipeline_run_common(input,size,reference_unix_s,request_sequence,PIPE_B0,
                               weights,margin,trace,out);
}
#endif
bool pipeline_search(const char *id,char out[PIPE_FRAME])
{
    if (id==NULL || out==NULL) return false;
    struct writer w=writer(out,PIPE_FRAME);
    for (size_t i=0;i<COUNT(catalog_entries);++i) {
        if (strcmp(id,catalog_entries[i].id)==0) {
            add(&w,catalog_entries[i].metadata_json);
            return w.ok;
        }
    }
    return false;
}
bool pipeline_inspect(char out[PIPE_FRAME])
{
    if (out==NULL) return false;
    struct writer w=writer(out,PIPE_FRAME);
    add(&w,"{\"mode\":\"F1 synthetic proposal-only pipeline; all real bindings blocked\",\"primary\":\"B0-rules\",\"alternative\":\"B1-guarded-weighted-lexical-retrieval\","
        "\"neural_parameters\":0,\"intent_count\":");
    number(&w,(int64_t)COUNT(rules));
    add(&w,",\"implemented_synthetic_intent_count\":");
    number(&w,(int64_t)COUNT(rules));
    add(&w,",\"catalogued_intent_count\":");
    number(&w,(int64_t)COUNT(catalog_entries));
    add(&w,",\"f0_skeleton_intent_count\":8,\"verified_binding_count\":0,\"profile\":\"debian-13 NOT VERIFIED\",");
    field(&w,"catalog_sha256",FIXTURE_CATALOG_SHA); add(&w,","); field(&w,"catalog_registry_sha256",FIXTURE_REGISTRY_SHA);
    add(&w,",\"ir_schema_version\":2,"); field(&w,"profile_sha256",FIXTURE_PROFILE_SHA);
    add(&w,","); field(&w,"policy_sha256",FIXTURE_POLICY_SHA);
    add(&w,",\"execution_allowed\":false,\"latency\":\"not measured by inspect\"}");
    return w.ok;
}
